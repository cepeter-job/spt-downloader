"""Use only an inspected origin-bound sign-in form; challenges stay manual."""
from spt_desktop import diagnostics
import time
import tempfile
from pathlib import Path
from urllib.parse import urlsplit
from .credentials import ALLOWED_ORIGINS,LOGIN_ORIGIN,read_login

SEARCH_URL = 'https://coretax.intranet.pajak.go.id/returnsheets/id-ID/taxpayer-search'
CORETAX_ORIGIN = 'https://coretax.intranet.pajak.go.id'
HOME_PATH = '/home/id-ID/'


class AuthBlocked(RuntimeError):
    pass


def _origin(url):
    parts=urlsplit(url)
    return f'{parts.scheme}://{parts.netloc}'


def authenticated(page):
    return (_origin(page.url)==CORETAX_ORIGIN and '/returnsheets/' in urlsplit(page.url).path
            and page.locator('#ObjectPermitNumber:visible').count()==1)


def _has_challenge(page):
    challenges='[autocomplete="one-time-code"],#captcha,.g-recaptcha,.h-captcha,iframe[src*="captcha" i],input[name*="captcha" i]'
    return bool(page.locator(challenges).count())


def _submission(button):
    # Read browser-resolved properties: a base URL and empty method override can
    # change the actual destination/method even when raw attributes look safe.
    return button.evaluate('''(button)=>({
        action:button.hasAttribute('formaction')?button.formAction:button.form.action,
        method:button.hasAttribute('formmethod')?button.formMethod:button.form.method
    })''')


def _login_fields(page):
    origin=_origin(page.url)
    if origin not in ALLOWED_ORIGINS:return None
    if _has_challenge(page):return None
    forms=page.locator('form')
    if forms.count()!=1:return None
    form=forms.first
    meta=form.evaluate('(e)=>({method:e.method,action:e.action})')
    if str(meta['method']).lower()!='post' or _origin(meta['action'])!=origin:return None
    identifiers=form.locator('input[autocomplete="username"],input[type="email"],input[name="username" i],input[id="username" i]')
    passwords=form.locator('input[type="password"]')
    buttons=form.locator('button[type="submit"],input[type="submit"]')
    if identifiers.count()!=1 or passwords.count()!=1 or buttons.count()!=1:return None
    identifier,password,button=identifiers.first,passwords.first,buttons.first
    if password.get_attribute('autocomplete')=='new-password':return None
    if not all(e.is_visible() and e.is_enabled() for e in (identifier,password,button)):return None
    submission=_submission(button)
    if _origin(submission['action'])!=origin or submission['method'].lower()!='post':return None
    visible_label=button.locator('.indicator-label:visible')
    caption=visible_label.first.inner_text() if visible_label.count()==1 else button.inner_text()
    label=(button.get_attribute('aria-label') or caption or button.get_attribute('value') or '').strip().casefold()
    if label not in ('login','log in','sign in','masuk'):return None
    action=submission['action']
    segments=[part.casefold() for part in urlsplit(action).path.split('/') if part]
    login_paths={'login','log-in','signin','sign-in','logon','session','sessions','authenticate','authentication'}
    if segments and not any(part in login_paths for part in segments):return None
    if not segments and not any(part.casefold() in login_paths for part in urlsplit(page.url).path.split('/')):return None
    if any(part in {'returnsheets','registration','submit','logout','signout'} for part in segments):return None
    editable=form.locator('input,textarea,select')
    fields=0
    for index in range(editable.count()):
        field=editable.nth(index)
        if field.is_visible() and field.is_enabled() and field.get_attribute('type') not in ('submit','button'):
            if field.get_attribute('readonly') is not None:return None
            fields+=1
    if fields!=2:return None
    return origin,identifier,password,button


def _bind_login_fields(page,fields):
    origin=fields[0]
    controls=tuple(locator.element_handle() for locator in fields[1:])
    form=controls[-1].evaluate_handle('(button)=>button.form')
    submission=_submission(controls[-1])
    def current():
        if _origin(page.url)!=origin:return False
        inspected=_login_fields(page)
        if inspected is None or inspected[0]!=origin:return False
        latest=tuple(locator.element_handle() for locator in inspected[1:])
        if _submission(latest[-1])!=submission:return False
        if not form.evaluate('(form,button)=>form.isConnected && form===button.form',latest[-1]):return False
        return all(original.evaluate('(element,current)=>element.isConnected && element===current',fresh)
                   for original,fresh in zip(controls,latest))
    return (origin,*controls),current


def _wait_login_fields(page,expected_origin,check_cancel,timeout=5):
    # Only an empty async shell is pending. An inspected unsafe form/challenge
    # stays manual; polling never broadens recognition or authorizes a retry.
    deadline=time.monotonic()+timeout
    while True:
        check_cancel()
        if expected_origin not in ALLOWED_ORIGINS or _origin(page.url)!=expected_origin:
            return None
        if _has_challenge(page):return None
        fields=_login_fields(page)
        if fields is not None:
            return fields if fields[0]==expected_origin else None
        if page.locator('form').count():
            # A form may render between the two read-only observations.
            check_cancel()
            fields=_login_fields(page)
            return fields if fields is not None and fields[0]==expected_origin else None
        remaining=deadline-time.monotonic()
        if remaining<=0:return None
        page.wait_for_timeout(min(200,max(1,int(remaining*1000))))


def try_saved_login(page,check_cancel,*,account=None):
    check_cancel()
    if account=='':return False
    fields=_login_fields(page)
    if fields is None:
        _,fields=_wait_login_ready(page,LOGIN_ORIGIN,check_cancel,5,lambda reason:None)
    if fields is None or fields[0]!=LOGIN_ORIGIN:return False
    try:
        fields,current=_bind_login_fields(page,fields)
        origin,identifier,password,button=fields
        if not current():return False
        check_cancel()
        login=read_login(origin)
        if login is None or (account is not None and login.identifier!=account):return False
        if not current():return False
        check_cancel()
        identifier.fill(login.identifier,timeout=5000)
        if not current():return False
        check_cancel()
        password.fill(login.password,timeout=5000)
        if not current():return False
        check_cancel()
        button.click(timeout=5000)
        return True
    except Exception:
        # Playwright call logs may include fill arguments; never forward this exception.
        return False


def _at_home(page):
    return _origin(page.url)==CORETAX_ORIGIN and urlsplit(page.url).path==HOME_PATH


def _open_search_from_home(page,check_cancel,timeout=30000,emit=None):
    if not _at_home(page):return False
    check_cancel()
    if emit:emit('progress','Beranda Coretax terdeteksi; membuka Pencarian WP untuk verifikasi sesi…')
    page.goto(SEARCH_URL,wait_until='domcontentloaded',timeout=timeout)
    return True


def _wait_ready(page,deadline,check_cancel,emit=None):
    opened_search=False
    while time.monotonic()<deadline:
        check_cancel()
        if authenticated(page):return True
        if not opened_search and _at_home(page):
            remaining=max(1,int((deadline-time.monotonic())*1000))
            opened_search=_open_search_from_home(page,check_cancel,timeout=min(30000,remaining),emit=emit)
            continue
        page.wait_for_timeout(200)
    return False


@diagnostics.traced('authentication')
def authenticate_owned(playwright,profile,browser,headless,emit,check_cancel,manual_timeout=300,*,account=None):
    if browser not in ('msedge','chrome'):raise AuthBlocked('Pilih Microsoft Edge atau Chrome.')
    context=None
    def launch(hidden):
        check_cancel()
        try:
            owned=playwright.chromium.launch_persistent_context(str(profile),channel=browser,
                headless=hidden,viewport={'width':1600,'height':1000})
        except Exception:
            raise AuthBlocked('Browser tidak dapat dibuka. Pastikan Edge/Chrome terpasang dan profil tidak dipakai.') from None
        try:
            page=owned.pages[0] if owned.pages else owned.new_page()
            page.goto(SEARCH_URL,wait_until='domcontentloaded',timeout=60000)
            return owned,page
        except BaseException:
            owned.close()
            raise
    try:
        context,page=launch(headless)
        if account and (authenticated(page) or _at_home(page)):
            raise AuthBlocked('Sesi SSO belum dapat dikaitkan dengan akun tersimpan. Gunakan mode login manual.')
        if authenticated(page):return context,page
        if _at_home(page) and _wait_ready(page,time.monotonic()+10,check_cancel,emit=emit):return context,page
        if _origin(page.url) not in ALLOWED_ORIGINS:
            raise AuthBlocked('Login beralih ke origin yang tidak disetujui. Hubungi administrator.')
        attempted=try_saved_login(page,check_cancel,account=account) if account is not None else try_saved_login(page,check_cancel)
        if attempted and _wait_ready(page,time.monotonic()+20,check_cancel,emit=emit):return context,page
        if account and not attempted and (authenticated(page) or _at_home(page)):
            raise AuthBlocked('Sesi SSO belum dapat dikaitkan dengan akun tersimpan. Gunakan mode login manual.')
        if headless:
            context.close(); context=None
            context,page=launch(False)
        emit('login_required','Selesaikan login/CAPTCHA/MFA di browser aplikasi. Maksimal 5 menit; otomatis lanjut setelah Pencarian WP terverifikasi.')
        if not _wait_ready(page,time.monotonic()+manual_timeout,check_cancel,emit=emit):
            raise AuthBlocked('Login manual belum selesai; tekan Mulai untuk mencoba lagi.')
        if headless:
            context.close(); context=None
            context,page=launch(True)
            if _wait_ready(page,time.monotonic()+10,check_cancel,emit=emit):return context,page
            context.close(); context=None
            context,page=launch(False)
            emit('login_required','Sesi headless tidak diterima. Lanjutkan login di browser terlihat.')
            if not _wait_ready(page,time.monotonic()+manual_timeout,check_cancel,emit=emit):
                raise AuthBlocked('Sesi browser terlihat belum siap.')
        return context,page
    except BaseException:
        if context is not None:context.close()
        raise



def _wait_login_ready(page, expected_origin, check_cancel, timeout, observe):
    """Wait for an observable login/session, not a momentarily stable entry URL."""
    deadline = time.monotonic() + timeout
    while True:
        check_cancel()
        initial_origin = _origin(page.url)
        if initial_origin not in ALLOWED_ORIGINS:
            return 'origin_blocked', None
        if authenticated(page):
            return 'existing_session', None
        if _at_home(page):
            return 'existing_home', None
        if _has_challenge(page):
            return 'challenge', None
        fields = _login_fields(page)
        if fields is None and page.locator('form').count():
            # A form can appear between observations; unsafe forms are not retried.
            check_cancel()
            fields = _login_fields(page)
            if fields is None:
                return 'unsafe_form', None
        if fields is not None:
            if fields[0] != initial_origin or _origin(page.url) != initial_origin:
                return 'form_changed', None
            observe('login_form_ready')
            return 'login_form_ready', fields
        current = _origin(page.url)
        if current not in ALLOWED_ORIGINS:
            return 'origin_blocked', None
        path = urlsplit(page.url).path
        entry_shell = current == CORETAX_ORIGIN and path in (
            '/returnsheets/id-ID/', '/returnsheets/id-ID/taxpayer-search')
        satu_shell = current == ALLOWED_ORIGINS[0] and path == '/login'
        if not (entry_shell or satu_shell or current == expected_origin):
            return 'unsafe_form', None
        observe('waiting_redirect' if entry_shell else 'waiting_form')
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return 'readiness_timeout', None
        page.wait_for_timeout(min(200, max(1, int(remaining * 1000))))


@diagnostics.traced('authentication')
def check_saved_credentials(playwright,root,origin,account,browser,headless,check_cancel,timeout=20):
    """Verify one saved login, never an old session or a manually replaced password."""
    from coretax_browser import CaptureCancelled
    if origin not in ALLOWED_ORIGINS or browser not in ('msedge','chrome'):
        raise ValueError('Origin/browser pengecekan tidak disetujui.')
    if not isinstance(account,str) or not account.strip() or '\0' in account:
        raise ValueError('Akun tersimpan harus dipilih dari Pengaturan.')
    check_cancel()
    page = None
    submitted = False
    observed_states = set()
    blocked_categories = set()
    blocked_requests = 0
    coretax_blocked_after_submit = False
    categories = {CORETAX_ORIGIN: 'coretax', ALLOWED_ORIGINS[0]: 'satu'}
    def diagnostic(event, reason, **fields):
        # Only category constants cross into logging, never URLs or form content.
        try:
            current = categories.get(_origin(page.url), 'other') if page is not None else 'other'
        except Exception:
            current = 'other'
        if event == 'auth.state':
            key = reason, current
            if key in observed_states:
                return
            observed_states.add(key)
        diagnostics.record(event, operation='login_check', phase='authentication',
            expected_origin=categories[origin], observed_origin=current, reason=reason, **fields)
    def finish(status, message, reason):
        diagnostic('auth.result', reason, status=status, submitted=submitted, blocked_requests=blocked_requests)
        return status, message
    cache=Path(root)/'cache'
    cache.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='login-check-',dir=cache) as fresh:
        context=None
        try:
            context=playwright.chromium.launch_persistent_context(fresh,channel=browser,headless=headless)
            def guard(route):
                nonlocal blocked_requests, coretax_blocked_after_submit
                request=route.request
                target=_origin(request.url)
                if target not in ALLOWED_ORIGINS or (request.method not in ('GET','HEAD') and target!=origin):
                    blocked_requests+=1
                    method=request.method if request.method in ('GET','HEAD','POST') else 'OTHER'
                    resource=getattr(request,'resource_type','other')
                    resource=resource if resource in ('document','xhr','fetch') else 'other'
                    category=categories.get(target,'other')
                    reason='origin_not_allowed' if target not in ALLOWED_ORIGINS else 'cross_origin_write'
                    # Track every occurrence independently of log deduplication:
                    # the same category can occur before and after submission.
                    if submitted and target == CORETAX_ORIGIN and reason == 'cross_origin_write':
                        coretax_blocked_after_submit = True
                    key=(category,method,resource,reason)
                    if key not in blocked_categories:
                        blocked_categories.add(key)
                        diagnostic('auth.request_blocked',reason,target_origin=category,method=method,resource_type=resource)
                    route.abort()
                else:route.fallback()
            context.route('**/*',guard)
            page=context.pages[0] if context.pages else context.new_page()
            page.goto(SEARCH_URL,wait_until='domcontentloaded',timeout=30000)
            state, fields = _wait_login_ready(page, origin, check_cancel, min(5, timeout),
                lambda reason: diagnostic('auth.state', reason))
            if state == 'existing_session':
                return finish('LOGIN_UNVERIFIED','Sesi SSO tersedia, tetapi password tersimpan belum diuji.',state)
            if state == 'existing_home':
                _wait_ready(page,time.monotonic()+timeout,check_cancel)
                return finish('LOGIN_UNVERIFIED','Beranda Coretax terbuka, tetapi password tersimpan belum diuji.',state)
            if state == 'origin_blocked':
                return finish('LOGIN_BLOCKED','Login beralih ke origin yang tidak disetujui; hubungi administrator.',state)
            if state == 'challenge':
                return finish('LOGIN_MANUAL','CAPTCHA/MFA terdeteksi; selesaikan melalui login manual saat Mulai.',state)
            if state == 'readiness_timeout':
                return finish('LOGIN_UNVERIFIED','Halaman login belum siap dalam batas waktu; password belum diuji. Periksa koneksi intranet.',state)
            if fields is None:
                return finish('LOGIN_MANUAL','Form login belum dikenali dengan aman; gunakan login manual saat Mulai.',state)
            if fields[0] != origin:
                return finish('LOGIN_BLOCKED',f'Origin login berbeda. Pilih {fields[0]} di Pengaturan lalu Simpan.','origin_mismatch')
            fields,current_form=_bind_login_fields(page,fields)
            changed_form=('LOGIN_MANUAL','Form login berubah; gunakan login manual saat Mulai.')
            if not current_form():return finish(*changed_form, 'form_changed')
            check_cancel()
            login=read_login(origin)
            if login is None:
                return finish('LOGIN_BLOCKED','Kredensial Satu belum disimpan; isi akun/password di Pengaturan lalu Simpan. Entri Coretax lama tidak dipindahkan otomatis.','credential_missing')
            if login.identifier!=account:
                return finish('LOGIN_BLOCKED','Akun tersimpan berbeda dari Pengaturan; masukkan akun/password lalu Simpan.','account_mismatch')
            _,identifier,password,button=fields
            if not current_form():return finish(*changed_form, 'form_changed')
            check_cancel()
            identifier.fill(login.identifier,timeout=5000)
            if not current_form():return finish(*changed_form, 'form_changed')
            check_cancel()
            password.fill(login.password,timeout=5000)
            if not current_form():return finish(*changed_form, 'form_changed')
            check_cancel()
            submitted = True
            button.click(timeout=5000)
            del login
            deadline=time.monotonic()+timeout
            opened_search=False
            while time.monotonic()<deadline:
                check_cancel()
                if authenticated(page):
                    return finish('LOGIN_OK','Login berhasil; kredensial tersimpan terverifikasi.','verified')
                if not opened_search and _at_home(page):
                    remaining=max(1,int((deadline-time.monotonic())*1000))
                    opened_search=_open_search_from_home(page,check_cancel,timeout=min(30000,remaining))
                    continue
                if _has_challenge(page):
                    return finish('LOGIN_MANUAL','CAPTCHA/MFA diperlukan setelah login; belum dapat menyatakan kredensial valid.','challenge')
                if _origin(page.url) not in ALLOWED_ORIGINS:
                    return finish('LOGIN_BLOCKED','Login beralih ke origin yang tidak disetujui; hubungi administrator.','origin_blocked')
                time.sleep(0.1)
            check_cancel()
            if coretax_blocked_after_submit:
                return finish('LOGIN_UNVERIFIED',
                    'Login belum terverifikasi. Pemeriksa memblokir permintaan lanjutan ke Coretax '
                    'setelah form login dikirim. Ini bukan bukti password salah. '
                    'Gunakan Mulai untuk alur login unduhan biasa.', 'cross_origin_write')
            return finish('LOGIN_UNVERIFIED','Login belum terverifikasi dalam batas waktu; periksa akun, password, atau koneksi. Tidak ada percobaan ulang otomatis.','verification_timeout')
        except CaptureCancelled:
            diagnostic('auth.result', 'cancelled', status='CANCELLED', submitted=submitted)
            raise
        except Exception:
            # Fill/navigation exceptions may contain secrets or token-bearing URLs.
            check_cancel()
            return finish('LOGIN_ERROR','Pengecekan gagal; periksa koneksi intranet, browser, dan akses Windows Credential Manager.','check_error')
        finally:
            if context is not None:context.close()
