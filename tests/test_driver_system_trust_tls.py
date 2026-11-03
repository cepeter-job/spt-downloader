"""Real Windows-runner TLS regression, using one owned synthetic certificate."""
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import threading
import uuid

import pytest


SETUP = r'''
$ErrorActionPreference = 'Stop'
$pfxPassword = ConvertTo-SecureString $env:SPT_TEST_PFX_PASSWORD -AsPlainText -Force
$cert = New-SelfSignedCertificate -Subject $env:SPT_TEST_CERT_SUBJECT -DnsName 'localhost' -CertStoreLocation 'Cert:\CurrentUser\My' -KeyAlgorithm RSA -KeyLength 2048 -HashAlgorithm SHA256 -KeyExportPolicy Exportable -NotAfter (Get-Date).AddHours(1) -KeyUsage DigitalSignature,KeyEncipherment,CertSign -TextExtension @('2.5.29.19={text}ca=true')
try {
  Export-PfxCertificate -Cert $cert -FilePath $env:SPT_TEST_PFX -Password $pfxPassword -CryptoAlgorithmOption AES256_SHA256 | Out-Null
  Export-Certificate -Cert $cert -FilePath $env:SPT_TEST_CER | Out-Null
  Import-Certificate -FilePath $env:SPT_TEST_CER -CertStoreLocation 'Cert:\LocalMachine\Root' | Out-Null
  @{thumbprint=$cert.Thumbprint} | ConvertTo-Json -Compress
} catch {
  foreach ($path in @("Cert:\LocalMachine\Root\$($cert.Thumbprint)","Cert:\CurrentUser\My\$($cert.Thumbprint)")) {
    if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force }
  }
  throw
}
'''

CLEANUP = r'''
$ErrorActionPreference = 'Stop'
$thumb = $env:SPT_TEST_CERT_THUMB
if ($thumb -cnotmatch '^[A-F0-9]{40}$') { throw 'Invalid synthetic thumbprint' }
foreach ($path in @("Cert:\LocalMachine\Root\$thumb","Cert:\CurrentUser\My\$thumb")) {
  if (Test-Path -LiteralPath $path) {
    $owned = Get-Item -LiteralPath $path
    if ($owned.Subject -ne $env:SPT_TEST_CERT_SUBJECT) { throw 'Refuse unrelated certificate' }
    Remove-Item -LiteralPath $path -Force
  }
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
    # Windows PowerShell must not autoload PowerShell 7's incompatible modules.
    ps_environment = {k:v for k,v in environment.items() if k.upper() != 'PSMODULEPATH'}
    ps_environment['PSMODULEPATH'] = str(Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/Modules')
    setup = subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',SETUP],
        env=ps_environment, capture_output=True, text=True, timeout=30, check=False)
    assert setup.returncode == 0, 'Synthetic certificate setup failed: ' + setup.stderr
    thumb = json.loads(setup.stdout)['thumbprint']
    assert re.fullmatch('[A-F0-9]{40}', thumb)
    environment['SPT_TEST_CERT_THUMB'] = thumb
    ps_environment['SPT_TEST_CERT_THUMB'] = thumb
    server = None
    try:
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
            subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',CLEANUP],
                env=ps_environment,capture_output=True,text=True,timeout=15,check=True)
