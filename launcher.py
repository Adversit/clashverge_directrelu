"""One-click bootstrap, Windows mutex and identity-checked existing server reuse."""
import ctypes
import json
import os
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT=Path(__file__).resolve().parent
URL='http://127.0.0.1:17891'


def healthy():
    try:
        op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with op.open(URL+'/api/health',timeout=1) as r:
            return json.load(r).get('app')=='clash-direct-manager-v1'
    except Exception:
        return False


def main():
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.CreateMutexW.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_wchar_p]
    k.CreateMutexW.restype=ctypes.c_void_p
    k.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint]
    k.ReleaseMutex.argtypes=[ctypes.c_void_p];k.CloseHandle.argtypes=[ctypes.c_void_p]
    handle=k.CreateMutexW(None,False,'Local\\ClashDirectManagerLauncherV1')
    if not handle or k.WaitForSingleObject(handle,90000) not in (0,128):
        raise RuntimeError('Another startup is in progress. Retry in one minute.')
    try:
        if healthy(): webbrowser.open(URL); return
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
    try: main()
    except Exception as exc:
        ctypes.windll.user32.MessageBoxW(None,str(exc),'Clash Direct Manager',0x10)
        sys.exit(1)
