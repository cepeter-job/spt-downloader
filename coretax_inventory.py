"""Source-backed inventory filtering, independent of return/detail extraction."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json

from coretax_json import JsonSafetyError, validate_period_filter


def plan_year_filters(catalog, year, basis, *, now=None):
    """Return disjoint candidate filters; local literal-period checks remain mandatory."""
    fallback = {'eligible': False, 'filters': [], 'reason': 'unverified_period_catalog'}
    if basis != 'period' or type(year) is not int or not 1900 <= year <= 2100:
        return {**fallback, 'reason': 'unsupported_year_scope'}
    if (not isinstance(catalog, dict) or catalog.get('ReferenceDataType') != 'PERIOD'
            or catalog.get('language') != 'id-ID'
            or not isinstance(catalog.get('Checksum'), str) or not catalog['Checksum']
            or not isinstance(catalog.get('Details'), list) or not catalog['Details']):
        return fallback
    now = datetime.now(timezone.utc) if now is None else now
    try:
        expires = datetime.fromisoformat(catalog['ExpiryDate'].replace('Z', '+00:00'))
        if now.tzinfo is None or expires.tzinfo is None or expires <= now:
            return {**fallback, 'reason': 'expired_or_unbound_period_catalog'}
        fingerprint = hashlib.sha256(json.dumps(catalog, ensure_ascii=False, sort_keys=True,
                                                separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()
    except (KeyError, TypeError, ValueError, AttributeError):
        return fallback

    from coretax_exporter import in_scope

    seen, extra = set(), []
    token = str(year)
    for row in catalog['Details']:
        if not isinstance(row, dict):
            return fallback
        code, label = row.get('Code'), row.get('CodeDescription')
        if (not isinstance(code, str) or not code or code != code.strip()
                or not isinstance(label, str) or not label.strip() or code in seen):
            return fallback
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
    return {'eligible': True, 'filters': filters, 'catalog_sha256': fingerprint,
            'catalog_checksum': catalog['Checksum'], 'catalog_expires': catalog['ExpiryDate']}


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


PERIOD_CATALOG_JS = r'''async () => {
 if(typeof indexedDB.databases !== 'function')return null;
 if(!(await indexedDB.databases()).some(d=>d.name==='e-tax-database'))return null;
 return await new Promise(resolve=>{
  let settled=false;
  const done=value=>{if(!settled){settled=true;clearTimeout(timer);resolve(value);}};
  const timer=setTimeout(()=>done(null),5000);
  const open=indexedDB.open('e-tax-database');
  open.onupgradeneeded=()=>{open.transaction.abort();done(null);};
  open.onerror=open.onblocked=()=>done(null);
  open.onsuccess=()=>{
   const db=open.result;
   if(settled||!db.objectStoreNames.contains('referenceDataStore')){db.close();done(null);return;}
   try{
    const tx=db.transaction('referenceDataStore','readonly');
    const request=tx.objectStore('referenceDataStore').get(['PERIOD','id-ID']);
    tx.onerror=()=>{db.close();done(null);};
    request.onerror=()=>{db.close();done(null);};
    request.onsuccess=()=>{
     try{
      const x=request.result;
      const value=x&&x.ReferenceDataType==='PERIOD'&&x.language==='id-ID'?{
       ReferenceDataType:x.ReferenceDataType,language:x.language,Checksum:x.Checksum,
       ExpiryDate:x.ExpiryDate instanceof Date?x.ExpiryDate.toISOString():x.ExpiryDate,
       Details:Array.isArray(x.Details)?x.Details.map(d=>({Code:d.Code,CodeDescription:d.CodeDescription})):null
      }:null;
      db.close();done(value);
     }catch{db.close();done(null);}
    };
   }catch{db.close();done(null);}
  };
 });
}'''


def read_period_catalog(page):
    """Read only the source PERIOD cache; never fetch metadata or create a database."""
    from urllib.parse import urlsplit
    url = urlsplit(page.url)
    if (url.scheme != 'https' or url.netloc != 'coretax.intranet.pajak.go.id'
            or not url.path.startswith('/returnsheets/')):
        return None
    return page.evaluate(PERIOD_CATALOG_JS)


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
