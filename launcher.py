"""One-click bootstrap, Windows mutex and identity-checked existing server reuse."""
import ctypes
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT=Path(__file__).resolve().parent
URL='http://127.0.0.1:17891'


def listeners():
    script = "$ErrorActionPreference='Stop'; $items=@(Get-NetTCPConnection -LocalAddress '127.0.0.1' -LocalPort 17891 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { $proc=Get-CimInstance Win32_Process -Filter ('ProcessId = ' + $_.OwningProcess); if ($proc) { [PSCustomObject]@{ProcessId=$proc.ProcessId;ExecutablePath=$proc.ExecutablePath;CommandLine=$proc.CommandLine;CreationFileTimeUtc=$proc.CreationDate.ToFileTimeUtc()} } }); ConvertTo-Json -InputObject $items -Compress"
    result=subprocess.run(['powershell.exe','-NoProfile','-Command',script],capture_output=True,text=True,encoding='utf-8',creationflags=subprocess.CREATE_NO_WINDOW,timeout=12)
    if result.returncode: raise RuntimeError('Cannot inspect the listener. No process was stopped.')
    return json.loads(result.stdout or '[]')


def is_our_process(record):
    executable=record.get('ExecutablePath') or ''
    if Path(executable).name.lower() not in ('python.exe','pythonw.exe'): return False
    args=[a or b for a,b in re.findall(r'"([^\"]*)"|(\S+)',record.get('CommandLine') or '')]
    expected=os.path.normcase(str(ROOT/'app.py'))
    return len(args)>1 and os.path.isabs(args[1]) and os.path.normcase(os.path.abspath(args[1]))==expected


def terminate_verified(record):
    """Retain the process handle and verify creation time before termination."""
    from ctypes import wintypes
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];k.OpenProcess.restype=wintypes.HANDLE
    k.GetProcessTimes.argtypes=[wintypes.HANDLE]+[ctypes.POINTER(wintypes.FILETIME)]*4
    k.TerminateProcess.argtypes=[wintypes.HANDLE,wintypes.UINT]
    k.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
    k.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=k.OpenProcess(0x100001|0x1000,False,record['ProcessId'])
    if not handle: raise RuntimeError('The listener process changed or cannot be accessed. Retry after refreshing.')
    try:
        times=[wintypes.FILETIME() for _ in range(4)]
        if not k.GetProcessTimes(handle,*[ctypes.byref(x) for x in times]):
            raise RuntimeError('Cannot verify listener creation time.')
        created=(times[0].dwHighDateTime<<32)|times[0].dwLowDateTime
        # WMI CreationDate has microsecond precision; FILETIME also has 100ns digits.
        if created//10!=int(record['CreationFileTimeUtc'])//10:
            raise RuntimeError('Listener PID was reused. No process was stopped.')
        if not k.TerminateProcess(handle,0): raise RuntimeError('Cannot stop the website server.')
        if k.WaitForSingleObject(handle,5000)!=0: raise RuntimeError('Website server stop timed out.')
    finally: k.CloseHandle(handle)


def stop_server():
    records=listeners()
    if not records: return
    if len(records)!=1 or not is_our_process(records[0]) or not healthy():
        raise RuntimeError('Port 17891 belongs to an unverified process. No process was stopped.')
    terminate_verified(records[0])
    if listeners(): raise RuntimeError('Port 17891 is still occupied. Restart was cancelled.')


def healthy():
    try:
        op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with op.open(URL+'/api/health',timeout=1) as r:
            return json.load(r).get('app')=='clash-direct-manager-v1'
    except Exception:
        return False


def main(action='start'):
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.CreateMutexW.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_wchar_p]
    k.CreateMutexW.restype=ctypes.c_void_p
    k.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint]
    k.ReleaseMutex.argtypes=[ctypes.c_void_p];k.CloseHandle.argtypes=[ctypes.c_void_p]
    handle=k.CreateMutexW(None,False,'Local\\ClashDirectManagerLauncherV1')
    if not handle or k.WaitForSingleObject(handle,90000) not in (0,128):
        raise RuntimeError('Another startup is in progress. Retry in one minute.')
    try:
        if action in ('stop','restart'):
            stop_server()
            if action=='stop': return
        if healthy(): webbrowser.open(URL); return
        if listeners(): raise RuntimeError('Port 17891 is occupied. No other process was stopped.')
        py=ROOT/'.venv'/'Scripts'/'python.exe'
        flags=subprocess.CREATE_NO_WINDOW
        if not py.exists():
            subprocess.run([sys.executable,'-m','venv',str(ROOT/'.venv')],check=True,creationflags=flags)
        dependency=subprocess.run([str(py),'-c','import yaml'],capture_output=True,creationflags=flags)
        if dependency.returncode:
            subprocess.run([str(py),'-m','pip','install','--index-url','https://pypi.org/simple','-r',str(ROOT/'requirements.txt')],check=True,creationflags=flags,timeout=120)
        (ROOT/'data').mkdir(exist_ok=True)
        with (ROOT/'data'/'server.log').open('ab') as log:
            p=subprocess.Popen([str(py),str(ROOT/'app.py')],cwd=str(ROOT),stdout=log,stderr=log,creationflags=flags)
        for _ in range(50):
            if p.poll() is not None:
                raise RuntimeError('Server startup failed (possibly port 17891 is occupied). See data/server.log. No other process was stopped.')
            if healthy(): webbrowser.open(URL); return
            time.sleep(.2)
        raise RuntimeError('Server startup timed out. See data/server.log.')
    finally:
        k.ReleaseMutex(handle);k.CloseHandle(handle)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--action',choices=('start','restart','stop'),default='start')
    args=parser.parse_args()
    try: main(args.action)
    except Exception as exc:
        ctypes.windll.user32.MessageBoxW(None,str(exc),'Clash Direct Manager',0x10)
        sys.exit(1)
