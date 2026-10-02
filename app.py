"""Loopback-only server. Controller credentials never leave the backend."""
import argparse
import json
import os
import secrets
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from manager import Manager
from transport import CoreError

APP_ID = 'clash-direct-manager-v1'


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False
    def server_bind(self):
        if os.name == 'nt':
            self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        super().server_bind()
    def __init__(self, port, manager):
        super().__init__(('127.0.0.1', port), Handler)
        self.manager = manager
        self.token = secrets.token_urlsafe(32)
        self.origin = 'http://127.0.0.1:' + str(self.server_port)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # Never log request bodies or controller configuration.

    def send(self, status, body, content_type='application/json; charset=utf-8'):
        if not isinstance(body, bytes): body = json.dumps(body, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        for k,v in {'Content-Type':content_type,'Content-Length':str(len(body)), 'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Content-Security-Policy':"default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"}.items():
            self.send_header(k,v)
        self.end_headers(); self.wfile.write(body)

    def safe(self, mutation=False):
        if self.headers.get('Host') != self.server.origin.removeprefix('http://'):
            self.send(403,{'error':'Invalid Host'}); return False
        origin = self.headers.get('Origin')
        if origin and origin != self.server.origin:
            self.send(403,{'error':'Invalid Origin'}); return False
        if self.headers.get('Sec-Fetch-Site') == 'cross-site':
            self.send(403,{'error':'Cross-site request blocked'}); return False
        if mutation and (origin != self.server.origin or not secrets.compare_digest(self.headers.get('X-Session-Token',''), self.server.token)):
            self.send(403,{'error':'请刷新页面后重试。'}); return False
        return True

    def do_GET(self):
        if not self.safe(): return
        path = urlsplit(self.path).path
        try:
            if path == '/api/health': return self.send(200,dict(app=APP_ID))
            if path == '/api/state': return self.send(200,dict(self.server.manager.state(),token=self.server.token))
            files = {'/':'index.html','/app.js':'app.js','/style.css':'style.css'}
            if path not in files: return self.send(404,{'error':'Not found'})
            body=(Path(__file__).parent/'static'/files[path]).read_bytes()
            types={'/':'text/html; charset=utf-8','/app.js':'text/javascript; charset=utf-8','/style.css':'text/css; charset=utf-8'}
            self.send(200,body,types[path])
        except Exception:
            self.send(500,{'error':'无法读取本地状态，请检查配置与目标清单。'})

    def mutate(self):
        if not self.safe(True): return
        try:
            if self.headers.get('Content-Type','').split(';')[0] != 'application/json':
                return self.send(415,{'error':'Expected JSON'})
            length=int(self.headers.get('Content-Length','0'))
            if length < 2 or length > 8192: return self.send(413,{'error':'Invalid body size'})
            self.connection.settimeout(5)
            body=json.loads(self.rfile.read(length))
            if not isinstance(body,dict): raise ValueError('请求格式错误。')
            path=urlsplit(self.path).path
            manager=self.server.manager
            if self.command=='POST' and path=='/api/targets': result=manager.add(body)
            elif self.command=='DELETE' and path.startswith('/api/targets/'): manager.delete(path.rsplit('/',1)[1]); result={'ok':True}
            elif self.command=='POST' and path=='/api/apply': result=manager.apply()
            elif self.command=='POST' and path=='/api/restore': result=manager.apply(restore=True)
            elif self.command=='POST' and path=='/api/recover': result=manager.recover()
            else: return self.send(404,{'error':'Not found'})
            self.send(200,result)
        except (ValueError,CoreError) as exc:
            self.send(400,{'error':str(exc)})
        except Exception:
            self.send(500,{'error':'操作失败，请刷新查看状态；如有中断记录，请先恢复。'})

    do_POST=mutate
    do_DELETE=mutate


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--port',type=int,default=17891)
    args=parser.parse_args()
    Server(args.port,Manager()).serve_forever()
