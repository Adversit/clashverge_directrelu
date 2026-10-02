import http.client
import json
import threading
import unittest
from app import Server


class FakeManager:
    def state(self):return {'targets':[]}
    def add(self,body):return body


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=Server(0,FakeManager());cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def req(self,path='/api/health',method='GET',body=None,headers=None):
        c=http.client.HTTPConnection('127.0.0.1',self.server.server_port)
        c.request(method,path,body=body,headers=headers or {});r=c.getresponse();data=r.read();status=r.status;c.close();return status,data
    def test_health_and_static(self):
        self.assertEqual(self.req()[0],200)
        self.assertEqual(self.req('/')[0],200)
    def test_host_and_origin(self):
        self.assertEqual(self.req(headers={'Host':'evil.test'})[0],403)
        self.assertEqual(self.req(headers={'Origin':'https://evil.test'})[0],403)
    def test_mutation_token(self):
        h={'Origin':self.server.origin,'Content-Type':'application/json'}
        self.assertEqual(self.req('/api/targets','POST','{}',h)[0],403)
        h['X-Session-Token']=self.server.token
        self.assertEqual(self.req('/api/targets','POST','{}',h)[0],200)
        self.assertEqual(self.req('/api/targets','POST','[]',h)[0],400)
    def test_cross_site_read(self):self.assertEqual(self.req('/api/state',headers={'Sec-Fetch-Site':'cross-site'})[0],403)
    def test_conflicting_port_and_bad_body(self):
        with self.assertRaises(OSError):Server(self.server.server_port,FakeManager())
        self.assertEqual(self.req()[0],200)
        h={'Origin':self.server.origin,'Content-Type':'application/json','X-Session-Token':self.server.token}
        self.assertEqual(self.req('/api/targets','POST','{broken',h)[0],400)
        h['Content-Type']='text/plain'
        self.assertEqual(self.req('/api/targets','POST','{}',h)[0],415)


if __name__=='__main__':unittest.main()
