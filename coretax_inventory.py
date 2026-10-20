"""Source-backed inventory filtering, independent of return/detail extraction."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json

from coretax_json import JsonSafetyError, validate_period_filter
from spt_desktop import diagnostics


def plan_year_filters(catalog, year, basis, *, now=None):
    """Return disjoint candidate filters; local literal-period checks remain mandatory."""
    def unavailable(reason, legacy_reason='unverified_period_catalog'):
        diagnostics.record('catalog.validation', catalog_reason=reason)
        return {'eligible': False, 'filters': [], 'reason': legacy_reason}

    if basis != 'period' or type(year) is not int or not 1900 <= year <= 2100:
        return unavailable('scope_unsupported', 'unsupported_year_scope')
    if not isinstance(catalog, dict):
        return unavailable('catalog_missing')
    if catalog.get('ReferenceDataType') != 'PERIOD':
        return unavailable('catalog_type')
    if catalog.get('language') != 'id-ID':
        return unavailable('catalog_language')
    if not isinstance(catalog.get('Checksum'), str) or not catalog['Checksum']:
        return unavailable('catalog_checksum')
    if not isinstance(catalog.get('Details'), list) or not catalog['Details']:
        return unavailable('catalog_details')
    now = datetime.now(timezone.utc) if now is None else now
    try:
        expires = datetime.fromisoformat(catalog['ExpiryDate'].replace('Z', '+00:00'))
        if now.tzinfo is None or expires.tzinfo is None or expires <= now:
            return unavailable('catalog_expired_or_unbound', 'expired_or_unbound_period_catalog')
    except (KeyError, TypeError, ValueError, AttributeError):
        return unavailable('catalog_expiry_invalid')
    try:
        fingerprint = hashlib.sha256(json.dumps(catalog, ensure_ascii=False, sort_keys=True,
                                                separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()
    except (KeyError, TypeError, ValueError, AttributeError):
        return unavailable('catalog_serialization')

    from coretax_exporter import in_scope

    seen, extra = set(), []
    token = str(year)
    for row in catalog['Details']:
        if not isinstance(row, dict):
            return unavailable('catalog_row')
        code, label = row.get('Code'), row.get('CodeDescription')
        if not isinstance(code, str) or not code or code != code.strip():
            return unavailable('catalog_code')
        if not isinstance(label, str) or not label.strip():
            return unavailable('catalog_label')
        if code in seen:
            return unavailable('catalog_duplicate')
        seen.add(code)
        if token in code:
            continue
        try:
            wanted = in_scope({'Masa Pajak': label}, year, 'period')
        except ValueError:
            # Preserve ambiguity for the collector to report, rather than hiding a row.
            wanted = True
        if wanted:
            extra.append(code)
    common = {'PropertyName': 'TaxPeriodCode', 'CaseSensitive': True, 'AsString': False}
    filters = [{**common, 'MatchMode': 'contains', 'Value': token}]
    if extra:
        extra.sort()
        filters.append({**common, 'MatchMode': 'equals' if len(extra) == 1 else 'any' + '-equals' * len(extra),
                        'Value': extra[0] if len(extra) == 1 else extra})
    # Retain the raw snapshot hash for custody. Renewal/order is not a change
    # to period semantics; catalog freshness is independently validated above.
    binding = {key: catalog[key] for key in ('ReferenceDataType', 'language', 'Checksum')}
    binding['Details'] = sorted(
        ({key: row[key] for key in ('Code', 'CodeDescription')} for row in catalog['Details']),
        key=lambda row: row['Code'])
    binding_fingerprint = hashlib.sha256(json.dumps(binding, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()
    diagnostics.record('catalog.validation', catalog_reason='available', count=len(catalog['Details']))
    return {'eligible': True, 'filters': filters, 'catalog_sha256': fingerprint,
            'catalog_binding_sha256': binding_fingerprint,
            'catalog_checksum': catalog['Checksum'], 'catalog_expires': catalog['ExpiryDate']}


def prove_period_equivalence(left, right, catalog, year):
    """Return private source evidence for one unique code/label pair, never a guess."""
    if not isinstance(left, str) or not isinstance(right, str) or left == right:
        return None
    plan = plan_year_filters(catalog, year, 'period')
    if not plan['eligible']:
        return None
    pairs = [row for row in catalog['Details']
             if (row['Code'] == left and row['CodeDescription'] == right)
             or (row['Code'] == right and row['CodeDescription'] == left)]
    if len(pairs) != 1:
        return None
    code, label = pairs[0]['Code'], pairs[0]['CodeDescription']
    # A caption shared by codes, or a caption that is another code, cannot
    # identify a unique source period. Literal equality elsewhere is unchanged.
    if sum(row['CodeDescription'] == label for row in catalog['Details']) != 1:
        return None
    if any(row['Code'] == label or row['CodeDescription'] == code for row in catalog['Details']):
        return None
    return {'code': code, 'label': label, 'catalog_sha256': plan['catalog_sha256'],
            'catalog_binding_sha256': plan['catalog_binding_sha256']}


def rewrite_inventory_request(request, condition, *, taxpayer_id):
    """Only alter filters on an owned, unfiltered submitted-list request."""
    if (not isinstance(request, dict) or not isinstance(taxpayer_id, str) or not taxpayer_id
            or request.get('TaxpayerAggregateIdentifier') != taxpayer_id
            or request.get('isArchieved') is not False or request.get('Filters') != []):
        raise ValueError('Request does not match the owned unfiltered submitted scope')
    first, rows = request.get('First'), request.get('Rows')
    if type(first) is not int or first < 0 or type(rows) is not int or rows < 1 or first % rows:
        raise ValueError('Invalid owned request pagination')
    try:
        validate_period_filter(condition)
    except JsonSafetyError as exc:
        raise ValueError('Unsupported owned period filter') from exc
    result = deepcopy(request)
    result['Filters'] = [deepcopy(condition)]
    return result


PERIOD_CATALOG_JS = r'''() => new Promise(resolve=>{
 let settled=false, db=null, tx=null;
 const done=(reason,catalog=null)=>{
  if(settled)return;
  settled=true;clearTimeout(timer);
  if(tx&&reason!=='available'){try{tx.abort();}catch{}}
  if(db){try{db.close();}catch{}}
  resolve({reason,catalog});
 };
 const timer=setTimeout(()=>done('read_timeout'),5000);
 (async()=>{
  if(typeof indexedDB==='undefined'||typeof indexedDB.databases!=='function'){
   done('enumeration_unavailable');return;
  }
  let databases;
  try{databases=await indexedDB.databases();}
  catch{done('enumeration_error');return;}
  if(settled)return;
  if(!databases.some(d=>d.name==='e-tax-database')){done('database_missing');return;}
  let open;
  try{open=indexedDB.open('e-tax-database');}
  catch{done('open_error');return;}
  open.onupgradeneeded=()=>{
   try{open.transaction.abort();}finally{
    try{open.result.close();}catch{}
    done('upgrade_refused');
   }
  };
  open.onerror=()=>done('open_error');
  open.onblocked=()=>done('open_blocked');
  open.onsuccess=()=>{
   db=open.result;
   if(settled){db.close();return;}
   db.onversionchange=()=>done('version_changed');
   if(!db.objectStoreNames.contains('referenceDataStore')){done('store_missing');return;}
   try{
    tx=db.transaction('referenceDataStore','readonly');
    const request=tx.objectStore('referenceDataStore').get(['PERIOD','id-ID']);
    tx.onerror=tx.onabort=()=>done('read_error');
    request.onerror=()=>done('read_error');
    request.onsuccess=()=>{
     if(settled)return;
     try{
      const x=request.result;
      if(x===undefined||x===null){done('record_missing');return;}
      if(x.ReferenceDataType!=='PERIOD'||x.language!=='id-ID'){done('record_identity');return;}
      const catalog={ReferenceDataType:x.ReferenceDataType,language:x.language,Checksum:x.Checksum,
       ExpiryDate:x.ExpiryDate instanceof Date?x.ExpiryDate.toISOString():x.ExpiryDate,
       Details:Array.isArray(x.Details)?x.Details.map(d=>({Code:d.Code,CodeDescription:d.CodeDescription})):null};
      done('available',catalog);
     }catch{done('projection_error');}
    };
   }catch{done('read_error');}
  };
 })().catch(()=>done('read_error'));
})'''


def validate_partition_response(response, condition):
    """Do not let DOM fallback or detail restoration weaken the effective filter."""
    validate_period_filter(condition)
    binding = response.get('binding') or {}
    if (binding.get('request', {}).get('Filters') != [condition]
            or not binding.get('filter_rewrite')):
        raise JsonSafetyError('Response is not bound to the declared inventory filter')
    mode, value = condition['MatchMode'], condition['Value']
    for row in response['rows']:
        code = row.get('TaxPeriodCode')
        if not isinstance(code, str):
            raise JsonSafetyError('Missing period in filtered response')
        if mode == 'contains':
            matches = value in code
        elif mode == 'equals':
            matches = code == value
        else:
            matches = code in value
        if not matches:
            raise JsonSafetyError('Record period/filter contradicts declared partition')


def read_period_catalog(page):
    """Read only the source PERIOD cache; never fetch metadata or create a database."""
    from urllib.parse import urlsplit
    url = urlsplit(page.url)
    if (url.scheme != 'https' or url.netloc != 'coretax.intranet.pajak.go.id'
            or not url.path.startswith('/returnsheets/')):
        diagnostics.record('catalog.read', catalog_reason='origin_blocked')
        return None
    try:
        result = page.evaluate(PERIOD_CATALOG_JS)
    except Exception:
        diagnostics.record('catalog.read', catalog_reason='evaluation_error')
        raise
    if not isinstance(result, dict):
        diagnostics.record('catalog.read', catalog_reason='evaluation_error')
        return None
    catalog = result.get('catalog')
    fields = {'catalog_reason': result.get('reason')}
    if isinstance(catalog, dict) and isinstance(catalog.get('Details'), list):
        fields['count'] = len(catalog['Details'])
    diagnostics.record('catalog.read', **fields)
    return catalog if isinstance(catalog, dict) else None


class InventoryFilterRoute:
    """Bind one observed read request to one immutable candidate partition."""

    endpoint = 'https://coretax.intranet.pajak.go.id/returnsheet/api/returnsheetssubmitted'

    def __init__(self, page, taxpayer_id, condition, *, check_cancel=None):
        validate_period_filter(condition)
        self.page = page
        self.taxpayer_id = taxpayer_id
        self.condition = deepcopy(condition)
        self.check_cancel = check_cancel
        self.error = None
        self._requests = {}
        self._handler = self._handle

    def __enter__(self):
        self.page.route(self.endpoint, self._handler)
        return self

    def __exit__(self, *_):
        self.page.unroute(self.endpoint, self._handler)
        self._requests.clear()

    def _handle(self, route):
        request = route.request
        try:
            if self.check_cancel:
                self.check_cancel()
            expected = ('https://coretax.intranet.pajak.go.id/returnsheets/id-ID/'
                        'submitted-returnsheets/' + self.taxpayer_id)
            if (request.method != 'POST' or request.url != self.endpoint
                    or request.frame != self.page.main_frame
                    or request.frame.url.rstrip('/') != expected):
                raise ValueError('Unexpected request owner or submitted route')
            original = request.post_data_json
            if original == {'TaxpayerAggregateIdentifier': self.taxpayer_id}:
                # The source also reads an identity-only auxiliary list here.
                # Preserve it unchanged, never as filtered-grid evidence.
                route.fallback()
                return
            effective = rewrite_inventory_request(original, self.condition, taxpayer_id=self.taxpayer_id)
            encode = lambda body: json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
            evidence = {'original_sha256': hashlib.sha256(encode(original).encode()).hexdigest(),
                        'effective_sha256': hashlib.sha256(encode(effective).encode()).hexdigest()}
            self._requests[request] = (deepcopy(original), deepcopy(effective), evidence)
            # fallback keeps runner fixtures and any earlier transport route in control.
            route.fallback(post_data=json.dumps(effective, ensure_ascii=False))
        except Exception:
            self.error = JsonSafetyError('Owned inventory filter request was rejected')
            route.abort()

    def effective_binding(self, request):
        if self.error:
            raise self.error
        saved = self._requests.pop(request, None)
        if saved is None:
            raise JsonSafetyError('Filtered response has no owned rewrite evidence')
        original, effective, evidence = saved
        observed = request.post_data_json
        if observed != original and observed != effective:
            raise JsonSafetyError('Request changed outside the owned inventory rewrite')
        if effective['Filters'] != [self.condition]:
            raise JsonSafetyError('Inventory filter changed during request processing')
        return deepcopy(effective), deepcopy(evidence)
