"""Closed L10-D original-data custody, never checkbox/calendar presentation.

The raw response and generic evidence table remain authoritative. This owner
cannot enable a native capture or a worksheet by itself.
"""
from datetime import date
import re

from coretax_build_pins import load_build_pins
from coretax_json import (ORIGIN, JsonSafetyError, _CorporateNumber, _UnsupportedMetadata,
                          _capture_component_lifetime)

PROVIDERS = tuple(ORIGIN + '/returnsheets/id-ID/' + name for name in (
    '525.c5690c441d8dbc45.js', 'main.16a01374a2a1ece5.js', 'vendor.c32c4ee39d966e30.js'))
KIND = 'corporate-l10d-originals-v1'
FLAG = 'IsObligationTransferPricing'
FINAL_CUSTODY_BLOCKER = 'unverified_corporate_l10d_final_selection_custody'

# This synchronous sample is intended for the shared JOINT final browser RPC,
# never for a sequential extra end sampler. It reads no input/checked values,
# Angular state, row text, cache, source bodies or business dates.
HISTORY_JS = r"""(d) => {
 // corporate-l10d-history: independent finite structural ownership.
 const selectors=['rshshr-corporate-income-tax-return','rshshr-citr-main-form','rshshr-citr-l10d-form'];
 const candidates=selectors.join(',');
 const initialClear=d===document&&!d.querySelector(candidates);
 const state={available:initialClear,changed:false,complete:false};
 const disabledNodes=new WeakSet();
 let roles=[null,null,null],ancestors=new Set(),remaining=4096;
 let tab=null,panel=null,li=null,view=null,started=false,ended=false;
 const observer=new MutationObserver(records=>process(records));
 const unavailable=()=>{state.available=false;state.complete=false;};
 const debit=()=>{if(--remaining<0){unavailable();return false;}return true;};
 const changed=()=>{state.changed=true;state.complete=false;};
 const remember=node=>{
   let depth=0;
   for(let p=node;p;p=p.parentElement){
     ancestors.add(p);
     if(++depth>64||ancestors.size>128){unavailable();return;}
   }
 };
 const visit=(node,removed)=>{
   if(!debit())return;
   const index=selectors.findIndex(selector=>node.matches(selector));
   if(removed||roles[index]&&roles[index]!==node){changed();return;}
   if(!roles[index]){roles[index]=node;remember(node);}
   if(!node.isConnected||node.ownerDocument!==d)changed();
 };
 const inspect=(node,removed)=>{
   if(node.nodeType!==1)return false;
   let relevant=false;
   if(node.matches(candidates)){relevant=true;visit(node,removed);}
   for(const child of node.querySelectorAll(candidates)){
     relevant=true;visit(child,removed);if(remaining<0)break;
   }
   return relevant;
 };
 const local=target=>roles.slice(1).some(role=>role&&(role===target||role.contains(target)));
 const process=records=>{
   if(!initialClear)return;
   for(const record of records){
     if(record.type==='attributes'){
       // Ignore normal tab highlighting/visibility. A transient disabled or
       // controlled-panel mutation remains a contradiction after restoration.
       const target=record.target,name=record.attributeName,old=record.oldValue;
       const now=target.getAttribute(name);
       const disabled=(name==='class'&&(String(old).split(/\s+/).includes('p-disabled')||target.classList.contains('p-disabled')))||
          (name==='aria-disabled'&&(old==='true'||now==='true'));
       if(disabled&&roles[0]&&roles[0].contains(target)&&target.closest('.p-tabview-nav')&&
          (target.localName==='li'||target.getAttribute('role')==='tab')){
         disabledNodes.add(target);debit();
       }
       if(!started)continue;
       const fixed=target===tab||target===panel||target===li||target===view||roles.includes(target);
       if(!fixed)continue;
       if(disabled||
          (['aria-controls','href','id'].includes(name)&&old!==now))changed();
       continue;
     }
     let relevant=false;
     for(const node of record.removedNodes){
       if(node.nodeType!==1)continue;
       if(roles.some(role=>role&&(node===role||node.contains(role)))||ancestors.has(node)||
          [tab,panel,li,view].some(role=>role&&(node===role||node.contains(role))))changed();
       if(inspect(node,true))relevant=true;
       // An emptied detached wrapper cannot reconstruct its former children.
       if(local(record.target)&&!relevant)unavailable();
     }
     for(const node of record.addedNodes){if(inspect(node,false))relevant=true;}
     if(relevant&&!debit())break;
   }
 };
 const owned=()=>{
   if(!initialClear)return false;
   if(d!==document){changed();return false;}
   if(roles.some(role=>!role))return false;
   if(roles.some(role=>!role.isConnected||role.ownerDocument!==d)){changed();return false;}
   if(!selectors.every((selector,index)=>{
     const nodes=d.querySelectorAll(selector);return nodes.length===1&&nodes[0]===roles[index];
   })){changed();return false;}
   for(const role of roles.slice(1)){
     if(role.closest(selectors[0])!==roles[0]){changed();return false;}
     for(let p=role.parentElement;p&&p!==roles[0];p=p.parentElement){
       const name=p.localName;
       if(name.includes('-')&&(name.endsWith('-form')||!(/^(p|ui)-/.test(name)||/^rsh(shr)?-(citr|corporate)-/.test(name)))){
         if(started)changed();else unavailable();return false;
       }
     }
   }
   return true;
 };
 const enabled=visible=>{
   if(!tab||!panel||!li||!view||[tab,panel,li,view].some(node=>!node.isConnected||node.ownerDocument!==d))return false;
   const id=tab.getAttribute('aria-controls'),href=tab.getAttribute('href');
   if(tab.closest('li')!==li||tab.closest('.p-tabview')!==view||
      roles[2].closest('.p-tabview-panel')!==panel||roles[2].closest('.p-tabview')!==view||
      !roles[0].contains(view)||panel.closest('.p-tabview')!==view||!id||panel.id!==id||
      !panel.matches('.p-tabview-panel')||tab.textContent.trim()!=='L10-D'||
      [...view.querySelectorAll('[id]')].filter(node=>node.id===id).length!==1||
      li.classList.contains('p-disabled')||tab.getAttribute('aria-disabled')==='true'||
      !(href===null||href===''||href==='#'||href==='#'+id))return false;
   if(!visible)return true;
   for(let p=roles[2];p;p=p.parentElement){const style=getComputedStyle(p);
     if(p.hidden||style.display==='none'||style.visibility==='hidden'||style.visibility==='collapse')return false;}
   return !!roles[2].getClientRects().length&&!!tab.getClientRects().length;
 };
 const sample=()=>{
   process(observer.takeRecords());
   const valid=owned();
   if(started&&valid&&!enabled(false))changed();
   state.complete=!!(state.available&&!state.changed&&valid&&started&&ended);
   return {...state};
 };
 observer.observe(d,{childList:true,subtree:true,attributes:true,attributeOldValue:true,
   attributeFilter:['class','aria-disabled','aria-controls','href','id']});
 return {sample,bind:args=>{
   process(observer.takeRecords());
   if(!owned())return sample();
   if(args.form!==roles[2])changed();
   if(args.phase==='start'&&!started&&!ended){
     tab=args.tab;panel=args.panel;li=tab&&tab.closest('li');view=roles[2].closest('.p-tabview');
     if(disabledNodes.has(tab)||disabledNodes.has(li))unavailable();
     for(const node of [tab,panel,li,view])if(node)remember(node);
   }else if(args.phase!=='end'||!started||ended||args.tab!==tab||args.panel!==panel)changed();
   if(!enabled(true)){if(started)changed();else unavailable();}
   if(state.available&&!state.changed){if(args.phase==='start')started=true;else ended=true;}
   return sample();
 },disconnect:()=>{observer.disconnect();roles=[];ancestors.clear();tab=panel=li=view=null;}};
}"""


class L10DHistory:
    """D-owned history transport; final joint snapshot/sealing belongs to capture.

    Boundary state is only a candidate. No method manufactures native admission
    or a final manifest capability from sequential RPCs.
    """

    def __init__(self):
        self.handle = None
        self.unavailable = False
        self.requested = False
        self.armed = False

    def probe(self, operation, cancel):
        cancel()
        try:
            value = operation()
        except JsonSafetyError:
            cancel()
            raise
        except Exception:
            value = None
        cancel()
        return value

    def arm(self, document, cancel):
        if self.armed:
            raise JsonSafetyError('Corporate L10-D history cannot be rearmed')
        self.armed = True
        def acquire():
            self.handle = document.evaluate_handle(HISTORY_JS)
            return self.handle
        self.probe(acquire, cancel)

    def accept_sample(self, state, *, boundary=False):
        if (not isinstance(state, dict) or set(state) != {'available', 'changed', 'complete'}
                or any(type(value) is not bool for value in state.values())):
            self.unavailable = True
            return None
        if state['changed']:
            raise JsonSafetyError('Observed corporate L10-D child history changed')
        if not state['available'] or not boundary and not state['complete']:
            self.unavailable = True
        return dict(state) if not self.unavailable else None

    def bind(self, form, tab, panel, *, phase, cancel):
        cancel()
        if phase not in ('start', 'end'):
            raise ValueError('Unknown L10-D structural boundary')
        self.requested = True
        if self.handle is None:
            return False
        handles = {}
        try:
            for key, locator in (('form', form), ('tab', tab), ('panel', panel)):
                def acquire():
                    handles[key] = locator.element_handle()
                    return handles[key]
                if self.probe(acquire, cancel) is None:
                    self.unavailable = True
                    return False
            state = self.probe(lambda: self.handle.evaluate(
                '(h,args) => h.bind(args)', {**handles, 'phase': phase}), cancel)
            state = self.accept_sample(state, boundary=phase == 'start')
            return state is not None
        finally:
            for handle in reversed(list(handles.values())):
                if handle is not None:
                    try:
                        handle.dispose()
                    except Exception:  # nosec B110 - Cleanup must preserve Stop/safety.
                        pass

    def close(self):
        handle, self.handle = self.handle, None
        if handle is None:
            return
        for release in (lambda: handle.evaluate('(h) => h.disconnect()'), handle.dispose):
            try:
                release()
            except Exception:  # nosec B110 - Release both resources without masking Stop.
                pass


def validate_lifetime(value, component):
    """Validate a manifest-owned final fact; never produce one during replay.

    The capture owner may call this only after a jointly consistent final
    sample. A matching schema or observer hint is not a producer capability.
    """
    identity = ('attempt', 'record_id', 'source_url', 'detail_url')
    facts = {'fresh_root', 'fresh_main', 'fresh_child', 'stable_root', 'stable_main',
             'stable_child', 'enabled_boundaries', 'final_joint_snapshot'}
    if not isinstance(component, dict):
        raise JsonSafetyError('Captured L10-D history lacks its component lifetime')
    _capture_component_lifetime(component, **{key: component.get(key) for key in identity})
    if (not isinstance(value, dict)
            or set(value) != {*identity, *facts, 'kind', 'selection_rule'}
            or value.get('kind') != 'corporate-l10d-spa-v1'
            or value.get('selection_rule') != 'submitted-immutable-induk-selection-v1'
            or any(value.get(key) != component[key] for key in identity)
            or any(value.get(key) is not True for key in facts)):
        raise JsonSafetyError('Captured L10-D history is invalid or unbound')
    return dict(value)


def validate_binding(binding):
    """An original-only offer must not smuggle display or capture authority."""
    offer = binding.get('original_custody')
    if (binding.get('name') != 'L10-D' or binding.get('paths') != [['L10dFormData']]
            or any(key in binding for key in ('disabled', 'primary', 'projection', 'raw_negative_projection'))
            or any(binding.get(key) for key in ('grids', 'responses', 'dependencies'))
            or not isinstance(offer, dict)
            or set(offer) != {'kind', 'builds', 'route', 'owner_binding'}
            or offer['kind'] != KIND or type(offer['route']) is not str
            or offer['owner_binding'] != 'observed-enabled-after-induk-v1'
            or not isinstance(offer['builds'], dict)
            or any(type(key) is not str or value is not None and type(value) is not str
                   for key, value in offer['builds'].items())):
        raise JsonSafetyError('Observed L10-D original custody is malformed or misplaced')


def approved_builds(builds):
    """Positive exact equality with all three reviewed loader pins, never None == None."""
    pins = load_build_pins()
    return (isinstance(builds, dict) and set(builds) == set(PROVIDERS)
            and all(type(pins.get(url)) is str and re.fullmatch(r'[a-f0-9]{64}', pins[url])
                    and type(builds[url]) is str and re.fullmatch(r'[a-f0-9]{64}', builds[url])
                    and builds[url] == pins[url] for url in PROVIDERS))


def collect_original_custody(binding, observed_forms, *, root, payload, record, event):
    """Collect a finite original-only candidate; this is NEVER native admission.

    Current Document/owner evidence and equal saved flags do not independently
    prove final Induk selection or continuous child lifetime. Keep that precise
    blocker explicit. Do not manufacture a finality fact from this observation.
    """
    validate_binding(binding)
    offer = binding['original_custody']
    if not approved_builds(offer['builds']):
        raise _UnsupportedMetadata('unverified_corporate_l10d_loaded_pins')
    fields = record.get('source_fields', {})
    route = (ORIGIN + '/returnsheets/id-ID/corporate-income-tax-return/' + '/'.join(
        str(value) for value in (fields.get('TaxpayerAggregateIdentifier'), record['record_id'],
                                fields.get('TaxTypeCode'), fields.get('AggregateIdentifier'))) + '?view=true')
    if (offer['route'] != route or offer['route'] != event['frame_url']
            or record.get('source_status') != 'SPT Dilaporkan'
            or fields.get('TaxTypeCode') != 'ICT_RCIT' or fields.get('ReturnSheetTypeCode') != 'ICT_RCITR'
            or fields.get('ReturnSheetModel') != 'Normal'
            or record.get('meta', {}).get('Model SPT') != 'Normal'
            or payload.get('ReturnSheetStatusCode') != 'SUBMITTED'
            or payload.get('ReturnSheetModel') != 'NORMAL' or root.get('TaxType') != 'ICT_RCIT'
            or any(key not in payload or payload[key] is not None
                   for key in ('PreviousFormData', 'LastSubmittedFormData'))
            or not isinstance(root.get('MainFormData'), dict)
            or any(type(owner.get(FLAG)) is not _CorporateNumber or owner[FLAG] != '1'
                   for owner in (payload, root['MainFormData']))
            or not any(form.get('name') == 'Induk'
                       for form in observed_forms[:observed_forms.index(binding)])
            or event.get('component_lifetime') is None):
        raise _UnsupportedMetadata('unverified_corporate_l10d_source_profile')
    _capture_component_lifetime(event['component_lifetime'], attempt=event['attempt'],
        record_id=record['record_id'], source_url=record['list_url'], detail_url=route)
    originals = retain_originals(root, payload, sequence=event['sequence'])
    predicates = []
    for owner, keys, container, prefix in (
            (payload, (FLAG, 'PreviousFormData', 'LastSubmittedFormData', 'ReturnSheetStatusCode',
                       'ReturnSheetModel'), ['Payload'], []),
            (root['MainFormData'], (FLAG,), ['Payload', 'CurrentFormData'], ['MainFormData'])):
        for key in keys:
            value = owner[key]
            predicates.append({'container': list(container), 'path': [*prefix, key], 'present': True,
                'type': 'null' if value is None else 'number' if type(value) is _CorporateNumber else 'string',
                'value': str(value) if type(value) is _CorporateNumber else value,
                'response_sequence': event['sequence'], 'rule': 'retained-original-custody-predicate'})
    return {'form': 'L10-D', 'kind': KIND, 'builds': dict(offer['builds']),
        'native_admission': False, 'blocker': FINAL_CUSTODY_BLOCKER,
        'source': {'response_sequence': event['sequence'], 'body_sha256': event['sha256'],
                   'attempt': event['attempt'], 'container': ['Payload', 'CurrentFormData'], 'path': [ROOT]},
        'originals': originals, 'predicate_values': predicates}

ROOT = 'L10dFormData'
CHECKS = tuple(f'{owner}Documentary{i}' for owner in ('Master', 'Local') for i in range(1, 6))
DATES = ('MasterDocumentAvailableDate', 'LocalDocumentAvailableDate')


def _original_date(value):
    # A closed ORIGINAL string grammar, not new Date()/calendar equivalence.
    # Do not borrow a renderer's timezone, sentinel, default or clock rules.
    if value is None:
        return
    if (type(value) is not str or not re.fullmatch(
            r'[0-9]{4}-[0-9]{2}-[0-9]{2}(?:T00:00:00(?:\.000)?(?:Z|\+07:00)?)?', value)):
        raise _UnsupportedMetadata('unsupported_corporate_l10d_date_original')
    try:
        day = date.fromisoformat(value[:10])
        if not 1970 <= day.year <= 2100:
            raise ValueError
    except ValueError:
        raise _UnsupportedMetadata('unsupported_corporate_l10d_date_original') from None


def retain_originals(root, payload, *, sequence):
    """Retain the exact closed source-root shape and fourteen typed originals.

    Missing, null, false and an empty object are different facts. Unsupported
    shapes refuse rather than manufacture a control or erase a guarded operand.
    The caller owns packet privacy, selected identity, and lifecycle validation.
    """
    form = root.get(ROOT) if isinstance(root, dict) else None
    if not isinstance(form, dict) or set(form) != {*CHECKS, *DATES}:
        raise _UnsupportedMetadata('unsupported_corporate_l10d_original_shape')
    if any(type(form[key]) is not bool for key in CHECKS):
        raise _UnsupportedMetadata('unsupported_corporate_l10d_checklist_original')
    for key in DATES:
        _original_date(form[key])
    if (not isinstance(payload, dict) or type(payload.get('TIN')) is not str
            or not re.fullmatch(r'[0-9]{16}', payload['TIN'])
            or type(payload.get('PeriodYear')) is not _CorporateNumber
            or not re.fullmatch(r'[0-9]{4}', payload['PeriodYear'])
            or not 1970 <= int(payload['PeriodYear']) <= 2100
            or type(sequence) is not int or sequence <= 0):
        raise _UnsupportedMetadata('unsupported_corporate_l10d_header_originals')
    values = []
    for owner, keys, container, prefix in (
            (form, form, ['Payload', 'CurrentFormData'], [ROOT]),
            (payload, ('TIN', 'PeriodYear'), ['Payload'], [])):
        for key in keys:
            value = owner[key]
            kind = ('boolean' if type(value) is bool else 'number' if type(value) is _CorporateNumber
                    else 'null' if value is None else 'string')
            values.append({'container': list(container), 'path': [*prefix, key],
                'present': True, 'type': kind,
                'value': str(value) if type(value) is _CorporateNumber else value,
                'response_sequence': sequence, 'rule': 'original-only-no-display'})
    return {'kind': 'corporate-l10d-originals-v1',
        'root': {'container': ['Payload', 'CurrentFormData'], 'path': [ROOT],
                 'present': True, 'type': 'object', 'keys': list(form)},
        'values': values,
        'dependencies': [{'target': [ROOT, DATES[1]],
            'operands': [[ROOT, DATES[0]], [ROOT, DATES[1]]],
            'rule': 'pinned-local-date-guarded-by-master-originals-only'}]}
