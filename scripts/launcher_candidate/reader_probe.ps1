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
 [DllImport("user32.dll",EntryPoint="SystemParametersInfoW")] static extern bool GetSPI(uint action,uint param,ref int value,uint flags);
 [DllImport("user32.dll",EntryPoint="SystemParametersInfoW")] static extern bool SetSPI(uint action,uint param,IntPtr value,uint flags);
 public static bool ScreenReader() {int v=0;if(!GetSPI(0x0046,0,ref v,0))throw new Exception("SPI read failed");return v!=0;}
 public static void RestoreScreenReader(bool value) {if(!SetSPI(0x0047,value?1u:0u,IntPtr.Zero,0))throw new Exception("SPI restore failed");}
 [DllImport("oleacc.dll")] static extern int AccessibleObjectFromWindow(IntPtr h,uint obj,ref Guid iid,[MarshalAs(UnmanagedType.Interface)] out object acc);
 public static IAccessible Accessible(IntPtr h) {
  object a; Guid id=new Guid("618736e0-3c3d-11cf-810c-00aa00389b71");
  int hr=AccessibleObjectFromWindow(h,0xfffffffc,ref id,out a);
  if(hr!=0) Marshal.ThrowExceptionForHR(hr); return (IAccessible)a;
 }
}
'@
function Save($path,$data) {$data | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $path -Encoding UTF8}
function Phase($name) {Save (Join-Path $output 'probe-phase.json') @{phase=$name;reader=$Reader;activation_timing=$ActivationTiming;utc=[DateTime]::UtcNow.ToString('o')}}
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
  Phase 'msaa_password_value'
  $acc=[ReaderNative]::Accessible([IntPtr]$state.password_hwnd)
  $result.msaa_value=Observation $true (Exposed $acc.get_accValue(0))
  $selection=$acc.accSelection
  if ($selection -is [Accessibility.IAccessible]) {$result.msaa_selection=Observation $true (Exposed $selection.get_accValue(0))}
  elseif ($selection -is [int]) {$result.msaa_selection=Observation $true (Exposed $acc.get_accValue($selection))}
  $selection=$null
 } catch {$result.msaa_error=$_.Exception.GetType().Name}
 try {
  Phase 'uia_password_value'
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
  if ($hostProcess.HasExited -or [DateTime]::UtcNow -gt $deadline) {
   $safeError=Join-Path $hostDirectory 'host-error.json'
   if (Test-Path -LiteralPath $safeError) {Get-Content -LiteralPath $safeError -Raw | Write-Output}
   $phaseFile=Join-Path $hostDirectory 'host-phase.json'
   $phase=if (Test-Path -LiteralPath $phaseFile) {Get-Content -LiteralPath $phaseFile -Raw | ConvertFrom-Json} else {$null}
   $failure=@{schema=1;kind='candidate_startup_failure';mode=$mode;reader=$Reader;activation_timing=$ActivationTiming;
    reader_running=$readerAvailable;reader_pid=if ($readerProcess) {$readerProcess.Id} else {$null};
    reader_version=if ($readerExe -and (Test-Path -LiteralPath $readerExe)) {(Get-Item -LiteralPath $readerExe).VersionInfo.FileVersion} else {$null};
    host_pid=$hostProcess.Id;host_exited=$hostProcess.HasExited;phase=$phase;
    exit_code=if ($hostProcess.HasExited) {$hostProcess.ExitCode} else {$null};
    executable_sha256=(Get-FileHash -LiteralPath $Runtime).Hash.ToLowerInvariant();
    password='not_tested';names_roles_values_states='blocked';focus='blocked';selection='blocked';speech_navigation='blocked'}
   Save (Join-Path $output 'startup-failure.json') $failure
   $failure | ConvertTo-Json -Depth 5 | Write-Output
   throw 'Fixture readiness unavailable'
  }
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
  $config=Join-Path $output 'nvda-config'
  New-Item -ItemType Directory -Path $config | Out-Null
  # Official pinned configSpec.py / speechViewer.py: built-in viewer, no add-on/hook.
  "[general]`nlanguage = en`nshowWelcomeDialogAtStartup = False`nsaveConfigurationOnExit = False`nloggingLevel = OFF`n[speechViewer]`nshowSpeechViewerAtStartup = True`n[keyboard]`nspeakTypedCharacters = True`nspeakTypedWords = True" | Set-Content -LiteralPath (Join-Path $config 'nvda.ini') -Encoding UTF8
  $script:readerProcess=Start-Process -FilePath $readerExe -ArgumentList @('--minimal','--disable-addons','--log-level=100',('--config-path="'+$output+'\nvda-config"')) -WindowStyle Hidden -PassThru
 } else {$script:readerProcess=Start-Process -FilePath $readerExe -WindowStyle Hidden -PassThru}
 $script:readerLauncherId=$readerProcess.Id
 Start-Sleep -Seconds 4
 $matches=@(Get-CimInstance Win32_Process -Filter "Name='$Reader.exe'" | Where-Object {
  ($_.ProcessId -eq $readerLauncherId -or $_.ParentProcessId -eq $readerLauncherId) -and
  $_.ExecutablePath -and [IO.Path]::GetFullPath($_.ExecutablePath) -eq [IO.Path]::GetFullPath($readerExe)
 })
 if ($matches.Count -eq 1) {$script:readerProcess=Get-Process -Id $matches[0].ProcessId}
 $script:readerAvailable=-not $readerProcess.HasExited
}
function SpeechText {
 if ($Reader -ne 'NVDA' -or -not $readerAvailable) {return $null}
 $condition=New-Object Windows.Automation.PropertyCondition([Windows.Automation.AutomationElement]::ProcessIdProperty,$readerProcess.Id)
 $windows=[Windows.Automation.AutomationElement]::RootElement.FindAll([Windows.Automation.TreeScope]::Children,$condition)
 foreach($window in $windows) {
  if ($window.Current.Name -ne 'NVDA Speech Viewer') {continue}
  $controls=$window.FindAll([Windows.Automation.TreeScope]::Descendants,[Windows.Automation.Condition]::TrueCondition)
  foreach($control in $controls) {
   if ($control.Current.ProcessId -ne $readerProcess.Id) {continue}
   $pattern=$null
   if ($control.TryGetCurrentPattern([Windows.Automation.TextPattern]::Pattern,[ref]$pattern)) {return $pattern.DocumentRange.GetText(65536)}
   $pattern=$null
   if ($control.TryGetCurrentPattern([Windows.Automation.ValuePattern]::Pattern,[ref]$pattern)) {return $pattern.Current.Value}
  }
 }
 return $null
}
$readerExe=if ($Reader -eq 'NVDA') {$NvdaPath} else {Join-Path $env:WINDIR 'System32/Narrator.exe'}
if (Get-Process -Name $Reader -ErrorAction SilentlyContinue) {throw 'Preexisting reader; isolated runner required'}
$readerProcess=$null; $hostProcess=$null; $state=$null; $readerAvailable=$false
$readerLauncherId=$null
$originalScreenReader=[ReaderNative]::ScreenReader()
$speechObserved=$false; $speechExposed=$false; $speechFacility=$false
$mode=if ((Split-Path -Leaf $Runtime) -eq 'python.exe') {'source'} else {'frozen'}
$hostDirectory=Join-Path $output 'host'; $sentinel='QzvKjXwR947263'; $observations=@{}
$native=@{reader=$Reader;activation_timing=$ActivationTiming;mode=$mode;observations=@();speech_observed=$false}
try {
 Phase 'before_reader_and_fixture'
 if ($ActivationTiming -eq 'before_tk') {StartReader}
 $hostArgs=if ($mode -eq 'source') {@('-B',('"'+$PSScriptRoot+'\reader_host.py"'),'--scenario','settings','--directory',('"'+$hostDirectory+'"'))} else {@('--candidate-scenario','settings','--candidate-directory',('"'+$hostDirectory+'"'))}
 $hostProcess=Start-Process -FilePath $Runtime -ArgumentList $hostArgs -WindowStyle Hidden -PassThru
 Phase 'awaiting_fixture'
 $state=ReadState; $initialInitialized=$state.tk_initialized
 if ($ActivationTiming -eq 'late') {StartReader; Start-Sleep -Seconds 1; $state=ReadState}
 $native.initial_tk_initialized=$initialInitialized; $native.observed_tk_initialized=$state.tk_initialized
 $native.reader_available=$readerAvailable; $native.reader_launcher_pid=$readerLauncherId
 $native.reader_pid=if ($readerProcess) {$readerProcess.Id} else {$null}
 if ($readerAvailable) {
  [void][ReaderNative]::SetForegroundWindow([IntPtr]$state.hwnd)
  'focus_password' | Set-Content -LiteralPath (Join-Path $hostDirectory 'command.txt') -Encoding UTF8
  Start-Sleep -Milliseconds 500
  Owned ([ReaderNative]::GetForegroundWindow()) $state.pid
  $beforeSpeech=SpeechText
  $speechFacility=$null -ne $beforeSpeech
  Phase 'typing_synthetic_password'
  [Windows.Forms.SendKeys]::SendWait($sentinel); Start-Sleep -Milliseconds 500
  $afterSpeech=SpeechText
  if ($null -ne $afterSpeech -and $speechFacility -and $afterSpeech.StartsWith([string]$beforeSpeech)) {
   $spoken=$afterSpeech.Substring(([string]$beforeSpeech).Length)
   $speechObserved=$spoken.Length -gt 0
   $speechExposed=Exposed $spoken
   foreach($line in ($spoken -split "`n")) {
    if ($line.Trim() -cmatch '^(?:cap |capital )?([QzvKjXwR947263])$') {$speechExposed=$true}
   }
  }
  $beforeSpeech=$null; $afterSpeech=$null; $spoken=$null
  [Windows.Forms.SendKeys]::SendWait('^a'); Start-Sleep -Milliseconds 300
  $observations=EntryObservation $state; $native.observations+=@{phase='typed_selected';values=$observations.Clone()}
  $observations.typing_echo=Observation $speechObserved $speechExposed
  foreach($action in @('remap','reopen')) {
   $action | Set-Content -LiteralPath (Join-Path $hostDirectory 'command.txt') -Encoding UTF8
   Start-Sleep -Milliseconds 600; $state=ReadState; $phase=EntryObservation $state
   $native.observations+=@{phase=$action;values=$phase}
   $observations[$action]=Observation ($phase.msaa_value.observed -or $phase.uia_value.observed) ($phase.msaa_value.exposed -or $phase.uia_value.exposed)
  }
 }
 $native.pid=$state.pid; $native.speech_viewer_available=$speechFacility; $native.speech_observed=$speechObserved
 $native.speech_exposed=$speechExposed; $native.original_screenreader_flag=$originalScreenReader
 $nativePath=Join-Path $output 'native.json'; Save $nativePath $native
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
  outcomes=$outcomes;password_observations=@{};speech=@{observed=$speechObserved;method='reader_output';evidence=@('native');reason='Only actual owned NVDA Speech Viewer text changes qualify; Narrator has no configured speech observer'}}
 foreach($key in @('msaa_value','uia_value','msaa_selection','uia_selection','remap','reopen','typing_echo')) {if ($observations.ContainsKey($key)) {$report.password_observations[$key]=$observations[$key]}}
 Save (Join-Path $output 'report.json') $report
 Phase 'report_written'
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
 [ReaderNative]::RestoreScreenReader($originalScreenReader)
 if ([ReaderNative]::ScreenReader() -ne $originalScreenReader) {throw 'Screen reader setting restoration failed'}
 Save (Join-Path $output 'cleanup.json') @{host_exited=($null -eq $hostProcess -or $hostProcess.HasExited);reader_exited=($null -eq $readerProcess -or $readerProcess.HasExited)}
 $sentinel=$null
}
