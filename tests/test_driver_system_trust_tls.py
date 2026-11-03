"""Real Windows-runner TLS regression, using one owned synthetic certificate."""
import json
import os
import queue
import re
import subprocess
import sys
import threading
import uuid

import pytest


SETUP = r'''
$ErrorActionPreference = 'Stop'
$rsa = [System.Security.Cryptography.RSA]::Create(2048)
$cert = $null
$public = $null
$store = $null
try {
  $request = [System.Security.Cryptography.X509Certificates.CertificateRequest]::new($env:SPT_TEST_CERT_SUBJECT,$rsa,[System.Security.Cryptography.HashAlgorithmName]::SHA256,[System.Security.Cryptography.RSASignaturePadding]::Pkcs1)
  $request.CertificateExtensions.Add([System.Security.Cryptography.X509Certificates.X509BasicConstraintsExtension]::new($true,$false,0,$true))
  $san = [System.Security.Cryptography.X509Certificates.SubjectAlternativeNameBuilder]::new()
  $san.AddDnsName('localhost')
  $request.CertificateExtensions.Add($san.Build())
  $usage = [System.Security.Cryptography.X509Certificates.X509KeyUsageFlags]::DigitalSignature -bor [System.Security.Cryptography.X509Certificates.X509KeyUsageFlags]::KeyEncipherment -bor [System.Security.Cryptography.X509Certificates.X509KeyUsageFlags]::KeyCertSign
  $request.CertificateExtensions.Add([System.Security.Cryptography.X509Certificates.X509KeyUsageExtension]::new($usage,$true))
  $cert = $request.CreateSelfSigned([DateTimeOffset]::UtcNow.AddMinutes(-5),[DateTimeOffset]::UtcNow.AddHours(1))
  # Persist public ownership before adding trust; no key is stored in My.
  [IO.File]::WriteAllBytes($env:SPT_TEST_CER,$cert.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Cert))
  [IO.File]::WriteAllBytes($env:SPT_TEST_PFX,$cert.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Pfx,$env:SPT_TEST_PFX_PASSWORD))
  $public = [System.Security.Cryptography.X509Certificates.X509Certificate2]::new($cert.RawData)
  $store = [System.Security.Cryptography.X509Certificates.X509Store]::new('Root',[System.Security.Cryptography.X509Certificates.StoreLocation]::LocalMachine)
  $store.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite)
  $store.Add($public)
  @{thumbprint=$cert.Thumbprint} | ConvertTo-Json -Compress
} finally {
  if ($store) { $store.Dispose() }
  if ($public) { $public.Dispose() }
  if ($cert) { $cert.Dispose() }
  $rsa.Dispose()
}
'''

CLEANUP = r'''
$ErrorActionPreference = 'Stop'
if (-not [IO.File]::Exists($env:SPT_TEST_CER)) { exit 0 }
$owned = [System.Security.Cryptography.X509Certificates.X509Certificate2]::new([IO.File]::ReadAllBytes($env:SPT_TEST_CER))
$store = $null
try {
  if ($env:SPT_TEST_CERT_SUBJECT -cnotmatch '^CN=SPTDownloaderSynthetic-[a-f0-9]{32}$' -or $owned.Subject -ne $env:SPT_TEST_CERT_SUBJECT -or $owned.Thumbprint -cnotmatch '^[A-F0-9]{40}$') { throw 'Invalid synthetic ownership' }
  $store = [System.Security.Cryptography.X509Certificates.X509Store]::new('Root',[System.Security.Cryptography.X509Certificates.StoreLocation]::LocalMachine)
  $store.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite)
  $matches = $store.Certificates.Find([System.Security.Cryptography.X509Certificates.X509FindType]::FindByThumbprint,$owned.Thumbprint,$false)
  foreach ($entry in $matches) {
    if ([Convert]::ToBase64String($entry.RawData) -cne [Convert]::ToBase64String($owned.RawData)) { throw 'Refuse unrelated certificate' }
    $store.Remove($entry)
  }
  if ($store.Certificates.Find([System.Security.Cryptography.X509Certificates.X509FindType]::FindByThumbprint,$owned.Thumbprint,$false).Count -ne 0) { throw 'Synthetic root cleanup failed' }
} finally {
  if ($store) { $store.Dispose() }
  $owned.Dispose()
}
'''

SERVER = r'''
const fs=require('node:fs'),https=require('node:https');
const server=https.createServer({pfx:fs.readFileSync(process.env.SPT_TEST_PFX),passphrase:process.env.SPT_TEST_PFX_PASSWORD},(req,res)=>{res.setHeader('Content-Type','application/json');res.end('{"synthetic":true}');});
server.listen({host:'::',port:0,ipv6Only:false},()=>process.stdout.write(JSON.stringify({port:server.address().port})+'\n'));
'''

CLIENT = r'''
import json, os
from playwright.sync_api import sync_playwright, Error
manager = sync_playwright()
if os.environ['SPT_TEST_NATIVE'] == '1':
    from coretax_transport import system_ca_manager
    manager = system_ca_manager(manager)
try:
    with manager as p:
        client = p.request.new_context(ignore_https_errors=False)
        try:
            response = client.get(os.environ['SPT_TEST_URL'], timeout=5000, max_redirects=0, max_retries=0)
            result = {'accepted':response.status==200 and response.body()==b'{"synthetic":true}'}
        finally:
            client.dispose()
except Error:
    result = {'accepted':False}
print(json.dumps(result))
'''


@pytest.mark.skipif(sys.platform != 'win32', reason='Native Windows CA store integration')
def test_owned_driver_uses_windows_trust_but_still_rejects_wrong_hostname(tmp_path):
    assert os.environ.get('GITHUB_ACTIONS') == 'true', 'Synthetic root requires a disposable hosted runner'
    from playwright._impl._driver import compute_driver_executable
    node, _ = compute_driver_executable()
    environment = dict(os.environ)
    environment.pop('NODE_USE_SYSTEM_CA', None)
    environment.pop('NODE_EXTRA_CA_CERTS', None)
    environment.pop('NODE_OPTIONS', None)
    environment.pop('NODE_TLS_REJECT_UNAUTHORIZED', None)
    environment.update(SPT_TEST_PFX_PASSWORD=uuid.uuid4().hex,
        SPT_TEST_PFX=str(tmp_path/'synthetic.pfx'), SPT_TEST_CER=str(tmp_path/'synthetic.cer'),
        SPT_TEST_CERT_SUBJECT='CN=SPTDownloaderSynthetic-'+uuid.uuid4().hex)
    server = None
    try:
        setup = subprocess.run(['pwsh','-NoProfile','-NonInteractive','-Command',SETUP],
            env=environment, capture_output=True, text=True, timeout=30, check=False)
        assert setup.returncode == 0, 'Synthetic certificate setup failed: ' + setup.stderr
        assert re.fullmatch('[A-F0-9]{40}', json.loads(setup.stdout)['thumbprint'])
        script = tmp_path/'server.cjs'
        script.write_text(SERVER,encoding='utf-8')
        server = subprocess.Popen([node,str(script)],env=environment,stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL,text=True)
        # A daemon reader cannot hold cleanup hostage if readiness times out.
        ready = queue.Queue()
        reader = threading.Thread(target=lambda: ready.put(server.stdout.readline()), daemon=True)
        reader.start()
        port = json.loads(ready.get(timeout=10))['port']
        def request(native, host):
            env = dict(environment,SPT_TEST_NATIVE=str(native),SPT_TEST_URL=f'https://{host}:{port}/fixed')
            result = subprocess.run([sys.executable,'-c',CLIENT],env=env,capture_output=True,
                                    text=True,timeout=20,check=True)
            return json.loads(result.stdout)['accepted']
        assert request(0,'localhost') is False, 'Default bundled trust unexpectedly accepted synthetic root'
        assert request(1,'localhost') is True, 'Native Windows trust did not reach the owned driver'
        assert request(1,'127.0.0.1') is False, 'Hostname verification was bypassed'
    finally:
        try:
            if server is not None:
                server.terminate()
                server.wait(timeout=5)
                server.stdout.close()
        finally:
            subprocess.run(['pwsh','-NoProfile','-NonInteractive','-Command',CLEANUP],
                env=environment,capture_output=True,text=True,timeout=15,check=True)
            (tmp_path/'synthetic.pfx').unlink(missing_ok=True)
            (tmp_path/'synthetic.cer').unlink(missing_ok=True)
