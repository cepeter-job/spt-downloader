"""Owned detail observations, not decoded tax records or primary identity proof.

Callbacks retain bounded driver metadata only. A completed response is read once
on the caller's thread, checked, and written immediately. Driver body() and JSON
parsing can still allocate a whole body; budgets are not hard RAM/interrupt caps.

Exception-handling policy for this module:
- Driver probes can fail through Playwright/CDP or an adapter. Preserve the
  bounded unavailable-proof fallback and surrounding Stop checks.
- Never forward exception text into captured JSON or diagnostics.
"""
from contextlib import contextmanager, ExitStack
import hashlib
import json
from pathlib import Path
import re
import stat
import time
from urllib.parse import parse_qsl, unquote, urlparse
from uuid import uuid4

from coretax_json import (JsonSafetyError, PPH21_REFERENCE_URLS, UNIFIKASI_REFERENCE_URL,
                          CORPORATE_REFERENCE_REQUESTS, CORPORATE_REFERENCE_SOURCES, ORIGIN,
                          _capture_clock_interval, _capture_component_lifetime, _capture_l8_lifetime,
                          _capture_l7_lifetime, _capture_corporate_reference_providers,
                          _corporate_reference_builds, _capture_l10b_lifetime, _capture_l10c_lifetime,
                          _object_pairs, _reject_constant, _trusted_origin)
from spt_desktop import diagnostics
from spt_desktop.output_windows import DirectoryGuard, locked_file

MAX_RESPONSES = 1024
MAX_BODY_BYTES = 32 * 1024 * 1024
# Fixed reasons reported by the L7 child-history script; enum-only diagnostics.
_L7_JS_REASONS = frozenset({'budget', 'chain', 'enabled', 'roles', 'shape', 'document',
                            'removed', 'depth', 'unknown', 'visibility', 'identity',
                            'boundary', 'initial', 'detached'} | {
    kind + '_' + str(index)
    for kind in ('chain_owner', 'chain_form')
    for index in range(1, 5)} | {
    'chain_prefix_' + family + '_' + str(index)
    for family in ('ui', 'p', 'rsh', 'rshshr', 'other')
    for index in range(1, 5)})
MAX_TOTAL_BYTES = 128 * 1024 * 1024
DRAIN_SECONDS = 20
MAX_REQUEST_METADATA_BYTES = 65536
_SECRET_KEYS = frozenset({'password', 'passwd', 'pwd', 'authorization', 'cookie',
                          'setcookie', 'token', 'accesstoken', 'refreshtoken',
                          'idtoken', 'apikey', 'clientsecret', 'secret', 'sessionid'})
_SECRET_TEXT = re.compile(r'\bBearer\s+\S+|\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', re.I)
_BROWSER_CLOCK = '() => ({epoch_ms:Date.now(),timezone:Intl.DateTimeFormat().resolvedOptions().timeZone})'
_L10C_FINAL_SAMPLE = '''(h) => {
 // corporate-l10c-final-clock: the same last RPC owns child and end clock.
 const state=h.sample();
 return {state,clock:{epoch_ms:Date.now(),timezone:Intl.DateTimeFormat().resolvedOptions().timeZone}};
}'''
_COMPONENT_OWNERS = """() => {
 const visible=e=>{for(let p=e;p;p=p.parentElement){const s=getComputedStyle(p);
   if(p.hidden||s.display==='none'||s.visibility==='hidden'||s.visibility==='collapse')return false;}
   return !!e.getClientRects().length;};
 const count=s=>Array.from(document.querySelectorAll(s)).filter(visible).length;
 return {source_owner:count('rshshr-submitted-returnsheets')===1,
         detail_owner:count('rshshr-corporate-income-tax-return')===1};
}"""
_FINAL_LIFETIMES = """(d, histories) => {
 // corporate-final-lifetimes: one synchronous turn, not successive RPCs.
 // Only these already-owned history handles can supply child facts. Each
 // sample drains its MutationObserver; an unavailable sibling cannot hide a
 // changed one. No async work, DOM writes or business-value reads occur here.
 const read=h=>{if(!h)return null;try{return h.sample();}catch{return null;}};
 const l8=read(histories.l8),l7=read(histories.l7),l10b=read(histories.l10b),l10c=read(histories.l10c);
 let owners=null;
 try{owners=(""" + _COMPONENT_OWNERS + """)();}catch{}
 // The final clock belongs to this same turn: a later clock RPC could pump a
 // sibling replacement after its sample.
 return {same_document:d===document,owners,l8,l7,l10b,l10c,
   clock:{epoch_ms:Date.now(),timezone:Intl.DateTimeFormat().resolvedOptions().timeZone}};
}"""
_L7_HISTORY = """(d) => {
 // corporate-l7-history: independent of the L8 all-DOM budget.
 const selectors=['rshshr-corporate-income-tax-return','rshshr-citr-l7-form',
                  'rsh-citr-l7-grid1','p-table','table'];
 const hosts=selectors.slice(0,3).join(','), candidates=selectors.join(',');
 const state={available:d===document&&!d.querySelector(hosts),changed:false,complete:false};
 let roles=[null,null,null,null,null],ancestors=new Set(),remaining=4096;
 let tab=null,panel=null,started=false,ended=false;
 // Fixed reason for the first refusal; value-free and never a DOM fact.
 let reason='ok';
 const note=name=>{if(reason==='ok')reason=name;};
 reason=d!==document?'document':(state.available?'ok':'initial');
 const observer=new MutationObserver(records=>process(records));
 const unavailable=()=>{note('unknown');state.available=false;observer.disconnect();};
 const debit=()=>{if(--remaining<0){note('budget');unavailable();return false;}return true;};
 const remember=node=>{
   let depth=0;
   for(let p=node.parentElement;p;p=p.parentElement){
     ancestors.add(p);
     if(++depth>64||ancestors.size>64){note('depth');unavailable();return;}
   }
 };
 const adopt=(node,index,removed)=>{
   if(!debit())return;
   if(removed){state.changed=true;return;}
   if(roles[index]&&roles[index]!==node){state.changed=true;return;}
   if(!roles[index]){roles[index]=node;remember(node);}
   if(!node.isConnected||node.ownerDocument!==d)state.changed=true;
 };
 const inside=target=>roles[1]&&(target===roles[1]||roles[1].contains(target));
 const inspect=(node,target,removed)=>{
   if(node.nodeType!==1)return false;
   // Exact structural queries, never traversal of business row/text nodes.
   // Query-engine/MutationObserver allocations are not claimed as a hard cap.
   const found=node.querySelectorAll(candidates);
   let relevant=false;
   const visit=element=>{
     const index=selectors.findIndex(selector=>element.matches(selector));
     if(index<3){relevant=true;adopt(element,index,removed);return;}
     const scope=inside(element)||inside(target)||roles.includes(element);
     if(scope){relevant=true;adopt(element,index,removed);}
     else if(!target.isConnected&&(roles.includes(target)||ancestors.has(target))){
       // Only a retained role or a remembered chain ancestor is provable L7
       // attribution; a detached contains() check cannot prove ownership, so
       // unrelated document teardown is not L7 evidence.
       relevant=true;note('detached');if(debit())unavailable();
     }
   };
   if(node.matches(candidates))visit(node);
   for(const element of found){if(remaining<0)break;visit(element);}
   return relevant;
 };
 const process=records=>{
   if(!state.available)return;
   for(const record of records){
     let relevant=false,removedStructure=false;
     const local=inside(record.target);
     const body=local&&record.target.nodeType===1&&
       !!record.target.closest('thead,tbody,tfoot');
     for(const node of record.removedNodes){
       if(node.nodeType!==1)continue;
       if(roles.some(role=>role&&(node===role||node.contains(role)))||ancestors.has(node)){
         state.changed=true;relevant=true;
       }
       if(inspect(node,record.target,true))relevant=true;
       // Removed ordinary wrappers can lose their children before delivery.
       // Their continuity cannot be reconstructed from final selectors alone.
       if(local&&!body)removedStructure=true;
       if(remaining<0)break;
     }
     for(const node of record.addedNodes){
       if(remaining<0)break;
       if(inspect(node,record.target,false))relevant=true;
     }
     if(local&&!body)relevant=true;
     if(relevant&&!debit())break;
     if(removedStructure&&!state.changed){note('removed');unavailable();}
     if(remaining<0)break;
   }
 };
 const snapshot=()=>{
   if(d!==document){note('document');state.changed=true;return false;}
   if(!state.available)return false;
   if(roles.some(role=>!role)){note('roles');return false;}
   if(roles.some(role=>!role.isConnected||role.ownerDocument!==d)){
     state.changed=true;return false;
   }
   const unique=selectors.slice(0,3).every((selector,index)=>{
     const nodes=d.querySelectorAll(selector);return nodes.length===1&&nodes[0]===roles[index];
   })&&roles[1].querySelectorAll('p-table').length===1&&roles[1].querySelectorAll('table').length===1;
   if(!unique){note('shape');state.changed=true;return false;}
   // Known framework outlets may be transparent; another business component
   // cannot lend its children to the declared corporate owner chain.
   const transparent=new Set(['p-tabview','p-tabpanel','ui-grid-offline']);
   const corporateHost=/^rsh(shr)?-(citr|corporate)-/;
   // Framework outlets (PrimeNG p-*, ui-*) and the corporate component family
   // are hosts; another *-form or an unknown business tag is not.
   const frameworkHost=/^(p|ui)-/;
   const family=name=>name.startsWith('rshshr-')?'rshshr':name.startsWith('rsh-')?'rsh':
     name.startsWith('ui-')?'ui':name.startsWith('p-')?'p':'other';
   const chain=roles.slice(1).every((role,index)=>{
     if(role.closest(selectors[index])!==roles[index]){note('chain_owner_'+(index+1));return false;}
     for(let p=role.parentElement;p&&p!==roles[index];p=p.parentElement){
       if(p.localName.includes('-')&&!transparent.has(p.localName)){
         if(!p.localName.endsWith('-form')&&
            (corporateHost.test(p.localName)||frameworkHost.test(p.localName)))continue;
         note(p.localName.endsWith('-form')?'chain_form_'+(index+1)
              :'chain_prefix_'+family(p.localName)+'_'+(index+1));
         return false;
       }
     }
     return true;
   });
   // Unknown initial ancestry is unsupported, not an invented ownership fact.
   if(!chain){note('chain');if(started)state.changed=true;else unavailable();return false;}
   return true;
 };
 const enabled=visible=>{
   if(!tab||!panel||!tab.isConnected||!panel.isConnected||tab.ownerDocument!==d||panel.ownerDocument!==d)return false;
   const form=roles[1],li=tab.closest('li'),view=form.closest('.p-tabview');
   const id=tab.getAttribute('aria-controls'),href=tab.getAttribute('href');
   if(!li||!view||form.closest('.p-tabview-panel')!==panel||tab.closest('.p-tabview')!==view||
      !roles[0].contains(view)||!panel.matches('.p-tabview-panel')||!id||panel.id!==id||
      [...view.querySelectorAll('[id]')].filter(e=>e.id===id).length!==1||
      tab.textContent.trim()!=='L7'||li.classList.contains('p-disabled')||
      tab.getAttribute('aria-disabled')==='true'||!(href===null||href===''||href==='#'||href==='#'+id))return false;
   if(!visible)return true;
   for(let p=form;p;p=p.parentElement){const style=getComputedStyle(p);
     if(p.hidden||style.display==='none'||style.visibility==='hidden'||style.visibility==='collapse')return false;}
   return !!form.getClientRects().length&&!!tab.getClientRects().length;
 };
 observer.observe(d,{childList:true,subtree:true});
 const sample=()=>{
   process(observer.takeRecords());
   const valid=snapshot();
   if(started&&valid&&!enabled(false)){note('visibility');state.changed=true;}
   state.complete=!!(state.available&&!state.changed&&valid&&started&&ended);
   return {...state};
 };
 return {sample,why:()=>reason,bind:args=>{
   process(observer.takeRecords());
   if(!snapshot())return {...state};
   if(args.form!==roles[1]||args.grid!==roles[2]||args.table!==roles[4]){note('identity');state.changed=true;}
   if(args.phase==='start'&&!started){tab=args.tab;panel=args.panel;}
   else if(args.phase!=='end'||!started||ended||tab!==args.tab||panel!==args.panel){note('boundary');state.changed=true;}
   if(!enabled(true)){note('enabled');if(started)state.changed=true;else unavailable();}
   if(state.available&&!state.changed){if(args.phase==='start')started=true;else ended=true;}
   return sample();
 },disconnect:()=>{
   observer.disconnect();roles=[];ancestors.clear();tab=null;panel=null;
 }};
}"""


_L10B_HISTORY = """(d) => {
 // corporate-l10b-history: source custody only, no business input/checked reads.
 const rootSelector='rshshr-corporate-income-tax-return',formSelector='rshshr-citr-l10b-form';
 const selectors=[rootSelector,formSelector],query=selectors.join(',');
 const state={available:d===document&&!d.querySelector(query),changed:false,complete:false};
 let root=null,form=null,tab=null,panel=null,view=null,started=false,ended=false,remaining=4096;
 const ancestors=new Set();
 const observer=new MutationObserver(records=>process(records));
 const unavailable=()=>{state.available=false;observer.disconnect();};
 const debit=()=>{if(--remaining<0){unavailable();return false;}return true;};
 const adopt=(node,removed)=>{
   if(!debit())return;
   const isRoot=node.matches(rootSelector),previous=isRoot?root:form;
   if(removed||(previous&&previous!==node)){state.changed=true;return;}
   if(isRoot)root=node;else form=node;
   let depth=0;
   for(let p=node.parentElement;p;p=p.parentElement){
     ancestors.add(p);if(++depth>64||ancestors.size>128){unavailable();break;}
   }
 };
 const inspect=(node,removed)=>{
   if(node.nodeType!==1)return false;
   let relevant=false;
   if(node.matches(query)){adopt(node,removed);relevant=true;}
   for(const child of node.querySelectorAll(query)){
     if(!state.available)break;adopt(child,removed);relevant=true;
   }
   return relevant;
 };
 const enabled=visible=>{
   if(!root||!form||!tab||!panel||!view||![root,form,tab,panel,view].every(e=>e.isConnected&&e.ownerDocument===d))return false;
   const li=tab.closest('li'),id=tab.getAttribute('aria-controls'),href=tab.getAttribute('href');
   if(!li||form.closest('.p-tabview')!==view||form.closest('.p-tabview-panel')!==panel||
      tab.closest('.p-tabview')!==view||!root.contains(view)||!id||panel.id!==id||
      [...view.querySelectorAll('[id]')].filter(e=>e.id===id).length!==1||
      tab.textContent.trim()!=='L10-B'||li.classList.contains('p-disabled')||
      tab.getAttribute('aria-disabled')==='true'||!(href===null||href===''||href==='#'||href==='#'+id))return false;
   if(!visible)return true;
   for(let p=form;p;p=p.parentElement){const s=getComputedStyle(p);
     if(p.hidden||s.display==='none'||s.visibility==='hidden'||s.visibility==='collapse')return false;}
   return !!form.getClientRects().length&&!!tab.getClientRects().length;
 };
 const snapshot=()=>{
   if(d!==document){state.changed=true;return false;}
   if(!state.available||!root||!form)return false;
   if(![root,form].every(e=>e.isConnected&&e.ownerDocument===d)||
      selectors.some((s,i)=>{const nodes=d.querySelectorAll(s);return nodes.length!==1||nodes[0]!==[root,form][i];})){
     state.changed=true;return false;
   }
   if(form.closest(rootSelector)!==root){unavailable();return false;}
   for(let p=form.parentElement;p&&p!==root;p=p.parentElement){
     if(p.localName.includes('-')&&(p.localName.endsWith('-form')||
        !/^(p-|ui-|rsh(shr)?-(citr|corporate)-)/.test(p.localName))){
       if(started)state.changed=true;else unavailable();return false;
     }
   }
   return true;
 };
 const process=records=>{
   if(!state.available)return;
   for(const record of records){
     if(record.type==='attributes'){
       if(!started)continue;
       const e=record.target,name=record.attributeName,li=tab&&tab.closest('li');
       if(e===li&&name==='class'&&((record.oldValue||'').split(/\\s+/).includes('p-disabled')||li.classList.contains('p-disabled')))
         state.changed=true;
       if(e===tab&&['aria-controls','aria-disabled','href'].includes(name)&&record.oldValue!==e.getAttribute(name))
         state.changed=true;
       if(e===panel&&name==='id'&&record.oldValue!==e.id)state.changed=true;
       if((e===tab||e===panel||e===li)&&!debit())break;
       continue;
     }
     let relevant=!!form&&(record.target===form||form.contains(record.target));
     for(const node of record.removedNodes){
       if(node.nodeType!==1)continue;
       if([root,form,tab,panel,view].some(e=>e&&(node===e||node.contains(e)))||ancestors.has(node)){
         state.changed=true;relevant=true;
       }
       if(inspect(node,true))relevant=true;
     }
     for(const node of record.addedNodes){if(!state.available)break;if(inspect(node,false))relevant=true;}
     if(relevant&&!debit())break;
   }
 };
 observer.observe(d,{subtree:true,childList:true,attributes:true,attributeOldValue:true,
                    attributeFilter:['class','aria-controls','aria-disabled','href','id']});
 const sample=()=>{
   process(observer.takeRecords());const valid=snapshot();
   if(started&&valid&&!enabled(false))state.changed=true;
   state.complete=!!(state.available&&!state.changed&&valid&&started&&ended);
   return {...state};
 };
 return {sample,bind:args=>{
   process(observer.takeRecords());if(!snapshot())return {...state};
   if(args.form!==form)state.changed=true;
   if(args.phase==='start'&&!started){tab=args.tab;panel=args.panel;view=form.closest('.p-tabview');}
   else if(args.phase!=='end'||!started||ended||tab!==args.tab||panel!==args.panel)state.changed=true;
   if(!enabled(true)){if(started)state.changed=true;else unavailable();}
   if(state.available&&!state.changed){if(args.phase==='start')started=true;else ended=true;}
   return sample();
 },disconnect:()=>{observer.disconnect();root=form=tab=panel=view=null;ancestors.clear();}};
}"""


_L10C_HISTORY = """(d) => {
 // corporate-l10c-history: a C-owned child, not a shared registry or B alias.
 const selectors=['rshshr-corporate-income-tax-return','rshshr-citr-main-form',
   'rshshr-citr-l10c-form','rsh-citr-l10c-grid1','ui-grid-offline','p-table','table'];
 const hosts=selectors.slice(0,4).join(','), candidates=selectors.join(',');
 const state={available:d===document&&!d.querySelector(hosts),changed:false,complete:false,why:''};
 let roles=Array(7).fill(null),ancestors=new Set(),controls=null,tab=null,panel=null;
 let started=false,ended=false,remaining=4096;
 const stop=why=>{state.available=false;state.why=why||'unknown';observer.disconnect();};
 const debit=()=>{if(--remaining<0){stop('budget');return false;}return true;};
 const inside=node=>roles[2]&&(node===roles[2]||roles[2].contains(node));
 const remember=node=>{let depth=0;for(let p=node.parentElement;p;p=p.parentElement){
   ancestors.add(p);if(++depth>64||ancestors.size>128){stop('ancestors');return;}}};
 const adopt=(node,index,removed)=>{
   if(!debit())return;
   if(removed||roles[index]&&roles[index]!==node){state.changed=true;return;}
   if(!roles[index]){roles[index]=node;remember(node);}
   if(!node.isConnected||node.ownerDocument!==d)state.changed=true;
 };
 const inspect=(node,target,removed)=>{
   if(node.nodeType!==1)return;
   const visit=element=>{
     const index=selectors.findIndex(selector=>element.matches(selector));
     if(index<4||inside(element)||inside(target)||roles.includes(element))adopt(element,index,removed);
     else if(!target.isConnected&&(roles.includes(target)||ancestors.has(target)))stop('target_disconnected');
   };
   if(node.matches(candidates))visit(node);
   for(const element of node.querySelectorAll(candidates)){if(remaining<0)break;visit(element);}
 };
 const process=records=>{
   if(!state.available)return;
   for(const record of records){
     if(record.type==='attributes'){
       // Keep transient disabled/re-enabled and original identity changes. No
       // input value, checked state, Angular instance or business text is read.
       if(record.attributeName==='class'){
         const li=tab&&tab.closest('li');
         if(record.target!==li||
            (record.oldValue||'').split(/\\s+/).includes('p-disabled')===li.classList.contains('p-disabled'))continue;
       }
       if(started&&(inside(record.target)&&record.target.closest('thead,tfoot')||
          roles.includes(record.target)||controls&&controls.includes(record.target)||
          record.target===tab||tab&&record.target===tab.closest('li'))){
         state.changed=true;if(!debit())break;
       }
       continue;
     }
     if(record.type==='characterData'){
       if(started&&inside(record.target)&&record.target.parentElement?.closest('thead,tfoot'))state.changed=true;
       continue;
     }
     if(started&&inside(record.target)&&record.target.closest('thead,tfoot'))state.changed=true;
     if(started&&inside(record.target)&&[...record.removedNodes,...record.addedNodes].some(node=>
       node.nodeType===1&&(node.matches('thead,tfoot')||node.querySelector('thead,tfoot'))))state.changed=true;
     for(const node of record.removedNodes){
       if(node.nodeType!==1)continue;
       if(inside(record.target)&&!roles[4]?.contains(record.target)&&
          (node.matches('input,p-radiobutton')||node.querySelector('input,p-radiobutton')))state.changed=true;
       if(roles.some(role=>role&&(node===role||node.contains(role)))||ancestors.has(node)||
          controls&&controls.some(control=>node===control||node.contains(control)))state.changed=true;
       inspect(node,record.target,true);
     }
     for(const node of record.addedNodes){inspect(node,record.target,false);if(remaining<0)break;}
     if(started&&inside(record.target)&&!record.target.closest('thead,tbody,tfoot')){
       if(!debit())break;
       // Unknown non-row/control restructuring is not reconstructed from its
       // final selectors after the fact.
       if(record.removedNodes.length)state.changed=true;
     }
     if(remaining<0)break;
   }
 };
 const observer=new MutationObserver(process);
 observer.observe(d,{childList:true,subtree:true,attributes:true,attributeOldValue:true,characterData:true,
   attributeFilter:['disabled','aria-disabled','aria-controls','href','id','class',
                    'formcontrolname','type','name','colspan','rowspan']});
 const snapshot=()=>{
   if(d!==document){state.changed=true;return false;}
   if(!state.available||roles.some(role=>!role))return false;
   // Reuse the existing parent structural reader in this same synchronous
   // sample, including the final C+clock RPC. Never trust an earlier parent.
   const owners=(""" + _COMPONENT_OWNERS + """)();
   if(owners.source_owner!==false||owners.detail_owner!==true){state.changed=true;return false;}
   if(roles.some(role=>!role.isConnected||role.ownerDocument!==d)){state.changed=true;return false;}
   const unique=selectors.slice(0,4).every((selector,index)=>{
     const nodes=d.querySelectorAll(selector);return nodes.length===1&&nodes[0]===roles[index];});
   if(!unique||roles[1].closest(selectors[0])!==roles[0]||
      roles[2].closest(selectors[0])!==roles[0]){state.changed=true;return false;}
   if(!roles[6].tHead||roles[6].tFoot&&roles[6].tFoot.rows.length){state.changed=true;return false;}
   for(let index=3;index<roles.length;index++){
     const owner=index===3?2:index-1;
     const nodes=roles[owner].querySelectorAll(selectors[index]);
     if(nodes.length!==1||nodes[0]!==roles[index]||
        roles[index].closest(selectors[owner])!==roles[owner]){state.changed=true;return false;}
     for(let p=roles[index].parentElement;p&&p!==roles[owner];p=p.parentElement){
       if(p.localName.includes('-')&&(p.localName.endsWith('-form')||
          !/^(p|ui|rsh-citr|rshshr-citr)-/.test(p.localName))){stop('owner_chain');return false;}
     }
   }
   const form=roles[2];
   const years=form.querySelectorAll('input[formcontrolname="PeriodYear"]');
   const tins=form.querySelectorAll('input[formcontrolname="CollectorTin"]');
   const radios=form.querySelectorAll('p-radiobutton[formcontrolname="Question"]');
   const businessInputs=[...form.querySelectorAll('input')].filter(node=>!(roles[4].contains(node)&&
     node.closest('p-paginator')&&node.closest('p-table')===roles[5]));
   if(years.length!==1){stop('controls_years');return false;}
   if(tins.length!==1){stop('controls_tins');return false;}
   if(radios.length!==2){stop('controls_radios');return false;}
   if(businessInputs.length!==4){stop('controls_business');return false;}
   const inputs=[...radios].map(radio=>radio.querySelectorAll('input[type="radio"]'));
   if(inputs.some(nodes=>nodes.length!==1)){stop('radio_inputs');return false;}
   const current=[years[0],tins[0],...radios,...inputs.map(nodes=>nodes[0])];
   if(current.some(node=>node.closest(selectors[2])!==form)||
      current.filter(node=>node.localName==='input').some(node=>!node.disabled)){stop('current_controls');return false;}
   if(controls&&current.some((node,index)=>node!==controls[index])){state.changed=true;return false;}
   if(!controls)controls=current;
   return true;
 };
 const enabled=visible=>{
   if(!tab||!panel||!tab.isConnected||!panel.isConnected||
      tab.ownerDocument!==d||panel.ownerDocument!==d)return false;
   const form=roles[2],view=form.closest('.p-tabview'),li=tab.closest('li');
   const id=tab.getAttribute('aria-controls'),href=tab.getAttribute('href');
   if(!view||!li||!roles[0].contains(view)||form.closest('.p-tabview-panel')!==panel||
      tab.closest('.p-tabview')!==view||!panel.matches('.p-tabview-panel')||!id||panel.id!==id||
      view.querySelectorAll('[id="'+CSS.escape(id)+'"]').length!==1||
      tab.textContent.trim()!=='L10-C'||li.classList.contains('p-disabled')||
      tab.getAttribute('aria-disabled')==='true'||!(href===null||href===''||href==='#'||href==='#'+id))return false;
   if(!visible)return true;
   for(let p=form;p;p=p.parentElement){const style=getComputedStyle(p);
     if(p.hidden||style.display==='none'||style.visibility==='hidden'||style.visibility==='collapse')return false;}
   return !!form.getClientRects().length&&!!tab.getClientRects().length;
 };
 const sample=()=>{
   process(observer.takeRecords());
   const valid=snapshot();
   if(started&&valid&&!enabled(false))state.changed=true;
   state.complete=!!(state.available&&!state.changed&&valid&&started&&ended);
   return {...state};
 };
 return {sample,bind:args=>{
   process(observer.takeRecords());
   if(!snapshot())return {...state};
   if(args.form!==roles[2]||args.grid!==roles[3]||args.table!==roles[6])state.changed=true;
   if(args.phase==='start'&&!started){tab=args.tab;panel=args.panel;}
   else if(args.phase!=='end'||!started||ended||tab!==args.tab||panel!==args.panel)state.changed=true;
   if(!enabled(true)){if(started)state.changed=true;else stop('enabled');}
   if(state.available&&!state.changed){if(args.phase==='start')started=true;else ended=true;}
   return sample();
 },disconnect:()=>{observer.disconnect();roles=[];ancestors.clear();controls=null;tab=null;panel=null;}};
}"""


_L8_HISTORY = """(d) => {
 const rootSelector='rshshr-corporate-income-tax-return';
 const dependents='rshshr-citr-l7-form,rshshr-citr-l13a-form,rshshr-citr-l13b-form';
 const relevant=rootSelector+','+dependents;
 const state={initial_clear:d===document&&!d.querySelector(relevant),
   root_seen:false,root_changed:false,dependent_seen:false};
 let root=null,remaining=4096;
 const visit=(node,removed)=>{
   if(--remaining<0){state.initial_clear=false;return;}
   if(node.nodeType!==1)return;
   if(node.matches(dependents))state.dependent_seen=true;
   if(node.matches(rootSelector)){
     if(removed)state.root_changed=true;
     else if(root&&root!==node)state.root_changed=true;
     else {root=node;state.root_seen=true;}
   }
 };
 // Only the L8 root and a dependent form are L8 evidence; a large but clean
 // grid render must not exhaust the budget. Unrelated nodes are not visited.
 const inspect=(node,removed)=>{
   if(node.nodeType!==1)return;
   const hits=node.matches(relevant)?[node]:[];
   for(const el of node.querySelectorAll(relevant))hits.push(el);
   for(const el of hits){if(!state.initial_clear)break;visit(el,removed);}
 };
 const process=records=>{
   if(!state.initial_clear)return;
   for(const record of records){
     for(const node of record.removedNodes){inspect(node,true);if(!state.initial_clear)break;}
     for(const node of record.addedNodes){inspect(node,false);if(!state.initial_clear)break;}
     if(!state.initial_clear)break;
   }
 };
 const observer=new MutationObserver(process);
 observer.observe(d,{childList:true,subtree:true});
 return {sample:()=>{
   process(observer.takeRecords());
   if(state.initial_clear&&root&&(!root.isConnected||root.ownerDocument!==d))state.root_changed=true;
   return {...state};
 },disconnect:()=>observer.disconnect()};
}"""


def _secret_key(value):
    return re.sub(r'[^a-z0-9]', '', value.casefold()) in _SECRET_KEYS


def _json(raw):
    return json.loads(raw, object_pairs_hook=_object_pairs, parse_constant=_reject_constant)


def _has_secret(value, depth=0):
    if depth > 64:
        raise ValueError('JSON nesting exceeds capture privacy inspection')
    if isinstance(value, dict):
        return any(_secret_key(key) or _has_secret(item, depth + 1) for key, item in value.items())
    if isinstance(value, list):
        return any(_has_secret(item, depth + 1) for item in value)
    if isinstance(value, str):
        if _SECRET_TEXT.search(value):
            return True
        # Embedded and doubly encoded form JSON has the same privacy boundary.
        text = value.lstrip()
        if text.startswith(('{', '[', '"')):
            try:
                decoded = _json(text)
            except (ValueError, JsonSafetyError, RecursionError):
                raise ValueError('Embedded JSON cannot be safely privacy inspected') from None
            return decoded != value and _has_secret(decoded, depth + 1)
    return False


def _safe_url(value):
    if not _trusted_origin(value):
        return False
    parsed = urlparse(value)
    if parsed.fragment or _SECRET_TEXT.search(unquote(value)):
        return False
    try:
        return not any(_secret_key(unquote(key)) or _has_secret(item)
                       for key, item in parse_qsl(parsed.query, keep_blank_values=True))
    except (ValueError, JsonSafetyError, RecursionError):
        return False


def _ordinary_directory(path):
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode)
            or getattr(info, 'st_file_attributes', 0) & 0x400):
        raise ValueError('Private capture ancestor is not an ordinary directory')
    return info.st_dev, info.st_ino


class DetailJsonCapture:
    """Enter before inspected View; bind only its verified page, then drain."""

    def __init__(self, context, page, record, scope, folder, *, ordinal=1, check_cancel=None):
        if (not isinstance(scope, (list, tuple)) or len(scope) != 3
                or not isinstance(scope[0], str) or not re.fullmatch(r'[0-9]{16}', scope[0])
                or type(scope[1]) is not int or not 1900 <= scope[1] <= 2100
                or scope[2] not in ('period', 'submission')):
            raise JsonSafetyError('Invalid private capture scope; values are not normalized')
        if type(ordinal) is not int or ordinal < 1:
            raise JsonSafetyError('Private capture ordinal must be a positive integer')
        if (not isinstance(record, dict) or not isinstance(record.get('record_id'), str)
                or not record['record_id'] or record['record_id'] != record['record_id'].strip()
                or '/' in record['record_id'] or '\\' in record['record_id']):
            raise JsonSafetyError('Missing literal selected record identity')
        source = record.get('list_url')
        if not _safe_url(source):
            raise JsonSafetyError('Private capture source is not authorized')
        match = re.fullmatch(r'/returnsheets/id-ID/[^/]*returnsheets/([^/]+)/?', urlparse(source).path)
        if not match or page.context is not context:
            raise JsonSafetyError('Private capture taxpayer or browser context is unverified')
        root = Path(folder)
        if '..' in root.parts:
            raise JsonSafetyError('Private capture path contains parent traversal')
        self.context = context
        self.page = page
        self.folder = root.absolute()
        self.scope = list(scope)
        self.record_id = record['record_id']
        meta = record.get('meta')
        tax = meta.get('Jenis Pajak') if isinstance(meta, dict) else None
        fields = record.get('source_fields', {})
        corporate = (tax == 'PPh Badan' and isinstance(fields, dict)
                     and fields.get('TaxTypeCode') == 'ICT_RCIT'
                     and fields.get('ReturnSheetTypeCode') == 'ICT_RCITR')
        self._reference_urls = (PPH21_REFERENCE_URLS if tax == 'PPh Pasal 21/26' else
                                (UNIFIKASI_REFERENCE_URL,) if tax == 'PPh Unifikasi' else
                                tuple(CORPORATE_REFERENCE_REQUESTS) if corporate else ())
        self.source_url = source
        self.taxpayer_id = match.group(1)
        self.ordinal = ordinal
        self.check_cancel = check_cancel
        self.attempt = uuid4().hex
        self._relative = Path('returns', 'json', f'{ordinal:04d}', self.attempt)
        self._guard = DirectoryGuard()
        self._listeners = []
        self._requests = {}
        self._observations = []
        self._active = False
        self._bound = None
        self._bound_url = None
        self._seen = 0
        self._read_bytes = 0
        self._responses = []
        self._reasons = []
        self._result = None
        self._manifest_hash = None
        self._clock_start = None
        self._reference_providers = None
        self._reference_providers_attempted = False
        self._corporate = corporate
        self._view_called = False
        self._component_document = None
        self._component_listener = None
        self._component_transitions = 0
        self._component_target = None
        self._component_invalid = False
        self._component_observed = False
        self._component_started = False
        self._l8_history = None
        self._l8_requested = False
        self._l8_refusal = None
        self._l7_history = None
        self._l7_requested = False
        self._l7_unavailable = False
        self._l10b_history = None
        self._l10b_requested = False
        self._l10b_unavailable = False
        self._l10c_history = None
        self._l10c_requested = False
        self._l10c_offered = False
        self._l10c_unavailable = False
        self._l10c_bind_reason = None
        self._l10c_state_reason = None
        self._l10c_unavailable_why = ''
        self._l10c_clock_end = None
        self._final_clock = None
        from coretax_corporate_l10d import L10DHistory
        self._l10d_history = L10DHistory()
        self._counts = {'accepted': 0, 'pending': 0, 'excluded': 0, 'failed': 0}
        self._limits = {'responses': MAX_RESPONSES, 'body_bytes': MAX_BODY_BYTES,
                        'attempt_bytes': MAX_TOTAL_BYTES, 'drain_seconds': DRAIN_SECONDS}

    def _cancel(self, callback=None):
        if self.check_cancel:
            self.check_cancel()
        if callback is not None and callback is not self.check_cancel:
            callback()

    def _reason(self, reason):
        if reason not in self._reasons:
            self._reasons.append(reason)

    def _hold(self, path):
        expected = {parent: _ordinary_directory(parent) for parent in reversed([path, *path.parents])}
        self._guard.include(expected)

    def _sample_clock(self, page, check_cancel=None):
        """Optional browser environment evidence; driver failures reveal no text."""
        self._cancel(check_cancel)
        try:
            sample = page.evaluate(_BROWSER_CLOCK)
        except Exception:
            # Driver probes against test doubles or CDP may raise arbitrary errors.
            # The fallback is unavailable proof; no exception text is forwarded.
            sample = None
        self._cancel(check_cancel)
        if not isinstance(sample, dict) or set(sample) != {'epoch_ms', 'timezone'}:
            return None
        try:
            _capture_clock_interval({'attempt': self.attempt, 'start_ms': sample['epoch_ms'],
                                     'end_ms': sample['epoch_ms'], 'timezone': sample['timezone']}, self.attempt)
        except JsonSafetyError:
            return None
        return dict(sample)

    def __enter__(self):
        self._cancel()
        if self._active or self._listeners or self._result is not None:
            raise JsonSafetyError('Private capture attempt cannot be restarted')
        try:
            self._hold(self.folder)
            current = self.folder
            for name in self._relative.parts:
                self._cancel()
                current = current / name
                current.mkdir(exist_ok=name != self.attempt)
                self._hold(current)
            self._clock_start = self._sample_clock(self.page)
            self._active = True
            for event, callback in (('request', self._on_request), ('response', self._on_response),
                                    ('requestfinished', self._on_finished), ('requestfailed', self._on_failed)):
                self.context.on(event, callback)
                self._listeners.append((event, callback))
            return self
        except (OSError, ValueError):
            self.close()
            raise JsonSafetyError('Private capture folder cannot be safely acquired') from None
        except BaseException:
            self.close()
            raise

    def _detail_matches(self, value):
        if not _safe_url(value) or not urlparse(value).path.startswith('/returnsheets/'):
            return False
        parts = urlparse(value).path.split('/')
        return self.taxpayer_id in parts and self.record_id in parts

    def _component_detail_matches(self, value):
        if not self._detail_matches(value):
            return False
        parsed = urlparse(value)
        return (not parsed.params and parsed.query == 'view=true' and not parsed.fragment and re.fullmatch(
            r'/returnsheets/id-ID/corporate-income-tax-return/' + re.escape(self.taxpayer_id)
            + '/' + re.escape(self.record_id) + r'/ICT_RCIT/[^/%\\]+', parsed.path) is not None)

    def _component_probe(self, operation, check_cancel=None):
        self._cancel(check_cancel)
        try:
            value = operation()
        except Exception:
            # Driver failure is unavailable proof; no exception text is forwarded.
            value = None
        self._cancel(check_cancel)
        return value

    def begin_readonly_view(self):
        """Called only after the controller inspects one exact View control."""
        self._cancel()
        if self._view_called:
            raise JsonSafetyError('Inspected View authorization cannot be reused')
        self._view_called = True
        if (not self._active or not self._corporate or self.page.url != self.source_url
                or self.source_url != ORIGIN + '/returnsheets/id-ID/submitted-returnsheets/' + self.taxpayer_id
                or getattr(self.context, '_spt_financial_route_policy', None) != 'service_workers_blocked'):
            return None
        self._component_listener = self._on_component_navigation
        try:
            self.page.on('framenavigated', self._component_listener)
        except Exception:
            self._component_listener = None
            self._cancel()
            return None
        def retain_document():
            self._component_document = self.page.evaluate_handle('() => document')
            return self._component_document
        self._component_probe(retain_document)
        if self._component_document is None:
            return None
        self._l10d_history.arm(self._component_document, self._cancel)
        def retain_l7_history():
            # Retain before the post-RPC Stop check so close owns the handle
            # even when cancellation arrives with the installation reply.
            self._l7_history = self._component_document.evaluate_handle(_L7_HISTORY)
            return self._l7_history
        self._l7_probe(retain_l7_history)
        self._l7_arm_state()
        def retain_l10b_history():
            self._l10b_history = self._component_document.evaluate_handle(_L10B_HISTORY)
            return self._l10b_history
        self._l7_probe(retain_l10b_history)
        def retain_l8_history():
            self._l8_history = self._component_document.evaluate_handle(_L8_HISTORY)
            return self._l8_history
        self._component_probe(retain_l8_history)
        def retain_l10c_history():
            self._l10c_history = self._component_document.evaluate_handle(_L10C_HISTORY)
            return self._l10c_history
        self._l10c_probe(retain_l10c_history)
        self._l8_history = self._component_probe(
            lambda: self._component_document.evaluate_handle(_L8_HISTORY))
        owners = self._component_probe(lambda: self.page.evaluate(_COMPONENT_OWNERS))
        same = self._component_probe(lambda: self._component_document.evaluate('(d) => d === document'))
        if owners != {'source_owner': True, 'detail_owner': False} or same is not True:
            return None
        self._component_started = True
        if self.page.url != self.source_url or self._component_transitions:
            self._component_invalid = True
        return None

    def _on_component_navigation(self, frame):
        if not self._active or self._result is not None:
            return
        try:
            if frame is not self.page.main_frame:
                return
            self._component_transitions += 1
            if self._component_transitions != 1 or not self._component_detail_matches(frame.url):
                self._component_invalid = True
            else:
                self._component_target = frame.url
        except Exception:
            self._component_invalid = True

    def observe_component_lifetime(self, *, check_cancel=None):
        """Value-free retained Document and structural owner evidence only."""
        self._cancel(check_cancel)
        self._verify_binding()
        if not self._component_started:
            return None
        if self._component_invalid:
            raise JsonSafetyError('Observed submitted component lifetime changed')
        if (self._component_document is None or self._bound is not self.page
                or self._component_transitions != 1 or self._component_target != self._bound_url):
            return None
        same_before = self._component_probe(
            lambda: self._component_document.evaluate('(d) => d === document'), check_cancel)
        owners = self._component_probe(lambda: self.page.evaluate(_COMPONENT_OWNERS), check_cancel)
        same_after = self._component_probe(
            lambda: self._component_document.evaluate('(d) => d === document'), check_cancel)
        self._verify_binding()
        if (same_before is False or same_after is False or self._component_invalid
                or self._component_observed and owners != {'source_owner': False, 'detail_owner': True}):
            raise JsonSafetyError('Observed submitted component lifetime changed')
        if same_before is not True or same_after is not True or owners != {'source_owner': False, 'detail_owner': True}:
            return None
        proof = _capture_component_lifetime({'attempt': self.attempt,
            'kind': 'corporate-submitted-spa-v1', 'record_id': self.record_id,
            'source_url': self.source_url, 'detail_url': self._bound_url,
            'transition_count': 1, 'same_document': True, 'source_owner': True, 'detail_owner': True},
            attempt=self.attempt, record_id=self.record_id, source_url=self.source_url, detail_url=self._bound_url)
        self._component_observed = True
        return proof

    def _l7_probe(self, operation, check_cancel=None):
        self._cancel(check_cancel)
        try:
            value = operation()
        except JsonSafetyError:
            self._cancel(check_cancel)
            raise
        except Exception:
            value = None
        self._cancel(check_cancel)
        return value

    def _l7_state(self, state):
        if (not isinstance(state, dict) or set(state) != {'available', 'changed', 'complete'}
                or any(type(value) is not bool for value in state.values())):
            self._l7_unavailable = True
            return None
        if state['changed']:
            raise JsonSafetyError('Observed corporate L7 child history changed')
        if not state['available']:
            self._l7_unavailable = True
        return state

    def _l10b_state(self, state):
        if (not isinstance(state, dict) or set(state) != {'available', 'changed', 'complete'}
                or any(type(value) is not bool for value in state.values())):
            self._l10b_unavailable = True
            return None
        if state['changed']:
            raise JsonSafetyError('Observed corporate L10-B child history changed')
        if not state['available']:
            self._l10b_unavailable = True
        return state

    def bind_l10b_structure(self, form, tab, panel, *, phase, check_cancel=None):
        """Retain real original owners at both enabled observation boundaries."""
        if phase not in ('start', 'end'):
            raise ValueError('Unknown L10-B structural boundary')
        self._l10b_requested = True
        if self.observe_component_lifetime(check_cancel=check_cancel) is None or self._l10b_history is None:
            return False
        handles = {}
        try:
            for name, locator in (('form', form), ('tab', tab), ('panel', panel)):
                def retain():
                    handles[name] = locator.element_handle()
                    return handles[name]
                if self._l7_probe(retain, check_cancel) is None:
                    self._l10b_unavailable = True
                    return False
            state = self._l10b_state(self._l7_probe(lambda: self._l10b_history.evaluate(
                '(h,args) => h.bind(args)', {**handles, 'phase': phase}), check_cancel))
            self._verify_binding()
            if self.observe_component_lifetime(check_cancel=check_cancel) is None:
                return False
            return bool(not self._l10b_unavailable and state and state['available']
                        and (phase == 'start' or state['complete']))
        finally:
            for handle in reversed(list(handles.values())):
                if handle is not None:
                    try:
                        handle.dispose()
                    except Exception:  # nosec B110 - Owned cleanup preserves Stop and original failure.
                        pass

    def observe_l10b_lifetime(self, *, check_cancel=None):
        self._l10b_requested = True
        if self.observe_component_lifetime(check_cancel=check_cancel) is None or self._l10b_history is None:
            return None
        state = self._l10b_state(self._l7_probe(
            lambda: self._l10b_history.evaluate('(h) => h.sample()'), check_cancel))
        self._verify_binding()
        if self._component_invalid:
            raise JsonSafetyError('Observed submitted component lifetime changed')
        # Candidate only. Drain later samples ALL requested children and the
        # parent together, in its final synchronous browser RPC.
        if self._l10b_unavailable or not state or not state['complete']:
            return None
        return _capture_l10b_lifetime({'kind': 'corporate-l10b-spa-v1', 'attempt': self.attempt,
            'record_id': self.record_id, 'source_url': self.source_url, 'detail_url': self._bound_url,
            'fresh_root': True, 'fresh_form': True, 'stable_root': True,
            'stable_form': True, 'enabled_boundaries': True}, attempt=self.attempt,
            record_id=self.record_id, source_url=self.source_url, detail_url=self._bound_url)

    def _l7_gate(self, name):
        # Fixed enum only; the optional L7 proof must name its own refusal.
        diagnostics.record('corporate.l7_capture_gate', corporate_l7_capture_gate=name)
        return False

    def _l7_arm_state(self):
        """Record only the fixed arming precondition of the optional L7 history."""
        history = self._l7_history
        if history is None:
            diagnostics.record('corporate.l7_history_arm', corporate_l7_history_arm='unsupported')
            return
        try:
            reason = history.evaluate('(h) => h.why()')
        except Exception:  # nosec B110 - Optional instrumentation must not replace Stop.
            diagnostics.record('corporate.l7_history_arm', corporate_l7_history_arm='unsupported')
            return
        name = {'ok': 'clear', 'initial': 'occupied', 'document': 'document'}.get(reason, 'unsupported')
        diagnostics.record('corporate.l7_history_arm', corporate_l7_history_arm=name)

    def bind_l7_structure(self, form, grid, table, tab, panel, *, phase, check_cancel=None):
        """Bind real held nodes twice; never adopt replacements after start."""
        self._cancel(check_cancel)
        if phase not in ('start', 'end'):
            raise ValueError('Unknown L7 structural boundary')
        self._l7_requested = True
        component = self.observe_component_lifetime(check_cancel=check_cancel)
        if component is None:
            return self._l7_gate('component')
        if self._l7_history is None:
            return self._l7_gate('history')
        if self._l7_unavailable:
            return self._l7_gate('flagged')
        history = self._l7_history
        handles = {}
        try:
            for key, locator in (('form', form), ('grid', grid), ('table', table), ('tab', tab), ('panel', panel)):
                self._cancel(check_cancel)
                def retain_element():
                    handles[key] = locator.element_handle()
                    return handles[key]
                handle = self._l7_probe(retain_element, check_cancel)
                if handle is None:
                    self._l7_unavailable = True
                    return self._l7_gate('handle_' + key)
                handles[key] = handle
            state = self._l7_probe(lambda: history.evaluate(
                '(h,args) => h.bind(args)', {**handles, 'phase': phase}), check_cancel)
            self._verify_binding()
            state = self._l7_state(state)
            if state is None:
                return self._l7_gate('state_malformed')
            if not state['available']:
                try:
                    reason = history.evaluate('(h) => h.why()')
                except JsonSafetyError:
                    raise
                except Exception:
                    return self._l7_gate('js_no_method')
                self._cancel(check_cancel)
                name = 'js_' + reason if type(reason) is str and reason in _L7_JS_REASONS else 'js_unknown'
                return self._l7_gate(name)
            component = self.observe_component_lifetime(check_cancel=check_cancel)
            if component is None:
                return self._l7_gate('component_end')
            if phase == 'end' and not state['complete']:
                return self._l7_gate('incomplete')
            return True
        finally:
            for handle in reversed(list(handles.values())):
                if handle is None:
                    continue
                try:
                    handle.dispose()
                except Exception:  # nosec B110 - Cleanup cannot replace Stop or safety refusal.
                    pass

    def bind_l10d_structure(self, form, tab, panel, *, phase, check_cancel=None):
        """D-specific boundaries only, never a final sequential end sampler."""
        def cancel():
            self._cancel(check_cancel)
        cancel()
        if phase not in ('start', 'end'):
            raise ValueError('Unknown L10-D structural boundary')
        self._l10d_history.requested = True
        if self.observe_component_lifetime(check_cancel=check_cancel) is None:
            return False
        bound = self._l10d_history.bind(form, tab, panel, phase=phase, cancel=cancel)
        self._verify_binding()
        return bound and self.observe_component_lifetime(check_cancel=check_cancel) is not None

    def observe_l7_lifetime(self, *, check_cancel=None):
        """Candidate only: drain resamples independently inside its final fence."""
        self._cancel(check_cancel)
        self._l7_requested = True
        component = self.observe_component_lifetime(check_cancel=check_cancel)
        if component is None or self._l7_history is None:
            return None
        state = self._l7_probe(lambda: self._l7_history.evaluate('(h) => h.sample()'), check_cancel)
        self._verify_binding()
        state = self._l7_state(state)
        component = self.observe_component_lifetime(check_cancel=check_cancel)
        if (component is None or state is None or self._l7_unavailable
                or not state['available'] or not state['complete']):
            return None
        return _capture_l7_lifetime({'kind': 'corporate-l7-spa-v1', 'attempt': self.attempt,
            'record_id': self.record_id, 'source_url': self.source_url, 'detail_url': self._bound_url,
            **dict.fromkeys(('fresh_root', 'fresh_l7', 'stable_root', 'stable_form',
                             'stable_grid', 'stable_table', 'enabled_boundaries'), True)},
            attempt=self.attempt, record_id=self.record_id,
            source_url=self.source_url, detail_url=self._bound_url)

    def _l10c_probe(self, operation, check_cancel=None):
        self._cancel(check_cancel)
        try:
            value = operation()
        except JsonSafetyError:
            self._cancel(check_cancel)
            raise
        except Exception:
            value = None
        self._cancel(check_cancel)
        if self._bound is not None:
            self._verify_binding()
        if self._component_invalid:
            raise JsonSafetyError('Observed submitted component lifetime changed')
        return value

    def _l10c_state(self, state):
        if (not isinstance(state, dict) or set(state) - {'why'} != {'available', 'changed', 'complete'}
                or any(type(state[key]) is not bool for key in ('available', 'changed', 'complete'))
                or ('why' in state and type(state['why']) is not str)):
            self._l10c_unavailable = True
            self._l10c_state_reason = 'malformed'
            return None
        if state['changed']:
            raise JsonSafetyError('Observed corporate L10-C child history changed')
        if not state['available']:
            self._l10c_unavailable = True
            self._l10c_state_reason = 'unavailable'
            self._l10c_unavailable_why = state.get('why', '')
        return state

    def bind_l10c_structure(self, form, grid, table, tab, panel, *, phase, check_cancel=None):
        """C-owned disabled controls and child nodes; never adopt a remount."""
        if phase not in ('start', 'end'):
            raise ValueError('Unknown L10-C structural boundary')
        self._l10c_requested = True
        if (self.observe_component_lifetime(check_cancel=check_cancel) is None
                or self._l10c_history is None or self._l10c_unavailable):
            self._l10c_bind_reason = 'lifetime_or_history'
            return False
        handles = {}
        try:
            for key, locator in (('form', form), ('grid', grid), ('table', table), ('tab', tab), ('panel', panel)):
                def retain():
                    handles[key] = locator.element_handle()
                    return handles[key]
                if self._l10c_probe(retain, check_cancel) is None:
                    self._l10c_unavailable = True
                    self._l10c_bind_reason = 'handle_' + key
                    return False
            probe_result = self._l10c_probe(lambda: self._l10c_history.evaluate(
                '(h,args) => h.bind(args)', {**handles, 'phase': phase}), check_cancel)
            if probe_result is None:
                # A failed evaluation must keep the history permanently
                # unavailable, exactly as _l10c_state(None) did before, so a
                # later lifetime sample can never resurrect it.
                self._l10c_unavailable = True
                self._l10c_bind_reason = 'state_' + phase + '_eval'
                return False
            self._l10c_state_reason = None
            self._l10c_unavailable_why = ''
            state = self._l10c_state(probe_result)
            result = bool(state is not None and not self._l10c_unavailable
                          and (phase == 'start' or state['complete']))
            if not result:
                if state is None:
                    self._l10c_bind_reason = ('state_' + phase + '_'
                                              + (self._l10c_state_reason or 'malformed'))
                elif self._l10c_unavailable:
                    self._l10c_bind_reason = ('state_' + phase + '_'
                                              + (self._l10c_state_reason or 'unavailable')
                                              + ('_' + self._l10c_unavailable_why
                                                 if self._l10c_unavailable_why else ''))
                else:
                    self._l10c_bind_reason = 'state_' + phase + '_incomplete'
            return result
        finally:
            for handle in reversed(list(handles.values())):
                if handle is not None:
                    try:
                        handle.dispose()
                    except Exception:  # nosec B110 - Cleanup preserves Stop and safety failure.
                        pass

    def observe_l10c_lifetime(self, *, check_cancel=None, _final=False):
        """Final=True is the last browser RPC; no later parent/sibling probe."""
        self._cancel(check_cancel)
        self._l10c_requested = True
        if not _final and self.observe_component_lifetime(check_cancel=check_cancel) is None:
            return None
        if self._l10c_history is None:
            return None
        sample = self._l10c_probe(lambda: self._l10c_history.evaluate(
            _L10C_FINAL_SAMPLE if _final else '(h) => h.sample()'), check_cancel)
        if _final:
            self._l10c_clock_end = None
            state = None
            if isinstance(sample, dict):
                self._l10c_state(sample.get('state'))  # Known changes dominate malformed-wrapper fallback.
            if isinstance(sample, dict) and set(sample) == {'state', 'clock'}:
                state, clock = sample['state'], sample['clock']
                if isinstance(clock, dict) and set(clock) == {'epoch_ms', 'timezone'}:
                    try:
                        _capture_clock_interval({'attempt': self.attempt,
                            'start_ms': self._clock_start['epoch_ms'] if self._clock_start else clock['epoch_ms'],
                            'end_ms': clock['epoch_ms'], 'timezone': clock['timezone']}, self.attempt)
                        self._l10c_clock_end = dict(clock)
                    except JsonSafetyError:
                        pass  # An unavailable/reversed final clock grants no dated catalog selection.
        else:
            state = sample
        state = self._l10c_state(state)
        if (state is None or self._l10c_unavailable or not state['complete']):
            return None
        self._l10c_offered = True
        return _capture_l10c_lifetime({'kind': 'corporate-l10c-spa-v1', 'attempt': self.attempt,
            'record_id': self.record_id, 'source_url': self.source_url, 'detail_url': self._bound_url,
            **dict.fromkeys(('fresh_root', 'fresh_form', 'stable_root', 'stable_form',
                             'stable_grid', 'stable_controls', 'enabled_boundaries'), True)},
            attempt=self.attempt, record_id=self.record_id,
            source_url=self.source_url, detail_url=self._bound_url)

    def observe_l8_lifetime(self, *, check_cancel=None):
        """Stronger L8-only structural history, armed before the inspected View."""
        self._l8_refusal = None
        self._cancel(check_cancel)
        self._verify_binding()
        self._l8_requested = True
        if self.observe_component_lifetime(check_cancel=check_cancel) is None:
            self._l8_refusal = 'l8_component_lifetime'
            return None
        if self._l8_history is None:
            self._l8_refusal = 'l8_history_missing'
            return None
        state = self._component_probe(lambda: self._l8_history.evaluate('(h) => h.sample()'), check_cancel)
        self._verify_binding()
        if (not isinstance(state, dict) or set(state) != {
                'initial_clear', 'root_seen', 'root_changed', 'dependent_seen'}
                or any(type(value) is not bool for value in state.values())):
            self._l8_refusal = 'l8_state_shape'
            return None
        if state['root_changed']:
            raise JsonSafetyError('Observed corporate L8 root history changed')
        if not state['initial_clear']:
            self._l8_refusal = 'l8_not_clear'
            return None
        if not state['root_seen']:
            self._l8_refusal = 'l8_no_root'
            return None
        if state['dependent_seen']:
            self._l8_refusal = 'l8_dependent'
            return None
        self._l8_refusal = None
        return _capture_l8_lifetime({'kind': 'corporate-l8-spa-v1', 'attempt': self.attempt,
            'record_id': self.record_id, 'source_url': self.source_url, 'detail_url': self._bound_url,
            'fresh_root': True, 'stable_root': True, 'no_dependent_forms': True},
            attempt=self.attempt, record_id=self.record_id,
            source_url=self.source_url, detail_url=self._bound_url)

    def l8_refusal_reason(self):
        """Bounded enum naming the L8 guard that refused, or None."""
        return self._l8_refusal

    def l8_refuse(self, reason):
        """Record a finite L8 guard name; never a value, URL, or digest."""
        self._l8_refusal = reason

    def observe_corporate_reference_providers(self, *, check_cancel=None):
        """Optional once-only loaded-source proof; never fetch a reference catalog."""
        from coretax_browser import CaptureCancelled
        from coretax_build_pins import load_build_pins
        from coretax_masa_observer import _PPN_MAIN_BUILD_HASH, _REFERENCE_ORDER_BUILD_HASH

        self._cancel(check_cancel)
        self._verify_binding()
        if self._result is not None:
            sealed = self._result.get('corporate_reference_providers')
            return dict(sealed['builds']) if sealed is not None else None
        if not self._corporate:
            return None
        if self.observe_component_lifetime(check_cancel=check_cancel) is None:
            return None
        if self._reference_providers_attempted:
            return (dict(self._reference_providers['builds'])
                    if self._reference_providers is not None else None)
        self._reference_providers_attempted = True
        configured = load_build_pins()
        pins = {url: configured.get(url) for url in CORPORATE_REFERENCE_SOURCES}
        if not _corporate_reference_builds(pins):
            return None
        try:
            # This is the existing L11-A script-provider predicate, not cache or
            # Angular inspection. The existing bounded readers own all hashing.
            loaded = self._bound.evaluate('''urls => urls.every(url =>
                [...document.scripts].some(s => s.src === url) ||
                performance.getEntriesByType('resource').some(e => e.name === url && e.initiatorType === 'script'))''',
                list(CORPORATE_REFERENCE_SOURCES))
            self._cancel(check_cancel)
            observed = {}
            if loaded is True:
                for url in CORPORATE_REFERENCE_SOURCES:
                    reader = _PPN_MAIN_BUILD_HASH if '/main.' in url else _REFERENCE_ORDER_BUILD_HASH
                    observed[url] = self._bound.evaluate(reader, url)
                    self._cancel(check_cancel)
                    if not isinstance(observed[url], str) or observed[url] != pins[url]:
                        break
        except (JsonSafetyError, CaptureCancelled):
            self._cancel(check_cancel)
            raise
        except Exception:
            self._cancel(check_cancel)
            observed = None
        self._cancel(check_cancel)
        if self.observe_component_lifetime(check_cancel=check_cancel) is None:
            return None
        if not _corporate_reference_builds(observed):
            return None
        self._reference_providers = _capture_corporate_reference_providers({
            'kind': 'corporate-reference-providers-v1', 'attempt': self.attempt,
            'record_id': self.record_id, 'source_url': self.source_url,
            'detail_url': self._bound_url, 'builds': observed}, attempt=self.attempt,
            record_id=self.record_id, source_url=self.source_url, detail_url=self._bound_url)
        return dict(observed)
    def _final_lifetimes(self, lifetime, l8_lifetime, l7_lifetime, l10b_lifetime,
                         l10c_lifetime=None, *, check_cancel=None):
        """Only narrow candidates, with every requested history in one last RPC.

        Separate child/parent probes can pump a change to an already sampled
        sibling. This fixed snapshot also closes L7's pre-existing post-sample
        parent-probe window. After it, sealing performs only local checks/I/O.
        """
        self._cancel(check_cancel)
        if not self._component_started or self._component_document is None:
            return None, None, None, None, None
        sample = self._l7_probe(lambda: self._component_document.evaluate(_FINAL_LIFETIMES, {
            'l8': self._l8_history if self._l8_requested else None,
            'l7': self._l7_history if self._l7_requested else None,
            'l10b': self._l10b_history if self._l10b_requested else None,
            'l10c': self._l10c_history if self._l10c_requested else None}), check_cancel)
        self._verify_binding()
        if self._component_invalid:
            raise JsonSafetyError('Observed submitted component lifetime changed')
        sample = sample if isinstance(sample, dict) else {}
        # Check known child changes even when another proof is unavailable or
        # the surrounding reply is malformed; never discard a negative offer
        # just to accept its sibling.
        l7 = self._l7_state(sample.get('l7')) if self._l7_requested else None
        l10b = self._l10b_state(sample.get('l10b')) if self._l10b_requested else None
        l10c = self._l10c_state(sample.get('l10c')) if self._l10c_requested else None
        l8 = sample.get('l8')
        l8_valid = (isinstance(l8, dict) and set(l8) == {
            'initial_clear', 'root_seen', 'root_changed', 'dependent_seen'}
            and all(type(value) is bool for value in l8.values()))
        if self._l8_requested and l8_valid and l8['root_changed']:
            raise JsonSafetyError('Observed corporate L8 root history changed')
        if set(sample) != {'same_document', 'owners', 'l8', 'l7', 'l10b', 'l10c', 'clock'}:
            return None, None, None, None, None
        owners = {'source_owner': False, 'detail_owner': True}
        if (sample['same_document'] is False
                or self._component_observed and sample['owners'] != owners):
            raise JsonSafetyError('Observed submitted component lifetime changed')
        if lifetime is None or sample['same_document'] is not True or sample['owners'] != owners:
            return None, None, None, None, None
        if not l7 or self._l7_unavailable or not l7['available'] or not l7['complete']:
            l7_lifetime = None
        if not l10b or self._l10b_unavailable or not l10b['available'] or not l10b['complete']:
            l10b_lifetime = None
        if not l10c or self._l10c_unavailable or not l10c['available'] or not l10c['complete']:
            l10c_lifetime = None
        if not l8_valid or not l8['initial_clear'] or not l8['root_seen'] or l8['dependent_seen']:
            l8_lifetime = None
        clock = sample['clock']
        if (isinstance(clock, dict) and set(clock) == {'epoch_ms', 'timezone'}
                and type(clock['epoch_ms']) is int and isinstance(clock['timezone'], str)):
            self._final_clock = dict(clock)
        # A final snapshot cannot create a capability that was not offered by
        # its own observer, or repair an unavailable parent/child candidate.
        return lifetime, l8_lifetime, l7_lifetime, l10b_lifetime, l10c_lifetime

    def _candidate(self, target, frame):
        return (target.context is self.context and frame is target.main_frame
                and frame.parent_frame is None
                and (target is self.page or target.opener() is self.page))

    def _on_request(self, request):
        if not self._active or self._result is not None:
            return
        try:
            # Replacement changes L1-D input despite ordinary capture excluding
            # this prefix. Retain only a value-free veto; never inspect its body.
            if (self._component_listener is not None and request.method == 'POST'
                    and request.url == ORIGIN + '/returnsheet/api/returnsheetsfinancialstatements'
                    and request.frame is self.page.main_frame):
                self._component_invalid = True
            reference = (request.url in self._reference_urls
                         and request.method == 'GET' and request.post_data is None)
            if (not _safe_url(request.url) or request.resource_type not in ('xhr', 'fetch')
                    or not (urlparse(request.url).path.startswith('/returnsheet/api/') or reference)
                    or urlparse(request.url).path.casefold().startswith('/returnsheet/api/returnsheets')):
                return
            frame = request.frame
            target = frame.page
            if (not self._candidate(target, frame) or not self._detail_matches(frame.url)
                    or self._bound is not None and target is not self._bound):
                return
            if self._seen >= self._limits['responses']:
                self._reason('response-limit')
                return
            self._seen += 1
            post = request.post_data
            request_json = None
            if post is not None:
                if not isinstance(post, str) or len(post.encode('utf-8')) > MAX_REQUEST_METADATA_BYTES:
                    self._reason('request-context-limit')
                    return
                request_json = _json(post)
                if _has_secret(request_json):
                    self._reason('secret-request')
                    return
            # Catatan observasi menyimpan metadata request terbatas, termasuk
            # request_json, tanpa menahan objek request/response driver atau
            # byte body respons pada catatan ini.
            observation = {'target': target, 'frame_url': frame.url, 'url': request.url,
                           'method': request.method, 'request_json': request_json,
                           'sequence': self._seen, 'status': None}
            self._observations.append(observation)
            self._requests[request] = {**observation, 'frame': frame,
                                       'observation': observation,
                                       'state': 'pending', 'response': None}
        except Exception:
            # Driver/JSON exception text may contain credentials; never persist it.
            self._reason('request-context-unavailable')

    def _on_response(self, response):
        entry = self._requests.get(response.request)
        if entry is None:
            return
        try:
            if response.url != entry['url'] or not _safe_url(response.url):
                entry['state'] = 'failed'
                self._reason('response-source-mismatch')
                return
            # Authorization failure is decisive even when the server sends HTML.
            # Keep only the status: no rejected body is read or persisted.
            entry['status'] = response.status
            entry['observation']['status'] = entry['status']
            if entry['status'] in (401, 403):
                entry['state'] = 'failed'
                self._reason('authorization-rejected')
                return
            content_type = response.header_value('content-type') or ''
            mime = content_type.split(';', 1)[0].strip().casefold()
            if mime != 'application/json' and not mime.endswith('+json'):
                self._requests.pop(response.request)
                self._counts['excluded'] += 1
                return
            entry.update(response=response, content_type=mime,
                         content_length=response.header_value('content-length'), status=response.status)
        except Exception:
            entry['state'] = 'failed'
            self._reason('response-metadata-unavailable')

    def _on_finished(self, request):
        entry = self._requests.get(request)
        if entry is not None and entry['state'] != 'failed':
            entry['state'] = 'finished'

    def _on_failed(self, request):
        entry = self._requests.get(request)
        if entry is not None:
            entry['state'] = 'failed'
            self._reason('request-failed')

    def bind_detail_page(self, detail):
        self._cancel()
        if (not self._active or detail.context is not self.context or detail.is_closed()
                or not self._detail_matches(detail.url)
                or detail is not self.page and detail.opener() is not self.page):
            raise JsonSafetyError('Detail page does not belong to this selected capture attempt')
        if self._bound is not None and self._bound is not detail:
            raise JsonSafetyError('Detail page changed inside a capture attempt')
        self._bound = detail
        self._bound_url = detail.url
        self._observations = [item for item in self._observations if item['target'] is detail]
        for request, entry in list(self._requests.items()):
            if entry['target'] is not detail:
                self._requests.pop(request)
                self._counts['excluded'] += 1

    def _verify_binding(self):
        if (not self._active or self._bound is None or self._bound.is_closed()
                or self._bound.context is not self.context or self._bound.url != self._bound_url
                or not self._detail_matches(self._bound.url)):
            raise JsonSafetyError('Verified detail page binding changed or is missing')

    def _write(self, name, raw, check_cancel=None):
        self._cancel(check_cancel)
        directory = self.folder / self._relative
        self._hold(directory)
        path = directory / name
        with path.open('xb') as stream:
            for offset in range(0, len(raw), 65536):
                self._cancel(check_cancel)
                stream.write(raw[offset:offset + 65536])
            self._cancel(check_cancel)
        self._hold(directory)
        return path.relative_to(self.folder).as_posix()

    def _process(self, entry, deadline, check_cancel):
        self._cancel(check_cancel)
        self._verify_binding()
        response = entry['response']
        if response is None:
            self._reason('response-metadata-unavailable')
            return
        declared = entry.get('content_length')
        if declared is not None and (not re.fullmatch(r'[0-9]+', declared)
                                     or int(declared) > self._limits['body_bytes']):
            self._reason('body-size-limit')
            return
        if declared is not None and int(declared) + self._read_bytes > self._limits['attempt_bytes']:
            self._reason('attempt-byte-limit')
            return
        # Driver membaca seluruh body sekaligus; batas byte/waktu diperiksa lagi
        # sesudahnya, sehingga batas ini bukan jaminan RAM atau interupsi seketika.
        try:
            raw = response.body()
        except Exception:
            self._reason('body-read-failed')
            return
        self._cancel(check_cancel)
        self._verify_binding()
        if time.monotonic() >= deadline:
            self._reason('drain-deadline')
            return
        if not isinstance(raw, bytes) or len(raw) > self._limits['body_bytes']:
            self._reason('body-size-limit')
            return
        self._read_bytes += len(raw)
        if self._read_bytes > self._limits['attempt_bytes']:
            self._reason('attempt-byte-limit')
            return
        try:
            payload = _json(raw)
            secret = _has_secret(payload)
        except (ValueError, JsonSafetyError, RecursionError, UnicodeError):
            self._reason('invalid-json')
            return
        if secret:
            self._reason('secret-body')
            return
        del payload
        self._cancel(check_cancel)
        self._verify_binding()
        relative = self._write(f'response-{len(self._responses) + 1:04d}.json', raw, check_cancel)
        self._responses.append({'relative_path': relative, 'bytes': len(raw),
                                'sha256': hashlib.sha256(raw).hexdigest(),
                                'url': entry['url'], 'method': entry['method'], 'status': entry['status'],
                                'frame_url': entry['frame_url'], 'sequence': entry['sequence'],
                                'attempt': self.attempt, 'record_id': self.record_id,
                                'scope': list(self.scope), 'request_json': entry['request_json'],
                                'identity_validated': False})
        self._counts['accepted'] += 1

    def drain(self, check_cancel=None):
        self._cancel(check_cancel)
        self._verify_binding()
        if self._result is not None:
            return json.loads(json.dumps(self._result))
        deadline = time.monotonic() + self._limits['drain_seconds']
        while self._requests:
            self._cancel(check_cancel)
            self._verify_binding()
            if time.monotonic() >= deadline:
                self._counts['pending'] = len(self._requests)
                self._reason('response-pending')
                break
            ready = next(((request, entry) for request, entry in self._requests.items()
                          if entry['state'] in ('finished', 'failed')), None)
            if ready is None:
                self._bound.wait_for_timeout(100)
                continue
            request, entry = ready
            try:
                if entry['state'] == 'failed':
                    self._counts['failed'] += 1
                else:
                    self._process(entry, deadline, check_cancel)
            finally:
                self._requests.pop(request, None)
            del request, entry, ready
        self._requests.clear()
        self._cancel(check_cancel)
        self._verify_binding()
        seen_before_clock = self._seen
        clock_end = self._sample_clock(self._bound, check_cancel)
        lifetime = self.observe_component_lifetime(check_cancel=check_cancel)
        l8_lifetime = self.observe_l8_lifetime(check_cancel=check_cancel) if self._l8_requested else None
        l7_lifetime = self.observe_l7_lifetime(check_cancel=check_cancel) if self._l7_requested else None
        l10b_lifetime = self.observe_l10b_lifetime(check_cancel=check_cancel) if self._l10b_requested else None
        # Produce every requested child candidate first; the joint snapshot may
        # only narrow it, never create or repair it, and owns the final clock.
        l10c_candidate = (self.observe_l10c_lifetime(check_cancel=check_cancel)
                         if self._l10c_requested else None)
        lifetime, l8_lifetime, l7_lifetime, l10b_lifetime, l10c_lifetime = self._final_lifetimes(
            lifetime, l8_lifetime, l7_lifetime, l10b_lifetime, l10c_candidate,
            check_cancel=check_cancel)
        if self._l10c_requested:
            # The joint snapshot owns the final clock. Only an actually offered
            # C fact needs its own last RPC to re-prove that clock; when C was
            # never offered, the joint turn clock still belongs to this capture
            # and must survive an unavailable C candidate.
            if self._l10c_offered:
                clock_end = None
                if lifetime is not None and self._final_clock is not None:
                    l10c_final = self.observe_l10c_lifetime(check_cancel=check_cancel, _final=True)
                    if l10c_final is not None:
                        l10c_lifetime = l10c_final
                        clock_end = self._final_clock
                    else:
                        l10c_lifetime = None
                if l10c_lifetime is None:
                    self._reason('corporate-l10c-not-sealed')
            elif self._final_clock is not None:
                # No C fact to seal: the joint snapshot clock is the capture's
                # final clock, not a pre-final sample.
                clock_end = self._final_clock
        self._cancel(check_cancel)
        self._verify_binding()
        if self._requests or self._seen != seen_before_clock:
            # Evaluating environment metadata pumps browser events too. A late
            # reply may already be excluded by MIME and absent from _requests.
            # It is outside the final drain, never an empty/complete set.
            self._counts['pending'] += len(self._requests)
            self._reason('response-after-final-drain')
            self._requests.clear()
        result = {'version': 1, 'attempt': self.attempt, 'record_id': self.record_id,
                  'scope': list(self.scope), 'source_url': self.source_url, 'detail_url': self._bound_url,
                  'limits': dict(self._limits), 'counts': dict(self._counts),
                  'complete': not self._reasons, 'reasons': list(self._reasons),
                  'responses': list(self._responses), 'credentials_accessed': False,
                  'primary_identity_validated': False}
        if lifetime is not None:
            result['component_lifetime'] = lifetime
        if l8_lifetime is not None:
            result['corporate_l8_lifetime'] = l8_lifetime
        if l7_lifetime is not None and lifetime is not None:
            result['corporate_l7_lifetime'] = l7_lifetime
        if l10b_lifetime is not None and lifetime is not None:
            result['corporate_l10b_lifetime'] = l10b_lifetime
        if l10c_lifetime is not None and lifetime is not None:
            result['corporate_l10c_lifetime'] = l10c_lifetime
        if self._clock_start is not None and clock_end is not None:
            try:
                result['clock_interval'] = _capture_clock_interval({
                    'attempt': self.attempt, 'start_ms': self._clock_start['epoch_ms'],
                    'end_ms': clock_end['epoch_ms'], 'timezone': clock_end['timezone']}, self.attempt)
            except JsonSafetyError:
                pass  # An unavailable/reversed sample cannot authorize dated selection.
        if (self._reference_providers is not None and lifetime is not None
                and 'clock_interval' in result):
            result['corporate_reference_providers'] = {
                **self._reference_providers, 'builds': dict(self._reference_providers['builds'])}
        raw = json.dumps(result, ensure_ascii=False, sort_keys=True).encode('utf-8')
        manifest = self._write('manifest.json', raw, check_cancel)
        self._cancel(check_cancel)
        self._manifest_hash = hashlib.sha256(raw).hexdigest()
        self._result = {**result, 'manifest': manifest, 'manifest_sha256': self._manifest_hash}
        return json.loads(json.dumps(self._result))

    def request_observations(self):
        """Expose this attempt's bounded metadata, including excluded replies."""
        self._cancel()
        self._verify_binding()
        keys = ('url', 'method', 'frame_url', 'sequence', 'request_json', 'status')
        return json.loads(json.dumps([{key: item.get(key) for key in keys}
                                      for item in self._observations
                                      if item['target'] is self._bound]))

    def iter_bodies(self, check_cancel=None):
        self._cancel(check_cancel)
        if self._result is None:
            raise JsonSafetyError('Capture must be drained before resolving body references')
        try:
            self._hold(self.folder / self._relative)
            with locked_file(self.folder / self._result['manifest']) as stream:
                manifest = stream.read()
            if hashlib.sha256(manifest).hexdigest() != self._manifest_hash:
                raise JsonSafetyError('Private capture manifest changed')
            saved = _json(manifest)
            if saved['attempt'] != self.attempt or saved['scope'] != self.scope or saved['record_id'] != self.record_id:
                raise JsonSafetyError('Private capture scope or attempt changed')
            clock = (_capture_clock_interval(saved['clock_interval'], self.attempt)
                     if 'clock_interval' in saved else None)
            lifetime = (_capture_component_lifetime(saved['component_lifetime'], attempt=self.attempt,
                record_id=self.record_id, source_url=self.source_url, detail_url=self._bound_url)
                if 'component_lifetime' in saved else None)
            providers = (_capture_corporate_reference_providers(saved['corporate_reference_providers'],
                attempt=self.attempt, record_id=self.record_id,
                source_url=self.source_url, detail_url=self._bound_url)
                if 'corporate_reference_providers' in saved else None)
            if providers is not None and (lifetime is None or clock is None):
                raise JsonSafetyError('Private reference providers lack original lifetime or clock')
            l8_lifetime = (_capture_l8_lifetime(saved['corporate_l8_lifetime'], attempt=self.attempt,
                record_id=self.record_id, source_url=self.source_url, detail_url=self._bound_url)
                if 'corporate_l8_lifetime' in saved else None)
            l7_lifetime = (_capture_l7_lifetime(saved['corporate_l7_lifetime'], attempt=self.attempt,
                record_id=self.record_id, source_url=self.source_url, detail_url=self._bound_url)
                if 'corporate_l7_lifetime' in saved else None)
            l10b_lifetime = (_capture_l10b_lifetime(saved['corporate_l10b_lifetime'], attempt=self.attempt,
                record_id=self.record_id, source_url=self.source_url, detail_url=self._bound_url)
                if 'corporate_l10b_lifetime' in saved else None)
            if l10b_lifetime is not None and lifetime is None:
                raise JsonSafetyError('Private L10-B history lacks its component lifetime')
            l10c_lifetime = (_capture_l10c_lifetime(saved['corporate_l10c_lifetime'], attempt=self.attempt,
                record_id=self.record_id, source_url=self.source_url, detail_url=self._bound_url)
                if 'corporate_l10c_lifetime' in saved else None)
            if l7_lifetime is not None and lifetime is None:
                raise JsonSafetyError('Private L7 history lacks its component lifetime')
            if l10c_lifetime is not None and lifetime is None:
                raise JsonSafetyError('Private L10-C history lacks its component lifetime')
            if l8_lifetime is not None and lifetime is None:
                raise JsonSafetyError('Private L8 history lacks its component lifetime')
            from coretax_corporate_l10d import validate_lifetime
            l10d_lifetime = (validate_lifetime(saved['corporate_l10d_lifetime'], lifetime)
                if 'corporate_l10d_lifetime' in saved else None)
            for descriptor in saved['responses']:
                self._cancel(check_cancel)
                relative = Path(descriptor['relative_path'])
                if (relative.is_absolute() or '..' in relative.parts or relative.parent != self._relative
                        or descriptor['attempt'] != self.attempt or 'clock_interval' in descriptor
                        or 'component_lifetime' in descriptor or 'corporate_l8_lifetime' in descriptor
                        or 'corporate_l7_lifetime' in descriptor or 'corporate_reference_providers' in descriptor or 'corporate_l10b_lifetime' in descriptor or 'corporate_l10c_lifetime' in descriptor or 'corporate_l10d_lifetime' in descriptor):
                    raise JsonSafetyError('Unsafe private response reference')
                self._hold(self.folder / self._relative)
                with locked_file(self.folder / relative) as stream:
                    raw = stream.read(self._limits['body_bytes'] + 1)
                if (len(raw) != descriptor['bytes'] or len(raw) > self._limits['body_bytes']
                        or hashlib.sha256(raw).hexdigest() != descriptor['sha256']):
                    raise JsonSafetyError('Private response bytes changed')
                self._cancel(check_cancel)
                payload = _json(raw)
                if _has_secret(payload):
                    raise JsonSafetyError('Private response no longer meets privacy policy')
                self._cancel(check_cancel)
                context = dict(descriptor)
                if clock is not None:
                    context['clock_interval'] = dict(clock)
                if lifetime is not None:
                    context['component_lifetime'] = dict(lifetime)
                if providers is not None:
                    context['corporate_reference_providers'] = {**providers, 'builds': dict(providers['builds'])}
                if l8_lifetime is not None:
                    context['corporate_l8_lifetime'] = dict(l8_lifetime)
                if l7_lifetime is not None:
                    context['corporate_l7_lifetime'] = dict(l7_lifetime)
                if l10b_lifetime is not None:
                    context['corporate_l10b_lifetime'] = dict(l10b_lifetime)
                if l10c_lifetime is not None:
                    context['corporate_l10c_lifetime'] = dict(l10c_lifetime)
                if l10d_lifetime is not None:
                    context['corporate_l10d_lifetime'] = dict(l10d_lifetime)
                yield {'body': raw, 'payload': payload, 'context': context}
                del raw, payload
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise JsonSafetyError('Private capture references cannot be safely resolved') from None

    def close(self):
        self._active = False
        self._requests.clear()
        self._observations.clear()
        if self._l10b_history is not None:
            try:
                self._l10b_history.evaluate('(h) => h.disconnect()')
            except Exception:  # nosec B110 - Owned cleanup preserves Stop and original failure.
                pass
            try:
                self._l10b_history.dispose()
            except Exception:  # nosec B110 - Owned cleanup preserves Stop and original failure.
                pass
            self._l10b_history = None
        if self._l10c_history is not None:
            try:
                self._l10c_history.evaluate('(h) => h.disconnect()')
            except Exception:  # nosec B110 - Cleanup preserves original outcome.
                pass
            try:
                self._l10c_history.dispose()
            except Exception:  # nosec B110 - Cleanup preserves original outcome.
                pass
            self._l10c_history = None
        self._l10d_history.close()
        if self._l7_history is not None:
            try:
                self._l7_history.evaluate('(h) => h.disconnect()')
            except Exception:  # nosec B110 - Owned cleanup must preserve the original outcome.
                pass
            try:
                self._l7_history.dispose()
            except Exception:  # nosec B110 - Owned cleanup must preserve the original outcome.
                pass
            self._l7_history = None
        if self._l8_history is not None:
            try:
                self._l8_history.evaluate('(h) => h.disconnect()')
            except Exception:  # nosec B110 - Owned cleanup is best effort; preserve the original outcome.
                pass
            try:
                self._l8_history.dispose()
            except Exception:  # nosec B110 - Owned cleanup is best effort; preserve the original outcome.
                pass
            self._l8_history = None
        if self._component_listener is not None:
            try:
                self.page.remove_listener('framenavigated', self._component_listener)
            except Exception:  # nosec B110 - Owned cleanup is best effort; preserve the original outcome.
                pass
            self._component_listener = None
        if self._component_document is not None:
            try:
                self._component_document.dispose()
            except Exception:  # nosec B110 - Owned cleanup is best effort; preserve the original outcome.
                pass
            self._component_document = None
        for event, callback in reversed(self._listeners):
            try:
                self.context.remove_listener(event, callback)
            except Exception:  # nosec B110 - Owned cleanup is best effort; preserve the original outcome.
                pass  # Context may already be disposed; never close user pages.
        self._listeners.clear()
        self._guard.close()

    def __exit__(self, exception_type, exception, traceback):
        try:
            self.close()
        except Exception:
            if exception_type is None:
                raise JsonSafetyError('Private capture cleanup failed') from None
        return False


JSON_OUTPUT_LAYOUT = 'tax-kind-v1'
_JSON_TAX_FOLDERS = {'PPh Badan': 'PPh Badan', 'PPh Pasal 21/26': 'SPT PPh 21',
                     'PPh Unifikasi': 'SPT PPh Unifikasi', 'PPN': 'PPN'}


def _json_output_layout(run):
    if 'json_output_layout' not in run:
        return None  # Existing published jobs retain the original ordinal layout.
    layout = run['json_output_layout']
    if not isinstance(layout, str) or layout != JSON_OUTPUT_LAYOUT:
        raise JsonSafetyError('Unsupported JSON output layout')
    return layout


def _published_json_path(name, record, layout):
    if layout is None:
        return name.removeprefix('returns/')
    if not isinstance(layout, str) or layout != JSON_OUTPUT_LAYOUT:
        raise JsonSafetyError('Unsupported JSON output layout')
    # Directory names are fixed presentation labels, never source path fragments.
    tax = record.get('meta', {}).get('Jenis Pajak')
    label = _JSON_TAX_FOLDERS.get(tax, 'SPT Lainnya')
    return 'json/' + label + '/' + name.removeprefix('returns/json/')


def checkpoint_bodies(folder, capture, record, scope, *, published=False,
                      output_layout=None, check_cancel=None):
    """Reacquire original private bytes; reject lexical escapes before any read."""
    from pathlib import PurePosixPath
    if not isinstance(capture, dict):
        raise JsonSafetyError('Missing private capture checkpoint')
    reference = capture.get('manifest')
    if (not isinstance(reference, str) or '\\' in reference or ':' in reference
            or not re.fullmatch(r'returns/json/[0-9]{4,}/[a-f0-9]{32}/manifest\.json', reference)):
        raise JsonSafetyError('Unsafe private capture manifest reference')
    relative = PurePosixPath(reference)
    root = Path(folder).absolute()
    if '..' in root.parts:
        raise JsonSafetyError('Unsafe private capture folder')

    def hold(guard, directory):
        guard.include({parent: _ordinary_directory(parent)
                       for parent in reversed([directory, *directory.parents])})

    def read(guard, name, maximum):
        if check_cancel:
            check_cancel()
        if published:
            name = _published_json_path(name, record, output_layout)
        hold(guard, (root / name).parent)
        with locked_file(root / name) as stream:
            raw = stream.read(maximum + 1)
        if len(raw) > maximum:
            raise JsonSafetyError('Private checkpoint exceeds its byte budget')
        if check_cancel:
            check_cancel()
        return raw

    try:
        with DirectoryGuard() as guard:
            raw = read(guard, reference, 8 * 1024 * 1024)
            if hashlib.sha256(raw).hexdigest() != capture.get('manifest_sha256'):
                raise JsonSafetyError('Private checkpoint manifest bytes changed')
            # Hash saja belum mengikat checkpoint ke SPT terpilih; manifest,
            # metadata, dan upaya capture harus cocok sebelum body dibuka.
            saved = _json(raw)
            if _has_secret(saved):
                raise JsonSafetyError('Private checkpoint metadata no longer meets privacy policy')
            expected = {**saved, 'manifest': reference, 'manifest_sha256': hashlib.sha256(raw).hexdigest()}
            if json.dumps(capture, sort_keys=True) != json.dumps(expected, sort_keys=True):
                raise JsonSafetyError('Private checkpoint manifest metadata changed')
            if (type(saved.get('version')) is not int or saved['version'] != 1
                    or saved.get('scope') != list(scope) or type(saved['scope'][1]) is not int
                    or saved.get('record_id') != record['record_id']
                    or saved.get('source_url') != record['list_url']
                    or saved.get('attempt') != relative.parent.name
                    or saved.get('detail_url') != record.get('detail_url')):
                raise JsonSafetyError('Private checkpoint identity or attempt changed')
            clock = (_capture_clock_interval(saved['clock_interval'], saved['attempt'])
                     if 'clock_interval' in saved else None)
            lifetime = (_capture_component_lifetime(saved['component_lifetime'], attempt=saved['attempt'],
                record_id=record['record_id'], source_url=record['list_url'], detail_url=record.get('detail_url'))
                if 'component_lifetime' in saved else None)
            providers = (_capture_corporate_reference_providers(saved['corporate_reference_providers'],
                attempt=saved['attempt'], record_id=record['record_id'],
                source_url=record['list_url'], detail_url=record.get('detail_url'))
                if 'corporate_reference_providers' in saved else None)
            if providers is not None and (lifetime is None or clock is None):
                raise JsonSafetyError('Private reference providers lack original lifetime or clock')
            l8_lifetime = (_capture_l8_lifetime(saved['corporate_l8_lifetime'], attempt=saved['attempt'],
                record_id=record['record_id'], source_url=record['list_url'], detail_url=record.get('detail_url'))
                if 'corporate_l8_lifetime' in saved else None)
            l7_lifetime = (_capture_l7_lifetime(saved['corporate_l7_lifetime'], attempt=saved['attempt'],
                record_id=record['record_id'], source_url=record['list_url'], detail_url=record.get('detail_url'))
                if 'corporate_l7_lifetime' in saved else None)
            l10b_lifetime = (_capture_l10b_lifetime(saved['corporate_l10b_lifetime'], attempt=saved['attempt'],
                record_id=record['record_id'], source_url=record['list_url'], detail_url=record.get('detail_url'))
                if 'corporate_l10b_lifetime' in saved else None)
            if l10b_lifetime is not None and lifetime is None:
                raise JsonSafetyError('Private L10-B history lacks its component lifetime')
            l10c_lifetime = (_capture_l10c_lifetime(saved['corporate_l10c_lifetime'], attempt=saved['attempt'],
                record_id=record['record_id'], source_url=record['list_url'], detail_url=record.get('detail_url'))
                if 'corporate_l10c_lifetime' in saved else None)
            if l7_lifetime is not None and lifetime is None:
                raise JsonSafetyError('Private L7 history lacks its component lifetime')
            if l10c_lifetime is not None and lifetime is None:
                raise JsonSafetyError('Private L10-C history lacks its component lifetime')
            if l8_lifetime is not None and lifetime is None:
                raise JsonSafetyError('Private L8 history lacks its component lifetime')
            descriptors = saved.get('responses')
            from coretax_corporate_l10d import validate_lifetime
            l10d_lifetime = (validate_lifetime(saved['corporate_l10d_lifetime'], lifetime)
                if 'corporate_l10d_lifetime' in saved else None)
            if not isinstance(descriptors, list) or len(descriptors) > MAX_RESPONSES:
                raise JsonSafetyError('Private checkpoint response budget changed')
            packets, total, seen = [], 0, set()
            for descriptor in descriptors:
                name = descriptor.get('relative_path')
                if (not isinstance(name, str) or '\\' in name or ':' in name
                        or PurePosixPath(name).parent != relative.parent
                        or not re.fullmatch(r'response-[0-9]{4,}\.json', PurePosixPath(name).name)
                        or name in seen or descriptor.get('attempt') != saved['attempt']
                        or 'clock_interval' in descriptor or 'component_lifetime' in descriptor
                        or 'corporate_l8_lifetime' in descriptor or 'corporate_l7_lifetime' in descriptor
                        or 'corporate_reference_providers' in descriptor or 'corporate_l10b_lifetime' in descriptor
                        or 'corporate_l10c_lifetime' in descriptor or 'corporate_l10d_lifetime' in descriptor
                        or descriptor.get('record_id') != record['record_id']
                        or descriptor.get('scope') != list(scope) or type(descriptor['scope'][1]) is not int
                        or type(descriptor.get('bytes')) is not int or descriptor['bytes'] < 0
                        or descriptor['bytes'] > MAX_BODY_BYTES):
                    raise JsonSafetyError('Unsafe private checkpoint response reference')
                seen.add(name)
                total += descriptor['bytes']
                if total > MAX_TOTAL_BYTES:
                    raise JsonSafetyError('Private checkpoint attempt budget changed')
                body = read(guard, name, MAX_BODY_BYTES)
                if len(body) != descriptor['bytes'] or hashlib.sha256(body).hexdigest() != descriptor.get('sha256'):
                    raise JsonSafetyError('Private checkpoint response bytes changed')
                payload = _json(body)
                if _has_secret(payload):
                    raise JsonSafetyError('Private checkpoint no longer meets privacy policy')
                context = dict(descriptor)
                if clock is not None:
                    context['clock_interval'] = dict(clock)
                if lifetime is not None:
                    context['component_lifetime'] = dict(lifetime)
                if providers is not None:
                    context['corporate_reference_providers'] = {**providers, 'builds': dict(providers['builds'])}
                if l8_lifetime is not None:
                    context['corporate_l8_lifetime'] = dict(l8_lifetime)
                if l7_lifetime is not None:
                    context['corporate_l7_lifetime'] = dict(l7_lifetime)
                if l10b_lifetime is not None:
                    context['corporate_l10b_lifetime'] = dict(l10b_lifetime)
                if l10c_lifetime is not None:
                    context['corporate_l10c_lifetime'] = dict(l10c_lifetime)
                if l10d_lifetime is not None:
                    context['corporate_l10d_lifetime'] = dict(l10d_lifetime)
                packets.append({'body': body, 'payload': payload, 'context': context})
            return packets
    except (OSError, ValueError, TypeError, KeyError, IndexError):
        raise JsonSafetyError('Private checkpoint custody cannot be safely verified') from None


def _json_output_entries(run):
    """Derive a closed file set; never enumerate private job directories."""
    from pathlib import PurePosixPath
    layout = _json_output_layout(run)
    entries, seen, sources = [], set(), set()
    for record in run['records']:
        audit = record.get('detail_source')
        if audit is None:
            continue
        if not isinstance(audit, dict):
            raise JsonSafetyError('Invalid JSON evidence audit')
        capture = audit.get('capture')
        if capture is None and audit.get('used') != 'json':
            continue
        if not isinstance(capture, dict):
            raise JsonSafetyError('Missing JSON evidence capture')
        reference = capture.get('manifest')
        if (not isinstance(reference, str) or not re.fullmatch(
                r'returns/json/[0-9]{4,}/[a-f0-9]{32}/manifest\.json', reference)):
            raise JsonSafetyError('Unsafe JSON evidence manifest path')
        responses = capture.get('responses')
        if not isinstance(responses, list) or len(responses) > MAX_RESPONSES:
            raise JsonSafetyError('Invalid JSON evidence response set')
        items = [{'source_path': reference, 'sha256': capture.get('manifest_sha256'),
                  'maximum': 8 * 1024 * 1024}]
        for descriptor in responses:
            name = descriptor.get('relative_path') if isinstance(descriptor, dict) else None
            if (not isinstance(name, str) or '\\' in name or ':' in name
                    or PurePosixPath(name).parent != PurePosixPath(reference).parent
                    or not re.fullmatch(r'response-[0-9]{4,}\.json', PurePosixPath(name).name)):
                raise JsonSafetyError('Unsafe JSON evidence response path')
            items.append({'source_path': name, 'sha256': descriptor.get('sha256'),
                          'maximum': MAX_BODY_BYTES, 'bytes': descriptor.get('bytes')})
        for item in items:
            name = _published_json_path(item['source_path'], record, layout)
            digest = item['sha256']
            if (name.casefold() in seen or item['source_path'] in sources
                    or not isinstance(digest, str)
                    or not re.fullmatch(r'[0-9a-f]{64}', digest)):
                raise JsonSafetyError('Duplicate or invalid JSON evidence declaration')
            seen.add(name.casefold())
            sources.add(item['source_path'])
            item['relative_path'] = name
        entries.append((record, capture, items))
    return entries


def json_output_names(run):
    return [item['relative_path'] for _, _, items in _json_output_entries(run) for item in items]


def verified_json_names(run):
    expected = json_output_names(run)
    if run.get('output_json', [] if not expected else None) != expected:
        raise JsonSafetyError('JSON output declaration differs from selected captures')
    return expected


def _verify_json_stream(stream, item, check_cancel=None):
    stream.seek(0)
    digest, total = hashlib.sha256(), 0
    for chunk in iter(lambda: stream.read(1048576), b''):
        if check_cancel:
            check_cancel()
        total += len(chunk)
        if total > item['maximum']:
            raise JsonSafetyError('JSON evidence exceeds its byte budget')
        digest.update(chunk)
    if (digest.hexdigest() != item['sha256']
            or 'bytes' in item and total != item['bytes']):
        raise JsonSafetyError('JSON evidence bytes changed')
    stream.seek(0)


@contextmanager
def json_custody(run, folder, *, published=True, target_layout=None, check_cancel=None):
    """Hold source-layout bytes; optionally relocate the same declared evidence."""
    if published:
        verified_json_names(run)
    entries = _json_output_entries(run)
    destinations = (_json_output_entries({**run, 'json_output_layout': target_layout})
                    if target_layout is not None else entries)
    target_items = {item['source_path']: item for _, _, items in destinations for item in items}
    if not entries:
        yield [], {}
        return
    root = Path(folder).absolute()
    if '..' in root.parts:
        raise JsonSafetyError('Unsafe JSON evidence folder')
    with DirectoryGuard() as guard, ExitStack() as readers:
        streams, items = {}, []
        for record, capture, record_items in entries:
            # Bind every byte to the unchanged manifest and literal selected scope.
            packets = checkpoint_bodies(root, capture, record,
                [run['npwp'], run['year'], run['year_basis']],
                published=published, output_layout=_json_output_layout(run), check_cancel=check_cancel)
            del packets
            for item in record_items:
                if check_cancel:
                    check_cancel()
                name = item['relative_path'] if published else item['source_path']
                parent = (root / name).parent
                guard.include({p: _ordinary_directory(p) for p in reversed([parent, *parent.parents])})
                stream = readers.enter_context(locked_file(root / name))
                _verify_json_stream(stream, item, check_cancel)
                destination = target_items[item['source_path']]
                streams[destination['relative_path']] = stream
                items.append(destination)
        yield items, streams
        for item in items:
            _verify_json_stream(streams[item['relative_path']], item, check_cancel)


def verify_existing_json(run, folder):
    """Refuse changed selected destination evidence before CLI replacement.

    A destination can contain only some selected attempts. Missing new files
    are allowed; every existing selected file must match its declared bytes.
    """
    entries = _json_output_entries(run)  # Validate the declared source layout first.
    if not entries:
        return
    legacy = {key: value for key, value in run.items() if key != 'json_output_layout'}
    # A migration must not hide changed selected evidence left at its old path.
    variants = (legacy, {**legacy, 'json_output_layout': JSON_OUTPUT_LAYOUT})
    selected = {item['relative_path']: item for variant in variants
                for _, _, items in _json_output_entries(variant) for item in items}
    root = Path(folder).absolute()
    if '..' in root.parts:
        raise JsonSafetyError('Unsafe JSON evidence destination')
    with DirectoryGuard() as guard:
        guard.include({p: _ordinary_directory(p) for p in reversed([root, *root.parents])})
        for item in selected.values():
            parent = root
            parts = Path(item['relative_path']).parts
            for index, component in enumerate(parts):
                if any(p.name.casefold() == component.casefold() and p.name != component
                       for p in parent.iterdir()):
                    raise JsonSafetyError('JSON evidence destination has a case alias')
                target = parent / component
                if not target.exists() and not target.is_symlink():
                    break
                if index == len(parts) - 1:
                    with locked_file(target) as stream:
                        _verify_json_stream(stream, item)
                else:
                    guard.include({target: _ordinary_directory(target)})
                    parent = target


def copy_held_json(items, streams, folder, check_cancel=None):
    """Copy declared evidence only; manifests retain their original references."""
    root = Path(folder).absolute()
    with DirectoryGuard() as guard:
        for item in items:
            if check_cancel:
                check_cancel()
            target = root / item['relative_path']
            for parent in reversed([target.parent, *target.parent.parents]):
                if parent == root or parent.is_relative_to(root):
                    parent.mkdir(exist_ok=True)
                    guard.include({p: _ordinary_directory(p) for p in reversed([parent, *parent.parents])})
            stream = streams[item['relative_path']]
            _verify_json_stream(stream, item, check_cancel)
            with target.open('xb') as destination:
                for chunk in iter(lambda: stream.read(1048576), b''):
                    if check_cancel:
                        check_cancel()
                    destination.write(chunk)
            with locked_file(target) as copied:
                _verify_json_stream(copied, item, check_cancel)
            stream.seek(0)
