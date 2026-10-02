let token='', busy=false;
const $=id=>document.getElementById(id);
function notice(text,error=false){$('notice').textContent=text;$('notice').className=error?'error':'';}
function el(tag,text,className){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(className)n.className=className;return n;}
async function request(path,method='GET',body={}){const options={method};if(method!=='GET'){options.headers={'Content-Type':'application/json','X-Session-Token':token};options.body=JSON.stringify(body);}const r=await fetch(path,options);const data=await r.json();if(!r.ok)throw Error(data.error||'请求失败');return data;}
async function refresh(){const s=await request('/api/state');token=s.token;$('online').textContent=s.online?'已连接':'未连接';$('mode').textContent=s.online?`${s.mode==='rule'?'规则模式':s.mode} / TUN ${s.tun?'开启':'关闭'}`:'—';$('effective').textContent=`${s.persisted?'已写入':'待应用'} / ${s.effective?'已生效':'未确认'}`;$('count').textContent=String(s.targets.length);$('recover').hidden=!s.pendingRecovery;
 $('targets').replaceChildren();$('empty').hidden=s.targets.length>0;
 for(const t of s.targets){const row=el('div',undefined,'target-row');const info=el('div');info.append(el('div',t.value,'target-value'),el('span',t.label,'target-label'));info.title=t.source;const del=el('button','×');del.type='button';del.setAttribute('aria-label','删除 '+t.value);del.onclick=()=>perform(async()=>{await request('/api/targets/'+t.id,'DELETE');return '已删除并保存，请应用规则。';});row.append(el('span',t.kind==='folder'?'FOLDER':'DOMAIN','tag'),info,del);$('targets').append(row);}
 $('connections').replaceChildren();$('connection-count').textContent=s.connections.length+' 条连接';
 if(!s.connections.length)$('connections').append(el('div',s.online?'尚未观察到目标连接。请打开目标网站或运行目标程序，再刷新；未观察到连接不能证明已直连。':'内核未连接，无法读取实时通道。','no-connections'));
 for(const c of s.connections){const row=el('div',undefined,'connection');const info=el('div',c.host||c.destinationIP);info.append(el('small',c.processPath||c.process||'未识别进程'),el('small',`${c.network||''} · ${c.rule} · ${c.rulePayload||''}`));row.append(info,el('div',c.chains.join(' → '),'chain'));$('connections').append(row);}
 $('rules').textContent=s.rules.join('\n')||'无规则';$('inventory').textContent=s.executables.join('\n')||'无可读取的目录程序';
 if(s.pendingRecovery)notice('上次操作中断，请先恢复中断操作。',true);else if(s.error)notice(s.error,true);else if(s.mode!=='rule'&&s.online)notice('请在 Clash Verge 切换到规则模式，直连规则才能参与分流。',true);
 return s;
}
async function perform(action){if(busy)return;busy=true;document.querySelectorAll('button').forEach(n=>n.disabled=true);try{const message=await action();const s=await refresh();if(!s.pendingRecovery&&!s.error&&(!s.online||s.mode==='rule'))notice(message);}catch(e){notice(e.message,true);}finally{busy=false;document.querySelectorAll('button').forEach(n=>n.disabled=false);}}
$('refresh').onclick=()=>perform(async()=>{await refresh();return '状态已刷新。';});
$('kind').onchange=()=>{$('value').placeholder=$('kind').value==='folder'?'G:\\Naraka':'https://example.com';};
$('add-form').onsubmit=e=>{e.preventDefault();perform(async()=>{await request('/api/targets','POST',{kind:$('kind').value,value:$('value').value,label:$('label').value});$('value').value='';$('label').value='';return '目标已保存，请点击应用直连规则。';});};
$('apply').onclick=()=>perform(async()=>{const r=await request('/api/apply','POST');return `已应用 ${r.ruleCount} 条规则，已读取内核规则确认。既有连接需要重新连接。`;});
$('restore').onclick=()=>perform(async()=>{await request('/api/restore','POST');return '已撤销本工具规则，直连清单仍保留。';});
$('recover').onclick=()=>perform(async()=>{await request('/api/recover','POST');return '已恢复到中断操作之前的配置。';});
busy=true;document.querySelectorAll('button').forEach(n=>n.disabled=true);
refresh().catch(e=>notice(e.message,true)).finally(()=>{busy=false;document.querySelectorAll('button').forEach(n=>n.disabled=false);});
