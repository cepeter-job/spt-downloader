"""Use only an inspected origin-bound sign-in form; challenges stay manual."""
import time
from urllib.parse import urljoin,urlsplit
from .credentials import ALLOWED_ORIGINS,read_login

SEARCH_URL = 'https://coretax.intranet.pajak.go.id/returnsheets/id-ID/taxpayer-search'
CORETAX_ORIGIN = 'https://coretax.intranet.pajak.go.id'


class AuthBlocked(RuntimeError):
    pass


def _origin(url):
    parts=urlsplit(url)
    return f'{parts.scheme}://{parts.netloc}'


def authenticated(page):
    return (_origin(page.url)==CORETAX_ORIGIN and '/returnsheets/' in urlsplit(page.url).path
            and page.locator('#ObjectPermitNumber:visible').count()==1)


def try_saved_login(page,check_cancel):
    check_cancel()
    origin=_origin(page.url)
    if origin not in ALLOWED_ORIGINS:return False
    challenges='[autocomplete="one-time-code"],#captcha,.g-recaptcha,.h-captcha,iframe[src*="captcha" i],input[name*="captcha" i]'
    if page.locator(challenges).count():return False
    forms=page.locator('form')
    if forms.count()!=1:return False
    form=forms.first
    meta=form.evaluate('(e)=>({method:e.method,action:e.action})')
    if str(meta['method']).lower()!='post' or _origin(meta['action'])!=origin:return False
    identifiers=form.locator('input[autocomplete="username"],input[type="email"],input[name="username" i],input[id="username" i]')
    passwords=form.locator('input[type="password"]')
    buttons=form.locator('button[type="submit"],input[type="submit"]')
    if identifiers.count()!=1 or passwords.count()!=1 or buttons.count()!=1:return False
    identifier,password,button=identifiers.first,passwords.first,buttons.first
    if password.get_attribute('autocomplete')=='new-password':return False
    if not all(e.is_visible() and e.is_enabled() for e in (identifier,password,button)):return False
    target=button.get_attribute('formaction')
    if target and _origin(urljoin(page.url,target))!=origin:return False
    if (button.get_attribute('formmethod') or 'post').lower()!='post':return False
    label=(button.get_attribute('aria-label') or button.inner_text() or button.get_attribute('value') or '').strip().casefold()
    if label not in ('login','log in','sign in','masuk'):return False
    segments=[part.casefold() for part in urlsplit(meta['action']).path.split('/') if part]
    login_paths={'login','log-in','signin','sign-in','logon','session','sessions','authenticate','authentication'}
    if segments and not any(part in login_paths for part in segments):return False
    if not segments and not any(part.casefold() in login_paths for part in urlsplit(page.url).path.split('/')):return False
    if any(part in {'returnsheets','registration','submit','logout','signout'} for part in segments):return False
    editable=form.locator('input,textarea,select')
    fields=0
    for index in range(editable.count()):
        field=editable.nth(index)
        if field.is_visible() and field.is_enabled() and field.get_attribute('type') not in ('submit','button'):
            if field.get_attribute('readonly') is not None:return False
            fields+=1
    if fields!=2:return False
    try:
        login=read_login(origin)
        if login is None:return False
        check_cancel()
        identifier.fill(login.identifier,timeout=5000)
        password.fill(login.password,timeout=5000)
        button.click(timeout=5000)
        return True
    except Exception:
        # Playwright call logs may include fill arguments; never forward this exception.
        return False


def _wait_ready(page,deadline,check_cancel):
    while time.monotonic()<deadline:
        check_cancel()
        if authenticated(page):return True
        page.wait_for_timeout(200)
    return False


def authenticate_owned(playwright,profile,browser,headless,emit,check_cancel,manual_timeout=300):
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
        if authenticated(page):return context,page
        if _origin(page.url) not in ALLOWED_ORIGINS:
            raise AuthBlocked('Login beralih ke origin yang tidak disetujui. Hubungi administrator.')
        attempted=try_saved_login(page,check_cancel)
        if attempted and _wait_ready(page,time.monotonic()+10,check_cancel):return context,page
        if headless:
            context.close(); context=None
            context,page=launch(False)
        emit('login_required','Selesaikan login/CAPTCHA/MFA langsung di browser aplikasi; batas waktu 5 menit.')
        if not _wait_ready(page,time.monotonic()+manual_timeout,check_cancel):
            raise AuthBlocked('Login manual belum selesai; tekan Mulai untuk mencoba lagi.')
        if headless:
            context.close(); context=None
            context,page=launch(True)
            if authenticated(page):return context,page
            context.close(); context=None
            context,page=launch(False)
            emit('login_required','Sesi headless tidak diterima. Lanjutkan login di browser terlihat.')
            if not _wait_ready(page,time.monotonic()+manual_timeout,check_cancel):
                raise AuthBlocked('Sesi browser terlihat belum siap.')
        return context,page
    except BaseException:
        if context is not None:context.close()
        raise
