<# GitHub-only actual-reader observation. Never serialize password values or infer speech. #>
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$Runtime,
 [Parameter(Mandatory=$true)][ValidateSet('NVDA','Narrator')][string]$Reader,
 [Parameter(Mandatory=$true)][string]$OutputDirectory,
 [ValidateSet('before_tk','late')][string]$ActivationTiming='before_tk', [string]$NvdaPath)
$ErrorActionPreference='Stop'
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:OS -ne 'Windows_NT') {throw 'GitHub Windows runner required'}
if (Test-Path -LiteralPath $OutputDirectory) {throw 'New output directory required'}
$output=[IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Path $output | Out-Null
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes, Accessibility, System.Windows.Forms
Add-Type -ReferencedAssemblies Accessibility -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using Accessibility;
public static class ReaderNative {
 [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
 [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h,out uint p);
 [DllImport("oleacc.dll")] static extern int AccessibleObjectFromWindow(IntPtr h,uint obj,ref Guid iid,[MarshalAs(UnmanagedType.Interface)] out object acc);
 public static IAccessible Accessible(IntPtr h) {
  object a; Guid id=new Guid("618736e0-3c3d-11cf-810c-00aa00389b71");
  int hr=AccessibleObjectFromWindow(h,0xfffffffc,ref id,out a);
  if(hr!=0) Marshal.ThrowExceptionForHR(hr); return (IAccessible)a;
 }
}
'@
function Save($path,$data) {$data | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $path -Encoding UTF8}
function Owned([IntPtr]$handle,[int]$processId) {
 [uint32]$actual=0; [void][ReaderNative]::GetWindowThreadProcessId($handle,[ref]$actual)
 if ($actual -ne $processId) {throw 'Unowned native window'}
}
function Exposed($value) {
 if ($null -eq $value) {return $false}; $text=[string]$value
 if ($text.Length -eq 1) {return $sentinel.Contains($text)}
 for ($i=0;$i -le $sentinel.Length-3;$i++) {if ($text.Contains($sentinel.Substring($i,3))) {return $true}}
 return $false
}
function Observation($observed,$exposed) {return @{observed=$observed;exposed=$exposed;evidence=@('native')}}
function EntryObservation($state) {
 Owned ([IntPtr]$state.password_hwnd) $state.pid
 $result=@{msaa_value=(Observation $false $false);uia_value=(Observation $false $false);msaa_selection=(Observation $false $false);uia_selection=(Observation $false $false)}
 try {
  $acc=[ReaderNative]::Accessible([IntPtr]$state.password_hwnd)
  $result.msaa_value=Observation $true (Exposed $acc.get_accValue(0))
  $selection=$acc.accSelection
  if ($selection -is [Accessibility.IAccessible]) {$result.msaa_selection=Observation $true (Exposed $selection.get_accValue(0))}
  elseif ($selection -is [int]) {$result.msaa_selection=Observation $true (Exposed $acc.get_accValue($selection))}
  $selection=$null
 } catch {$result.msaa_error=$_.Exception.GetType().Name}
 try {
  $element=[Windows.Automation.AutomationElement]::FromHandle([IntPtr]$state.password_hwnd)
  if ($element.Current.ProcessId -ne $state.pid) {throw 'Unowned UIA element'}
  $pattern=$null
  if ($element.TryGetCurrentPattern([Windows.Automation.ValuePattern]::Pattern,[ref]$pattern)) {$result.uia_value=Observation $true (Exposed $pattern.Current.Value)}
  $pattern=$null
  if ($element.TryGetCurrentPattern([Windows.Automation.TextPattern]::Pattern,[ref]$pattern)) {
   $leaked=$false
   foreach($range in $pattern.GetSelection()) {$leaked=$leaked -or (Exposed $range.GetText(256))}
   $result.uia_selection=Observation $true $leaked
  }
 } catch {$result.uia_error=$_.Exception.GetType().Name}
 return $result
}
function ReadState {
 $ready=Join-Path $hostDirectory 'ready.json'; $deadline=[DateTime]::UtcNow.AddSeconds(30)
 while (-not (Test-Path -LiteralPath $ready)) {
  if ($hostProcess.HasExited -or [DateTime]::UtcNow -gt $deadline) {throw 'Fixture readiness unavailable'}
  Start-Sleep -Milliseconds 100
 }
 $state=Get-Content -LiteralPath $ready -Raw | ConvertFrom-Json
 $nativeProcess=Get-CimInstance Win32_Process -Filter "ProcessId=$($state.pid)"
 if ($state.pid -ne $hostProcess.Id -and $nativeProcess.ParentProcessId -ne $hostProcess.Id) {throw 'Fixture ancestry unverified'}
 Owned ([IntPtr]$state.hwnd) $state.pid
 return $state
}
function StartReader {
 if (-not $readerExe -or -not (Test-Path -LiteralPath $readerExe)) {return}
 if ($Reader -eq 'NVDA') {
  $script:readerProcess=Start-Process -FilePath $readerExe -ArgumentList @('--minimal','--disable-addons','--log-level=100',('--config-path="'+$output+'\nvda-config"')) -WindowStyle Hidden -PassThru
 } else {$script:readerProcess=Start-Process -FilePath $readerExe -WindowStyle Hidden -PassThru}
 Start-Sleep -Seconds 4
 $script:readerAvailable=-not $readerProcess.HasExited
}
$readerExe=if ($Reader -eq 'NVDA') {$NvdaPath} else {Join-Path $env:WINDIR 'System32/Narrator.exe'}
if (Get-Process -Name $Reader -ErrorAction SilentlyContinue) {throw 'Preexisting reader; isolated runner required'}
$readerProcess=$null; $hostProcess=$null; $state=$null; $readerAvailable=$false
$mode=if ((Split-Path -Leaf $Runtime) -eq 'python.exe') {'source'} else {'frozen'}
$hostDirectory=Join-Path $output 'host'; $sentinel='QzvKjXwR947263'; $observations=@{}
$native=@{reader=$Reader;activation_timing=$ActivationTiming;mode=$mode;observations=@();speech_observed=$false}
try {
 if ($ActivationTiming -eq 'before_tk') {StartReader}
 $hostArgs=if ($mode -eq 'source') {@('-B',('"'+$PSScriptRoot+'\reader_host.py"'),'--scenario','settings','--directory',('"'+$hostDirectory+'"'))} else {@('--candidate-scenario','settings','--candidate-directory',('"'+$hostDirectory+'"'))}
 $hostProcess=Start-Process -FilePath $Runtime -ArgumentList $hostArgs -WindowStyle Hidden -PassThru
 $state=ReadState; $initialInitialized=$state.tk_initialized
 if ($ActivationTiming -eq 'late') {StartReader; Start-Sleep -Seconds 1; $state=ReadState}
 $native.initial_tk_initialized=$initialInitialized; $native.observed_tk_initialized=$state.tk_initialized
 $native.reader_available=$readerAvailable; $native.reader_pid=if ($readerProcess) {$readerProcess.Id} else {$null}
 if ($readerAvailable) {
  [void][ReaderNative]::SetForegroundWindow([IntPtr]$state.hwnd)
  'focus_password' | Set-Content -LiteralPath (Join-Path $hostDirectory 'command.txt') -Encoding UTF8
  Start-Sleep -Milliseconds 500
  Owned ([ReaderNative]::GetForegroundWindow()) $state.pid
  [Windows.Forms.SendKeys]::SendWait($sentinel); Start-Sleep -Milliseconds 500
  [Windows.Forms.SendKeys]::SendWait('^a'); Start-Sleep -Milliseconds 300
  $observations=EntryObservation $state; $native.observations+=@{phase='typed_selected';values=$observations.Clone()}
  foreach($action in @('remap','reopen')) {
   $action | Set-Content -LiteralPath (Join-Path $hostDirectory 'command.txt') -Encoding UTF8
   Start-Sleep -Milliseconds 600; $state=ReadState; $phase=EntryObservation $state
   $native.observations+=@{phase=$action;values=$phase}
   $observations[$action]=Observation ($phase.msaa_value.observed -or $phase.uia_value.observed) ($phase.msaa_value.exposed -or $phase.uia_value.exposed)
  }
 }
 $native.pid=$state.pid; $nativePath=Join-Path $output 'native.json'; Save $nativePath $native
 $reason=if (-not $readerAvailable) {'Actual reader could not run on disposable runner'} elseif (-not $state.tk_initialized) {'Actual reader running but Tk initialization unobserved'} else {'Speech, typing echo, focus notifications and reader inspection require actual output observation'}
 $outcomes=@{}
 foreach($gate in @('password','names_roles_values_states','focus','selection','speech_navigation')) {$outcomes[$gate]=@{status='blocked';reason=$reason;evidence=@('native')}}
 $leak=@($observations.Values | Where-Object {$_.exposed -eq $true}).Count -gt 0
 if ($leak -and $readerAvailable -and $state.tk_initialized) {
  $outcomes.password=@{status='failed';evidence=@('native')}
  foreach($key in @('names_roles_values_states','focus','selection','speech_navigation')) {$outcomes[$key].reason='Password gate failed; adoption stopped'}
 }
 $version=if ($readerAvailable) {(Get-Item -LiteralPath $readerExe).VersionInfo.FileVersion} else {$null}
 $report=@{schema=1;reader=@{name=$Reader;version=$version;available=$readerAvailable;pid=$native.reader_pid};mode=$mode;scenario='settings';activation_timing=$ActivationTiming;
  candidate=$state.candidate;ownership=@{pid=$state.pid;windows_verified=$true;isolated=$true};
  activation=@{observed=($readerAvailable -and $state.tk_initialized);reader_running=$readerAvailable;tk_initialized=[bool]$state.tk_initialized;evidence=@('native')};
  evidence=@{native=@{path='native.json';sha256=(Get-FileHash $nativePath).Hash.ToLowerInvariant();mode=$mode;reader=$Reader;scenario='settings';activation_timing=$ActivationTiming;pid=$state.pid}};
  providers=@{MSAA=@{observed=[bool]$observations.msaa_value.observed;evidence=@('native')};UIA=@{observed=[bool]$observations.uia_value.observed;evidence=@('native')}};
  outcomes=$outcomes;password_observations=@{};speech=@{observed=$false;reason='No actual speech output observer available'}}
 foreach($key in @('msaa_value','uia_value','msaa_selection','uia_selection','remap','reopen')) {if ($observations.ContainsKey($key)) {$report.password_observations[$key]=$observations[$key]}}
 Save (Join-Path $output 'report.json') $report
 foreach($scenario in @('main','selection','overwrite','progress','result')) {
  Save (Join-Path $output ($scenario+'-blocked.json')) @{scenario=$scenario;reader=$Reader;mode=$mode;activation_timing=$ActivationTiming;status='blocked';reason='Password prerequisite not passed';settings_report='report.json'}
 }
} finally {
 if ($hostProcess) {
  if (Test-Path -LiteralPath $hostDirectory) {'close' | Set-Content -LiteralPath (Join-Path $hostDirectory 'command.txt') -Encoding UTF8}
  if (-not $hostProcess.WaitForExit(15000)) {
   if ($state) {$owned=Get-Process -Id $state.pid -ErrorAction SilentlyContinue; if ($owned) {$owned.Kill(); [void]$owned.WaitForExit(5000)}}
   if (-not $hostProcess.HasExited) {$hostProcess.Kill(); [void]$hostProcess.WaitForExit(5000)}
  }
 }
 if ($readerProcess -and -not $readerProcess.HasExited) {$readerProcess.Kill(); [void]$readerProcess.WaitForExit(5000)}
 Save (Join-Path $output 'cleanup.json') @{host_exited=($null -eq $hostProcess -or $hostProcess.HasExited);reader_exited=($null -eq $readerProcess -or $readerProcess.HasExited)}
 $sentinel=$null
}
