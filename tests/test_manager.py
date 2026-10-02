import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import yaml
from manager import Manager, compile_rules, normalize, project_script, remove_owned, signature, live_signatures, save_json
from transport import CoreError


def api_rules(rules):
    return [dict(type=k,payload=p,proxy=v) for k,p,v in map(signature,rules)]


class FakeClient:
    runtime=None
    fail_once=False
    last_transport='fake-pipe'
    def __init__(self,cfg): pass
    def request(self,method,endpoint,payload=None):
        if method=='PUT':
            FakeClient.runtime=yaml.safe_load(payload['payload'])
            if FakeClient.fail_once:
                FakeClient.fail_once=False
                raise CoreError('uncertain reload')
            return {}
        if endpoint=='/configs': return {k:copy.deepcopy(self.runtime[k]) for k in ('mode','tun','find-process-mode')}
        if endpoint=='/rules': return {'rules':api_rules(self.runtime['rules'])}
        if endpoint=='/connections': return {'connections':[]}


class ManagerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.verge=self.root/'verge';(self.verge/'profiles').mkdir(parents=True)
        self.cfg=dict(mode='rule',tun={'enable':True},**{'find-process-mode':'strict'},rules=['DOMAIN,keep.test,DIRECT','IP-CIDR,1.1.1.1/32,DIRECT,no-resolve','MATCH,PROXY'])
        (self.verge/'clash-verge.yaml').write_text(yaml.safe_dump(self.cfg),encoding='utf-8')
        (self.verge/'profiles.yaml').write_text(yaml.safe_dump({'items':[{'uid':'Script','type':'script','file':'Script.js'}]}),encoding='utf-8')
        self.script='function main(config) { config.custom = 1; return config; }\n'
        (self.verge/'profiles'/'Script.js').write_text(self.script,encoding='utf-8')
        self.m=Manager(self.root,self.verge,self.root/'fake-core')
        save_json(self.m.store,{'schema':1,'targets':[dict(id='1',kind='domain',value='game.test',label='game',source='test')]})
        FakeClient.runtime=copy.deepcopy(self.cfg);FakeClient.fail_once=False
        self.client=patch('manager.CoreClient',FakeClient);self.client.start()
        self.validation=patch.object(self.m,'validate');self.validation.start()
    def tearDown(self):
        self.validation.stop();self.client.stop();self.tmp.cleanup()
    def test_normalization(self):
        self.assertEqual(normalize('domain','https://EXAMPLE.com:443/a?q=1'),'example.com')
        self.assertEqual(normalize('domain','https://例子.中国'),'xn--fsqu00a.xn--fiqs8s')
        for bad in ('','x','127.0.0.1','*.example.com','a,b.com','a.com\nMATCH,PROXY','https://user:pass@example.com','ftp://x.com','a..com','https://x.com:bad'):
            with self.subTest(bad=bad), self.assertRaises(ValueError): normalize('domain',bad)
    def test_path_boundary(self):
        import re
        r=compile_rules([{'kind':'folder','value':'G:/Naraka'}])[0].split(',')[1]
        self.assertTrue(re.match(r,'g:\\NARAKA\\program\\game.exe'))
        self.assertTrue(re.match(r,'G:/Naraka/game.exe'))
        self.assertFalse(re.match(r,'G:/NarakaOther/game.exe'))
    def test_script_preserves_original(self):
        rules=['DOMAIN-SUFFIX,game.test,DIRECT']
        projected=project_script(self.script,rules)
        self.assertEqual(project_script(projected,[]),self.script)
        self.assertEqual(project_script(projected,rules),projected)
    def test_signatures(self):
        self.assertEqual(signature('IP-CIDR6,::1/128,DIRECT'),('ipcidr','::1/128','DIRECT'))
        self.assertEqual(signature('GEOIP,CN,DIRECT'),('geoip','cn','DIRECT'))
        self.assertEqual(signature('MATCH,PROXY'),('match','','PROXY'))
        self.assertEqual(signature('IP-CIDR,1.1.1.1/32,DIRECT,no-resolve'),('ipcidr','1.1.1.1/32','DIRECT'))
    def test_owned_duplicate_preserved(self):
        self.assertEqual(remove_owned(['own','keep','own'],['own']),['keep','own'])
        with self.assertRaises(ValueError):remove_owned(['keep','own'],['own'])
    def test_apply_reapply_restore(self):
        self.m.apply();self.m.apply()
        self.assertEqual(FakeClient.runtime['rules'][1:],self.cfg['rules'])
        self.assertTrue((self.verge/'profiles'/'Script.js').read_text(encoding='utf-8').startswith(self.script))
        self.m.apply(restore=True)
        self.assertEqual(FakeClient.runtime['rules'],self.cfg['rules'])
        self.assertEqual((self.verge/'profiles'/'Script.js').read_text(encoding='utf-8'),self.script)
    def test_uncertain_reload_rolls_back(self):
        FakeClient.fail_once=True
        with self.assertRaises(CoreError):self.m.apply()
        self.assertEqual(FakeClient.runtime,self.cfg)
        self.assertFalse(self.m.journal.exists())
    def test_validation_failure_no_writes(self):
        original=(self.verge/'clash-verge.yaml').read_bytes()
        self.m.validate.side_effect=ValueError('invalid')
        with self.assertRaises(ValueError):self.m.apply()
        self.assertEqual((self.verge/'clash-verge.yaml').read_bytes(),original)
        self.assertFalse(self.m.journal.exists())
    def test_mode_and_mismatch_block(self):
        FakeClient.runtime['mode']='global'
        with self.assertRaises(ValueError):self.m.apply()
        FakeClient.runtime['mode']='rule';FakeClient.runtime['rules']=['MATCH,DIRECT']
        with self.assertRaises(ValueError):self.m.apply()
    def test_store_persistence_and_duplicate(self):
        t=self.m.add({'kind':'domain','value':'https://new.test/path','label':'new'})
        with self.assertRaises(ValueError):self.m.add({'kind':'domain','value':'NEW.test'})
        self.assertEqual(Manager(self.root,self.verge).targets()[-1]['id'],t['id'])
        self.m.delete(t['id']);self.assertEqual(len(self.m.targets()),1)
    def test_crash_journal_blocks(self):
        save_json(self.m.journal,{'pending':True})
        with self.assertRaises(ValueError):self.m.apply()
    def test_deleted_rule_not_reported_effective(self):
        self.m.apply()
        self.assertTrue(self.m.state()['effective'])
        self.m.delete('1')
        self.assertFalse(self.m.state()['effective'])
        self.m.apply()
        self.assertEqual(FakeClient.runtime['rules'],self.cfg['rules'])
    def test_missing_store_schema_not_overwritten(self):
        self.m.store.write_text('{"schema":99}',encoding='utf-8')
        with self.assertRaises(ValueError):Manager(self.root,self.verge)
        self.assertEqual(json.loads(self.m.store.read_text())['schema'],99)
    def test_pending_recovery_and_concurrent_edits(self):
        configpath=self.verge/'clash-verge.yaml';scriptpath=self.verge/'profiles'/'Script.js'
        old=configpath.read_text(encoding='utf-8')
        new=yaml.safe_dump(dict(self.cfg,rules=['DOMAIN-SUFFIX,game.test,DIRECT']+self.cfg['rules']))
        save_json(self.m.journal,dict(oldConfig=old,newConfig=new,oldScript=self.script,newScript=project_script(self.script,['DOMAIN-SUFFIX,game.test,DIRECT']),scriptPath=str(scriptpath),previous={}))
        configpath.write_text(new,encoding='utf-8')
        self.m.recover()
        self.assertEqual(configpath.read_text(encoding='utf-8'),old)
        self.assertFalse(self.m.journal.exists())
    def test_concurrent_change_blocks_write(self):
        self.m.validate.side_effect=lambda *args:(self.verge/'profiles'/'Script.js').write_text(self.script+'// external change\n',encoding='utf-8')
        with self.assertRaises(ValueError):self.m.apply()
        self.assertEqual(FakeClient.runtime,self.cfg)
    def test_folder_requires_process_detection(self):
        self.m.add({'kind':'folder','value':str(self.root),'label':'temp folder'})
        FakeClient.runtime['find-process-mode']='off'
        with self.assertRaises(ValueError):self.m.apply()
        self.assertFalse(self.m.journal.exists())


if __name__=='__main__':unittest.main()
