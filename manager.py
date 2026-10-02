"""Owned rule projection, loopback core access and recoverable transactions."""
import copy
import ipaddress
import json
import os
import re
import shutil
import subprocess
import threading
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

import yaml
from transport import CoreClient, CoreError

BEGIN = '// BEGIN CLASH_DIRECT_MANAGER_V1'
END = '// END CLASH_DIRECT_MANAGER_V1'
DEFAULTS = [
    ('domain', 'yjwujian.cn', '永劫无间国服官网与更新站', 'https://www.yjwujian.cn/ + local repair logs'),
    ('domain', 'narakathegame.com', '永劫无间国际官网', 'https://www.narakathegame.com/'),
    ('domain', 'd90.gdl.netease.com', '游戏下载服务器', 'G:/Naraka/patch/repair_2026_10_02_09_42_49.log'),
    ('domain', 'd90-06.gdl.netease.com', '游戏补丁下载服务器', 'G:/Naraka/patch/repair_2026_10_02_09_42_49.log'),
    ('folder', 'G:/Naraka', '游戏、启动器与更新器', 'Local executable inventory'),
]


def stamp():
    return datetime.now().astimezone().isoformat(timespec='seconds')


def write_atomic(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        tmp.write_text(text, encoding='utf-8', newline='')
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def read_json(path, default):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else copy.deepcopy(default)


def save_json(path, data):
    write_atomic(path, json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def normalize(kind, value):
    if not isinstance(value, str) or not value.strip() or len(value) > 2048:
        raise ValueError('请输入有效的网址或目录。')
    value = value.strip()
    if any(ord(c) < 32 for c in value) or ',' in value:
        raise ValueError('输入不能包含逗号或控制字符。')
    if kind == 'domain':
        u = urlsplit(value if '://' in value else 'https://' + value)
        if u.scheme not in ('http', 'https') or u.username or u.password or not u.hostname:
            raise ValueError('只接受 HTTP(S) 网址或域名，不接受账户信息。')
        try:
            u.port
            host = u.hostname.rstrip('.').encode('idna').decode('ascii').lower()
        except (ValueError, UnicodeError):
            raise ValueError('域名或端口格式错误。') from None
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError('请使用域名，暂不接受 IP 地址。')
        if len(host) > 253 or '.' not in host or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', s) for s in host.split('.')):
            raise ValueError('域名格式错误。')
        return host
    if kind == 'folder':
        path = Path(value).resolve()
        if not path.is_dir() or not re.match(r'^[A-Za-z]:[\\/]', str(path)) or path == Path(path.anchor):
            raise ValueError('请选择存在的 Windows 本地目录，不能使用磁盘根目录。')
        return path.as_posix().rstrip('/')
    raise ValueError('不支持的目标类型。')


def compile_rules(targets):
    result = []
    for t in targets:
        if t['kind'] == 'domain':
            result.append('DOMAIN-SUFFIX,' + t['value'] + ',DIRECT')
        else:
            parts = re.split(r'[\\/]', t['value'].rstrip('/\\'))
            pattern = '(?i)^' + r'[\\/]'.join(re.escape(s) for s in parts) + r'[\\/].*'
            result.append('PROCESS-PATH-REGEX,' + pattern + ',DIRECT')
    return list(dict.fromkeys(result))


def strip_script(text):
    if BEGIN not in text and END not in text:
        return text
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        raise ValueError('全局脚本的管理标记异常，请先检查备份。')
    start, end = text.index(BEGIN), text.index(END) + len(END)
    if end < start or text[end:].strip():
        raise ValueError('管理脚本之后有其他内容，停止修改以保留自定义脚本。')
    return text[:start]


def project_script(text, rules):
    base = strip_script(text)
    if not rules:
        return base
    if not re.search(r'function\s+main\s*\(', base):
        raise ValueError('全局脚本缺少 main 函数。')
    # Keep the original bytes; the managed block owns its added newline.
    if base and not base.endswith('\n'):
        raise ValueError('请先在全局脚本末尾添加换行。')
    return base + BEGIN + '\n' + 'const __cdmOriginal = main;\nmain = function(config, profileName) {\n' + \
        '  const out = __cdmOriginal(config, profileName);\n' + \
        '  const direct = ' + json.dumps(rules, ensure_ascii=True) + ';\n' + \
        '  out.rules = direct.concat((out.rules || []).filter(r => !direct.includes(r)));\n' + \
        '  return out;\n};\n' + END + '\n'


def signature(rule):
    parts = rule.split(',')
    while parts[-1] in ('no-resolve', 'src'):
        parts.pop()
    kind, proxy = parts[0], parts[-1]
    payload = ','.join(parts[1:-1])
    key=kind.replace('-', '').lower()
    if key=='ipcidr6': key='ipcidr'
    if key=='geoip': payload=payload.lower()
    return (key, payload, proxy)


def live_signatures(rules):
    return [(r['type'].replace('-', '').lower(), r.get('payload', ''), r['proxy']) for r in rules]


def remove_owned(rules, owned):
    if owned and rules[:len(owned)] != owned:
        # Regeneration or user modifications: refuse an ambiguous removal.
        if any(r in rules for r in owned):
            raise ValueError('规则顺序已被其他程序修改，请刷新后检查或恢复。')
        return list(rules)
    return list(rules[len(owned):])


class Manager:
    def __init__(self, root=None, verge=None, core=None):
        self.root = Path(root or Path(__file__).parent)
        self.data = self.root / 'data'
        self.verge = Path(verge or os.environ.get('CLASH_VERGE_DATA') or Path(os.environ['APPDATA']) / 'io.github.clash-verge-rev.clash-verge-rev')
        self.core = Path(core or os.environ.get('MIHOMO_EXE', 'D:/clash verge/verge-mihomo.exe'))
        self.lock = threading.RLock()
        self.store = self.data / 'targets.json'
        self.applied = self.data / 'applied.json'
        self.journal = self.data / 'transaction.json'
        if not self.store.exists():
            targets = [dict(id=uuid.uuid4().hex, kind=k, value=v, label=l, source=s) for k,v,l,s in DEFAULTS if k != 'folder' or Path(v).is_dir()]
            save_json(self.store, {'schema': 1, 'targets': targets})
        self.targets()  # A corrupt store must never be overwritten.

    def targets(self):
        data = read_json(self.store, {})
        if data.get('schema') != 1 or not isinstance(data.get('targets'), list):
            raise ValueError('目标清单损坏，请从备份恢复 data/targets.json。')
        ids = set()
        for t in data['targets']:
            if not isinstance(t, dict) or not all(isinstance(t.get(k), str) for k in ('id', 'kind', 'value', 'label', 'source')) or t['id'] in ids:
                raise ValueError('目标清单字段损坏。')
            ids.add(t['id'])
            if t['kind'] == 'domain' and normalize('domain', t['value']) != t['value']:
                raise ValueError('保存的域名格式错误。')
            if t['kind'] not in ('domain', 'folder') or (t['kind'] == 'folder' and (not re.match(r'^[A-Za-z]:/', t['value']) or ',' in t['value'] or any(ord(c)<32 for c in t['value']))):
                raise ValueError('保存的目录格式错误。')
        return data['targets']

    def add(self, body):
        with self.lock:
            kind = body.get('kind', 'domain')
            value = normalize(kind, body.get('value'))
            label = body.get('label', '')
            if not isinstance(label, str) or len(label) > 120:
                raise ValueError('备注最多 120 字。')
            targets = self.targets()
            if any(t['kind'] == kind and t['value'].lower() == value.lower() for t in targets):
                raise ValueError('该目标已经存在。')
            target = dict(id=uuid.uuid4().hex, kind=kind, value=value, label=label.strip() or value, source='User')
            targets.append(target)
            save_json(self.store, {'schema': 1, 'targets': targets})
            return target

    def delete(self, tid):
        with self.lock:
            targets = self.targets()
            new = [t for t in targets if t['id'] != tid]
            if len(new) == len(targets):
                raise ValueError('目标不存在。')
            save_json(self.store, {'schema': 1, 'targets': new})

    def config(self):
        return yaml.safe_load((self.verge / 'clash-verge.yaml').read_text(encoding='utf-8'))

    def script_path(self):
        profiles = yaml.safe_load((self.verge / 'profiles.yaml').read_text(encoding='utf-8'))
        item = next((x for x in profiles['items'] if x['uid'] == 'Script'), None)
        if not item or item['type'] != 'script':
            raise ValueError('未找到 Clash Verge 全局 Script。')
        path = (self.verge / 'profiles' / item['file']).resolve()
        if path.parent != (self.verge / 'profiles').resolve():
            raise ValueError('全局脚本路径异常。')
        return path

    def state(self):
        with self.lock:
            targets = self.targets()
            desired = compile_rules(targets)
            applied = read_json(self.applied, {})
            s = dict(targets=targets, rules=desired, online=False, persisted=False, effective=False,
                     pendingRecovery=self.journal.exists(), lastApply=applied.get('result'), connections=[], executables=[])
            try:
                text = self.script_path().read_text(encoding='utf-8')
                s['persisted'] = text == project_script(text, desired)
                client = CoreClient(self.config())
                cfg = client.request('GET', '/configs')
                live = client.request('GET', '/rules')['rules']
                sigs = live_signatures(live)
                s.update(online=True, mode=cfg['mode'], tun=cfg.get('tun', {}).get('enable', False), transport='Windows named pipe' if client.last_transport else 'Loopback HTTP',
                         effective=cfg['mode'] == 'rule' and (cfg.get('find-process-mode')!='off' or not any(t['kind']=='folder' for t in targets)) and applied.get('desired') == desired and set(sigs[:len(desired)]) == set(signature(r) for r in desired))
                connections = client.request('GET', '/connections')['connections']
                for x in connections:
                    m = x['metadata']; host = m.get('host', '').lower(); path = m.get('processPath', '')
                    related = any((t['kind']=='domain' and (host==t['value'] or host.endswith('.'+t['value']))) or (t['kind']=='folder' and path.replace('\\','/').lower().startswith(t['value'].lower()+'/')) for t in targets)
                    if related:
                        s['connections'].append(dict(host=host, process=m.get('process'), processPath=path, destinationIP=m.get('destinationIP'), network=m.get('network'), chains=x['chains'], rule=x['rule'], rulePayload=x.get('rulePayload')))
            except (OSError, CoreError, ValueError, KeyError) as exc:
                s['error'] = str(exc) if isinstance(exc, (CoreError, ValueError)) else '无法读取 Clash Verge 配置或连接。'
            for t in targets:
                if t['kind']=='folder' and Path(t['value']).is_dir():
                    s['executables'].extend(str(p) for p in Path(t['value']).rglob('*.exe'))
            return s

    def validate(self, candidate, script, desired):
        node = shutil.which('node')
        if not node:
            raise ValueError('需要 Node.js 来校验全局脚本，请安装 Node.js 后重试。')
        js = 'const vm=require("vm");const fs=require("fs");const x=JSON.parse(fs.readFileSync(0,"utf8"));const ctx={input:x.config};vm.createContext(ctx);vm.runInContext(x.script,ctx,{timeout:1500});const out=vm.runInContext("main(input,\\\"validation\\\")",ctx,{timeout:1500});if(JSON.stringify(out.rules.slice(0,x.rules.length))!==JSON.stringify(x.rules))process.exit(2);'
        result = subprocess.run([node,'-e',js], input=json.dumps(dict(script=script,config=yaml.safe_load(candidate),rules=desired)), text=True, encoding='utf-8', capture_output=True, timeout=8)
        if result.returncode:
            raise ValueError('全局脚本校验失败，尚未修改 Clash Verge。')
        if not self.core.is_file():
            raise ValueError('未找到 Mihomo。请设置 MIHOMO_EXE 为内核程序路径。')
        testfile = self.data / 'candidate.yaml'
        write_atomic(testfile, candidate)
        try:
            result = subprocess.run([str(self.core), '-t', '-d', str(self.verge), '-f', str(testfile)], capture_output=True, timeout=30)
            if result.returncode:
                raise ValueError('Mihomo 配置校验失败，尚未修改 Clash Verge。')
        finally:
            testfile.unlink(missing_ok=True)

    def apply(self, restore=False):
        with self.lock:
            if self.journal.exists():
                raise ValueError('上次操作未完成，请先点击恢复中断操作。')
            configpath = self.verge / 'clash-verge.yaml'
            scriptpath = self.script_path()
            original = configpath.read_text(encoding='utf-8')
            oldscript = scriptpath.read_text(encoding='utf-8')
            cfg = yaml.safe_load(original)
            client = CoreClient(cfg)
            runtime = client.request('GET', '/configs')
            live = client.request('GET', '/rules')['rules']
            if live_signatures(live) != [signature(r) for r in cfg.get('rules', [])]:
                raise ValueError('运行规则与配置文件不一致，请在 Clash Verge 重载配置后再试。')
            if not restore and runtime['mode'] != 'rule':
                raise ValueError('当前不是规则模式，请在 Clash Verge 切换到规则模式再应用。')
            previous = read_json(self.applied, {})
            desired = [] if restore else compile_rules(self.targets())
            remaining = remove_owned(cfg.get('rules', []), previous.get('owned', []))
            inserted = [r for r in desired if r not in remaining]
            # Already-existing identical rules are moved only if at the beginning; otherwise refuse ownership ambiguity.
            present = [r for r in desired if r in remaining]
            if present and remaining[:len(present)] != present:
                raise ValueError('已有相同直连规则位于其他位置，请在 Clash Verge 整理后再应用。')
            newcfg = copy.deepcopy(cfg)
            newcfg['rules'] = inserted + remaining
            for key in ('mode','tun','find-process-mode'):
                if key in runtime: newcfg[key] = runtime[key]
            if any(t['kind']=='folder' for t in self.targets()) and not restore and newcfg.get('find-process-mode')=='off':
                raise ValueError('Clash Verge 已关闭进程识别，请启用后再应用目录规则。')
            candidate = yaml.safe_dump(newcfg, allow_unicode=True, sort_keys=False)
            newscript = project_script(oldscript, desired)
            self.validate(candidate, newscript, desired)
            if configpath.read_text(encoding='utf-8') != original or scriptpath.read_text(encoding='utf-8') != oldscript or client.request('GET','/configs') != runtime:
                raise ValueError('校验期间配置已改变，请刷新后重试。')
            backup = self.data / 'backups' / (datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8])
            backup.mkdir(parents=True)
            write_atomic(backup/'clash-verge.yaml', original)
            write_atomic(backup/'Script.js', oldscript)
            journal = dict(backup=str(backup),scriptPath=str(scriptpath),oldConfig=original,oldScript=oldscript,newConfig=candidate,newScript=newscript,previous=previous)
            save_json(self.journal,journal)
            try:
                write_atomic(scriptpath,newscript)
                write_atomic(configpath,candidate)
                client.request('PUT','/configs?force=true',{'payload':candidate})
                if live_signatures(client.request('GET','/rules')['rules']) != [signature(r) for r in newcfg['rules']]:
                    raise CoreError('重载后的规则与预期不一致。')
                after=client.request('GET','/configs')
                if after.get('mode')!=runtime.get('mode') or after.get('tun',{}).get('enable')!=runtime.get('tun',{}).get('enable'):
                    raise CoreError('重载后的模式或 TUN 状态改变。')
                result=dict(time=stamp(),action='restore' if restore else 'apply',ok=True,backup=str(backup),ruleCount=len(desired))
                save_json(self.applied,dict(owned=inserted,desired=desired,result=result))
                self.journal.unlink()
                return result
            except Exception:
                try:
                    self.recover()
                except Exception:
                    raise CoreError('应用失败且回滚未确认，请先恢复中断操作；备份保存在 data/backups。') from None
                raise CoreError('应用失败，已回滚到操作前的配置。') from None

    def recover(self):
        with self.lock:
            if not self.journal.exists(): return dict(ok=True,action='recover',time=stamp())
            j=read_json(self.journal,{})
            configpath=self.verge/'clash-verge.yaml'; scriptpath=Path(j['scriptPath'])
            for p, old, new in [(configpath,j['oldConfig'],j['newConfig']), (scriptpath,j['oldScript'],j['newScript'])]:
                if p.read_text(encoding='utf-8') not in (old,new):
                    raise ValueError('中断后配置被其他程序修改，请检查备份，停止自动恢复。')
            client=CoreClient(yaml.safe_load(j['oldConfig']))
            client.request('PUT','/configs?force=true',{'payload':j['oldConfig']})
            if live_signatures(client.request('GET','/rules')['rules']) != [signature(r) for r in yaml.safe_load(j['oldConfig'])['rules']]:
                raise CoreError('回滚规则未能确认。')
            write_atomic(scriptpath,j['oldScript']); write_atomic(configpath,j['oldConfig'])
            save_json(self.applied,j['previous'])
            self.journal.unlink()
            return dict(ok=True,action='recover',time=stamp())
