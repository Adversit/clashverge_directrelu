"""Local Mihomo API, including Windows service/sidecar named pipes."""
import ctypes
import http.client
import io
import json
import os
from ctypes import wintypes


class CoreError(RuntimeError):
    pass


class PipeIO(io.RawIOBase):
    """Overlapped pipe IO: both opening and HTTP reads have bounded timeouts."""
    def __init__(self, name, timeout=5):
        if os.name != 'nt':
            raise CoreError('Windows named pipes require Windows.')
        super().__init__()
        self.timeout = int(timeout * 1000)
        self.k = ctypes.WinDLL('kernel32', use_last_error=True)
        class OVERLAPPED(ctypes.Structure):
            _fields_ = [('Internal', ctypes.c_size_t), ('InternalHigh', ctypes.c_size_t),
                        ('Offset', wintypes.DWORD), ('OffsetHigh', wintypes.DWORD),
                        ('hEvent', wintypes.HANDLE)]
        self.OV = OVERLAPPED
        self.k.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                      ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        self.k.CreateFileW.restype = wintypes.HANDLE
        self.k.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
        self.k.CreateEventW.restype = wintypes.HANDLE
        for method in ('ReadFile', 'WriteFile'):
            getattr(self.k, method).argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
                                               ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(OVERLAPPED)]
        self.k.WaitNamedPipeW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD]
        self.k.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        self.k.GetOverlappedResult.argtypes = [wintypes.HANDLE, ctypes.POINTER(OVERLAPPED), ctypes.POINTER(wintypes.DWORD), wintypes.BOOL]
        self.k.CancelIoEx.argtypes = [wintypes.HANDLE, ctypes.POINTER(OVERLAPPED)]
        self.k.CloseHandle.argtypes = [wintypes.HANDLE]
        self.k.WaitNamedPipeW(name, self.timeout)
        self.handle = self.k.CreateFileW(name, 0xC0000000, 0, None, 3, 0x40000000, None)
        if self.handle == ctypes.c_void_p(-1).value:
            self.handle = None
            raise OSError(ctypes.get_last_error(), 'Cannot connect to Mihomo pipe')

    def readable(self):
        return True

    def writable(self):
        return True

    def _io(self, write, buf, count):
        event = self.k.CreateEventW(None, True, False, None)
        ov = self.OV()
        ov.hEvent = event
        done = wintypes.DWORD()
        try:
            ok = (self.k.WriteFile if write else self.k.ReadFile)(self.handle, buf, count, ctypes.byref(done), ctypes.byref(ov))
            if not ok:
                err = ctypes.get_last_error()
                if not write and err in (109, 232):
                    return 0
                if err != 997:
                    raise OSError(err, 'Mihomo pipe IO failed')
                if self.k.WaitForSingleObject(event, self.timeout) != 0:
                    self.k.CancelIoEx(self.handle, ctypes.byref(ov))
                    self.k.GetOverlappedResult(self.handle, ctypes.byref(ov), ctypes.byref(done), True)
                    raise TimeoutError('Mihomo pipe request timed out')
                if not self.k.GetOverlappedResult(self.handle, ctypes.byref(ov), ctypes.byref(done), False):
                    err = ctypes.get_last_error()
                    if not write and err in (109, 232):
                        return 0
                    raise OSError(err, 'Mihomo pipe response failed')
            return done.value
        finally:
            self.k.CloseHandle(event)

    def readinto(self, b):
        buf = (ctypes.c_char * len(b)).from_buffer(b)
        return self._io(False, buf, len(b))

    def write(self, b):
        buf = ctypes.create_string_buffer(bytes(b))
        return self._io(True, buf, len(b))

    def close(self):
        if getattr(self, 'handle', None):
            self.k.CloseHandle(self.handle)
            self.handle = None
        super().close()


class PipeSocket:
    def __init__(self, raw):
        self.raw = raw

    def makefile(self, *args, **kwargs):
        return io.BufferedReader(self.raw)


class CoreClient:
    def __init__(self, config):
        self.config = config
        self.last_transport = None

    def pipe_names(self):
        name = str(self.config.get('external-controller-pipe', '')).split('\\')[-1]
        if not name:
            return []
        names = [name, name.replace('sidecar-release', 'production')]
        return list(dict.fromkeys('\\\\.\\pipe\\' + n for n in names))

    def request(self, method, endpoint, payload=None):
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8') if payload is not None else b''
        headers = {'Authorization': 'Bearer ' + str(self.config.get('secret', '')),
                   'Content-Type': 'application/json', 'Connection': 'close'}
        # Service mode uses a production pipe with the same installation ID.
        candidates = self.pipe_names()
        if self.last_transport in candidates:
            candidates.remove(self.last_transport)
            candidates.insert(0, self.last_transport)
        last = None
        for name in candidates:
            try:
                raw = PipeIO(name)
            except OSError as exc:
                last = exc
                continue
            try:
                request = f'{method} {endpoint} HTTP/1.1\r\nHost: localhost\r\n'
                request += ''.join(f'{k}: {v}\r\n' for k, v in headers.items())
                data = (request + f'Content-Length: {len(body)}\r\n\r\n').encode() + body
                offset = 0
                while offset < len(data):
                    written = raw.write(data[offset:])
                    if not written:
                        raise CoreError('Mihomo pipe write failed.')
                    offset += written
                response = http.client.HTTPResponse(PipeSocket(raw))
                response.begin()
                content = response.read()
                status = response.status
                response.close()
                self.last_transport = name
                return self._result(status, content)
            except (OSError, TimeoutError, http.client.HTTPException) as exc:
                # Never retry an uncertain mutation on another transport.
                raise CoreError('Mihomo pipe request failed; refresh before retrying.') from exc
            finally:
                raw.close()
        controller = str(self.config.get('external-controller', '')).strip()
        if controller:
            host, port = controller.rsplit(':', 1)
            if host not in ('127.0.0.1', 'localhost'):
                raise CoreError('Only a loopback controller is supported.')
            connection = http.client.HTTPConnection(host, int(port), timeout=5)
            try:
                connection.request(method, endpoint, body=body, headers=headers)
                response = connection.getresponse()
                return self._result(response.status, response.read())
            except OSError as exc:
                raise CoreError('Clash Verge is offline or its controller is unavailable.') from exc
            finally:
                connection.close()
        raise CoreError('Clash Verge is offline or its named pipe is unavailable.') from last

    @staticmethod
    def _result(status, content):
        if status >= 400:
            # Do not relay core errors which may include credentials/config text.
            raise CoreError(f'Mihomo rejected the request (HTTP {status}).')
        return json.loads(content) if content else {}
