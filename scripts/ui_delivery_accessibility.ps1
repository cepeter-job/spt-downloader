<#
Windows GitHub runner diagnostic. Run with Windows PowerShell 5.1 -STA:
  powershell -NoProfile -STA -File scripts/ui_delivery_accessibility.ps1 `
    -Python .venv/Scripts/python.exe -OutputDirectory "$env:RUNNER_TEMP/ui-accessibility" `
    -RequestLargeDisplay -IncludeHighContrast

Only the synthetic child process is inspected. No real application window,
credentials, live portal, driver installation or registry scaling edits.
Actual display mode and High Contrast are restored in finally. Output is
observation, not a screen-reader or cross-monitor accessibility PASS.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Python,
    [Parameter(Mandatory=$true)][string]$OutputDirectory,
    [switch]$RequestLargeDisplay,
    [switch]$IncludeHighContrast
)
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:OS -ne 'Windows_NT') {
    throw 'This native diagnostic is restricted to GitHub Windows runners.'
}
if ([Threading.Thread]::CurrentThread.ApartmentState -ne 'STA') {
    throw 'Run this script with Windows PowerShell -STA.'
}
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes, System.Drawing
Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Runtime.InteropServices;
public static class SptAccessNative {
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left,Top,Right,Bottom; }
  [StructLayout(LayoutKind.Sequential,CharSet=CharSet.Unicode)] public struct MONITORINFO {
    public int cbSize; public RECT Monitor,Work; public uint Flags;
    [MarshalAs(UnmanagedType.ByValTStr,SizeConst=32)] public string Device;
  }
  [StructLayout(LayoutKind.Sequential,CharSet=CharSet.Unicode)] public struct DEVMODE {
    [MarshalAs(UnmanagedType.ByValTStr,SizeConst=32)] public string DeviceName;
    public ushort SpecVersion,DriverVersion,Size,DriverExtra; public uint Fields;
    public int PositionX,PositionY; public uint Orientation,FixedOutput;
    public short Color,Duplex,YResolution,TTOption,Collate;
    [MarshalAs(UnmanagedType.ByValTStr,SizeConst=32)] public string FormName;
    public ushort LogPixels; public uint BitsPerPel,PelsWidth,PelsHeight,DisplayFlags,DisplayFrequency;
    public uint ICMMethod,ICMIntent,MediaType,DitherType,Reserved1,Reserved2,PanningWidth,PanningHeight;
  }
  [StructLayout(LayoutKind.Sequential)] public struct HC { public uint Size,Flags; public IntPtr Scheme; }
  public class Contrast { public uint Flags; public string Scheme; public bool Enabled { get { return (Flags&1)!=0; } } }
  public class MonitorRecord { public string Device; public RECT Bounds,Work; public bool Primary;
    public int ScalePercent,ScaleResult; }
  [StructLayout(LayoutKind.Sequential,CharSet=CharSet.Unicode)] public struct PROCESSENTRY {
    public uint Size,Usage,ProcessId; public UIntPtr DefaultHeap; public uint ModuleId,Threads,ParentId;
    public int BasePriority; public uint Flags;
    [MarshalAs(UnmanagedType.ByValTStr,SizeConst=260)] public string ExeFile;
  }
  [DllImport("kernel32.dll",SetLastError=true)] static extern IntPtr CreateToolhelp32Snapshot(uint flags,uint processId);
  [DllImport("kernel32.dll",CharSet=CharSet.Unicode)] static extern bool Process32FirstW(IntPtr snapshot,ref PROCESSENTRY entry);
  [DllImport("kernel32.dll",CharSet=CharSet.Unicode)] static extern bool Process32NextW(IntPtr snapshot,ref PROCESSENTRY entry);
  [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr handle);
  public static Dictionary<int,int> ProcessParents() {
    IntPtr snapshot=CreateToolhelp32Snapshot(2,0);
    if(snapshot==new IntPtr(-1)) throw new Win32Exception();
    try {
      var parents=new Dictionary<int,int>(); PROCESSENTRY entry=new PROCESSENTRY();
      entry.Size=(uint)Marshal.SizeOf(typeof(PROCESSENTRY));
      if(!Process32FirstW(snapshot,ref entry)) throw new Win32Exception();
      do { parents[(int)entry.ProcessId]=(int)entry.ParentId; } while(Process32NextW(snapshot,ref entry));
      return parents;
    } finally { CloseHandle(snapshot); }
  }
  public delegate bool MonitorCallback(IntPtr monitor,IntPtr dc,ref RECT rect,IntPtr data);
  [DllImport("user32.dll")] static extern bool EnumDisplayMonitors(IntPtr dc,IntPtr clip,MonitorCallback callback,IntPtr data);
  [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern bool GetMonitorInfoW(IntPtr monitor,ref MONITORINFO info);
  [DllImport("shcore.dll")] static extern int GetScaleFactorForMonitor(IntPtr monitor,out int scale);
  [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern bool EnumDisplaySettingsW(string device,int index,ref DEVMODE mode);
  [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern int ChangeDisplaySettingsExW(string device,ref DEVMODE mode,IntPtr hwnd,uint flags,IntPtr param);
  [DllImport("user32.dll",SetLastError=true)] static extern bool SystemParametersInfoW(uint action,uint param,ref HC data,uint flags);
  [DllImport("user32.dll")] public static extern IntPtr SetThreadDpiAwarenessContext(IntPtr context);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hwnd,out RECT rect);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hwnd);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hwnd,out uint processId);
  public static DEVMODE Mode(string device,int index) {
    DEVMODE mode=new DEVMODE(); mode.Size=(ushort)Marshal.SizeOf(typeof(DEVMODE));
    if(!EnumDisplaySettingsW(device,index,ref mode)) throw new Win32Exception(); return mode;
  }
  public static DEVMODE[] Modes(string device) {
    var modes=new List<DEVMODE>();
    for(int n=0;n<1000;n++) { DEVMODE mode=new DEVMODE(); mode.Size=(ushort)Marshal.SizeOf(typeof(DEVMODE));
      if(!EnumDisplaySettingsW(device,n,ref mode)) break; modes.Add(mode); }
    return modes.ToArray();
  }
  public static MonitorRecord[] Monitors() {
    var result=new List<MonitorRecord>();
    MonitorCallback callback=delegate(IntPtr monitor,IntPtr dc,ref RECT rect,IntPtr data) {
      MONITORINFO info=new MONITORINFO(); info.cbSize=Marshal.SizeOf(typeof(MONITORINFO));
      if(!GetMonitorInfoW(monitor,ref info)) throw new Win32Exception();
      int scale; int status=GetScaleFactorForMonitor(monitor,out scale);
      result.Add(new MonitorRecord { Device=info.Device,Bounds=info.Monitor,Work=info.Work,
        Primary=(info.Flags&1)!=0,ScalePercent=scale,ScaleResult=status }); return true; };
    if(!EnumDisplayMonitors(IntPtr.Zero,IntPtr.Zero,callback,IntPtr.Zero)) throw new Win32Exception();
    return result.ToArray();
  }
  public static Contrast GetContrast() {
    HC hc=new HC(); hc.Size=(uint)Marshal.SizeOf(typeof(HC));
    if(!SystemParametersInfoW(0x0042,hc.Size,ref hc,0)) throw new Win32Exception();
    // The Windows-owned pointer must not be freed. Microsoft's .NET implementation
    // explicitly corrects the contradictory Learn documentation on ownership:
    // https://source.dot.net/System.Private.Windows.Core/Windows/Win32/PInvokeCore.SystemParametersInfo.cs.html
    return new Contrast { Flags=hc.Flags,Scheme=Marshal.PtrToStringUni(hc.Scheme) };
  }
  public static void SetContrast(Contrast contrast) {
    HC hc=new HC(); hc.Size=(uint)Marshal.SizeOf(typeof(HC)); hc.Flags=contrast.Flags;
    hc.Scheme=Marshal.StringToHGlobalUni(contrast.Scheme);
    try { if(!SystemParametersInfoW(0x0043,hc.Size,ref hc,2)) throw new Win32Exception(); }
    finally { Marshal.FreeHGlobal(hc.Scheme); }
  }
}
'@

function Write-Evidence($Path, $Value) {
    $Value | ConvertTo-Json -Depth 25 | Set-Content -LiteralPath $Path -Encoding UTF8
}

function Write-RestorationCheckpoint {
    # Evidence persistence must never prevent the independent restoration steps.
    try { Write-Evidence (Join-Path $output 'report.json') $report }
    catch { [Console]::Error.WriteLine("Restoration checkpoint write failed: " + $_.Exception.Message) }
}

function Write-Phase([string]$Name) {
    $report.last_phase = $Name
    $report.last_phase_utc = [DateTime]::UtcNow.ToString('o')
    Write-Evidence (Join-Path $output 'report.json') $report
}

function Read-UiaNode($Element, $Depth, $Index, $Parent) {
    $current = $Element.Current
    $result = [ordered]@{index=$Index; parent=$Parent; depth=$Depth; name=$current.Name;
        automation_id=$current.AutomationId; class=$current.ClassName;
        role=$current.ControlType.ProgrammaticName; localized_role=$current.LocalizedControlType;
        focusable=$current.IsKeyboardFocusable; focused=$current.HasKeyboardFocus;
        enabled=$current.IsEnabled; offscreen=$current.IsOffscreen; password=$current.IsPassword;
        process_id=$current.ProcessId; hwnd=$current.NativeWindowHandle;
        bounds=@($current.BoundingRectangle.X,$current.BoundingRectangle.Y,
                 $current.BoundingRectangle.Width,$current.BoundingRectangle.Height);
        patterns=@($Element.GetSupportedPatterns() | ForEach-Object { $_.ProgrammaticName })}
    if ($current.IsPassword) { $result.name = '<password control>' }
    else {
        $pattern = $null
        if ($Element.TryGetCurrentPattern([Windows.Automation.ValuePattern]::Pattern,[ref]$pattern)) {
            $result.value = $pattern.Current.Value
            $result.readonly = $pattern.Current.IsReadOnly
        }
        $pattern = $null
        if ($Element.TryGetCurrentPattern([Windows.Automation.RangeValuePattern]::Pattern,[ref]$pattern)) {
            $result.range_value = $pattern.Current.Value
        }
    }
    return $result
}

function Read-UiaTree([IntPtr]$WindowHandle, [int]$OwnedProcessId) {
    $element = [Windows.Automation.AutomationElement]::FromHandle($WindowHandle)
    if ($element.Current.ProcessId -ne $OwnedProcessId) { throw 'UIA root is not the synthetic process.' }
    $nodes = [Collections.Generic.List[object]]::new()
    $pending = [Collections.Generic.Queue[object]]::new()
    $pending.Enqueue(@($element,0,-1))
    $walker = [Windows.Automation.TreeWalker]::RawViewWalker
    while ($pending.Count -gt 0 -and $nodes.Count -lt 1000) {
        $item = $pending.Dequeue()
        $index = $nodes.Count
        $nodes.Add((Read-UiaNode $item[0] $item[1] $index $item[2]))
        if ($item[1] -ge 30) { continue }
        $child = $walker.GetFirstChild($item[0])
        while ($null -ne $child) {
            if ($child.Current.ProcessId -eq $OwnedProcessId) { $pending.Enqueue(@($child,($item[1]+1),$index)) }
            $child = $walker.GetNextSibling($child)
        }
    }
    $focused = [Windows.Automation.AutomationElement]::FocusedElement
    $focus = $null
    if ($null -ne $focused -and $focused.Current.ProcessId -eq $OwnedProcessId) {
        $focus = Read-UiaNode $focused 0 -1 -1
    }
    $inputs = @($nodes | Where-Object { $_.role -eq 'ControlType.Edit' })
    $tables = @($nodes | Where-Object { $_.role -in @('ControlType.Tree','ControlType.Table','ControlType.DataGrid') })
    $namedInputs = @($inputs | Where-Object { -not [string]::IsNullOrWhiteSpace($_.name) })
    $valueInputs = @($inputs | Where-Object { $_.patterns -contains 'ValuePatternIdentifiers.Pattern' })
    $exposure = @{edit_roles=$inputs.Count; named_edit_roles=$namedInputs.Count;
        edit_roles_with_value_pattern=$valueInputs.Count; tree_table_grid_roles=$tables.Count;
        focused_role=if ($null -eq $focus) { $null } else { $focus.role };
        observation=if ($inputs.Count -eq 0 -and $tables.Count -eq 0) {
            'No expected input/table UIA roles exposed; window chrome or generic HWND nodes do not establish accessibility'
        } else { 'Some input/table roles exposed; inspect each required name, value and focus before acceptance' }}
    return @{nodes=@($nodes.ToArray()); truncated=($pending.Count -gt 0); focused=$focus; exposure=$exposure;
        source='Windows UI Automation raw tree; native provider results, no inferred widget labels'}
}

function Save-NativeFrame([IntPtr]$WindowHandle, [int]$OwnedProcessId, [string]$Path) {
    [uint32]$windowProcessId = 0
    [void][SptAccessNative]::GetWindowThreadProcessId($WindowHandle,[ref]$windowProcessId)
    if ($windowProcessId -ne $OwnedProcessId) { throw 'Screenshot window is not the synthetic process.' }
    $bounds = New-Object SptAccessNative+RECT
    if (-not [SptAccessNative]::GetWindowRect($WindowHandle,[ref]$bounds)) { throw 'GetWindowRect failed.' }
    $foreground = [SptAccessNative]::GetForegroundWindow() -eq $WindowHandle
    if (-not $foreground) { return @{captured=$false; reason='Synthetic window is not foreground'; bounds=$bounds} }
    $contained = $false
    foreach ($monitor in [SptAccessNative]::Monitors()) {
        if ($bounds.Left -ge $monitor.Bounds.Left -and $bounds.Top -ge $monitor.Bounds.Top -and
            $bounds.Right -le $monitor.Bounds.Right -and $bounds.Bottom -le $monitor.Bounds.Bottom) { $contained=$true }
    }
    if (-not $contained) { return @{captured=$false; reason='Window extends outside a physical monitor'; bounds=$bounds} }
    $bitmap = New-Object Drawing.Bitmap ($bounds.Right-$bounds.Left),($bounds.Bottom-$bounds.Top)
    $graphics = [Drawing.Graphics]::FromImage($bitmap)
    try {
        $graphics.CopyFromScreen($bounds.Left,$bounds.Top,0,0,$bitmap.Size,[Drawing.CopyPixelOperation]::SourceCopy)
        $bitmap.Save($Path,[Drawing.Imaging.ImageFormat]::Png)
    } finally { $graphics.Dispose(); $bitmap.Dispose() }
    return @{captured=$true; foreground=$foreground; bounds=$bounds;
        method='CopyFromScreen physical desktop pixels'; sha256=(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash}
}

function Wait-HostSnapshot($Process, [string]$Directory, [int]$Sequence) {
    $deadline = [DateTime]::UtcNow.AddSeconds(25)
    do {
        if ($Process.HasExited) { throw "Synthetic host exited with $($Process.ExitCode)." }
        $path = Join-Path $Directory 'ready.json'
        if (Test-Path -LiteralPath $path) {
            $snapshot = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
            if ($snapshot.sequence -eq $Sequence) { return $snapshot }
        }
        Start-Sleep -Milliseconds 100
    } while ([DateTime]::UtcNow -lt $deadline)
    throw 'Synthetic host did not reach the requested observation.'
}

function Confirm-OwnedHost($Launcher, [int]$HostProcessId, [IntPtr]$WindowHandle) {
    # uv virtualenv launchers can spawn the real interpreter before Python runs.
    # Trust neither the ready-file pid nor the UIA provider without OS ancestry.
    if ($Launcher.HasExited) { throw 'Launcher exited before host ownership verification.' }
    $parents = [SptAccessNative]::ProcessParents()
    $chain = [Collections.Generic.List[int]]::new()
    $currentId = $HostProcessId
    $childCreated = [DateTime]::MaxValue
    for ($depth=0; $depth -lt 32; $depth++) {
        if ($chain.Contains($currentId)) { throw 'Synthetic host ancestry contains a cycle.' }
        $chain.Add($currentId)
        $process = [Diagnostics.Process]::GetProcessById($currentId)
        try {
            $created = $process.StartTime.ToUniversalTime()
            if ($created -gt $childCreated -or $created -lt $Launcher.StartTime.ToUniversalTime()) {
                throw 'Synthetic host ancestry fails process creation-time validation.'
            }
            $childCreated = $created
        } finally { $process.Dispose() }
        if ($currentId -eq $Launcher.Id) { break }
        if (-not $parents.ContainsKey($currentId)) { throw 'Synthetic host is absent from native process snapshot.' }
        $currentId = $parents[$currentId]
    }
    if ($currentId -ne $Launcher.Id) { throw 'Reported host is not a descendant of the launched interpreter.' }
    [uint32]$windowProcessId = 0
    [void][SptAccessNative]::GetWindowThreadProcessId($WindowHandle,[ref]$windowProcessId)
    if ($windowProcessId -ne $HostProcessId) { throw 'Native window owner does not match the verified host.' }
    return @{launcher_pid=$Launcher.Id; actual_host_pid=$HostProcessId; ancestry=@($chain.ToArray());
        ancestry_source='Toolhelp32 process snapshot, creation ordering and GetWindowThreadProcessId'}
}

$output = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $output) { throw 'Use a new diagnostic output directory; prior evidence is never overwritten.' }
[void](New-Item -ItemType Directory -Path $output)
$pythonPath = (Resolve-Path -LiteralPath $Python).Path
$hostPath = Join-Path $PSScriptRoot 'ui_delivery_accessibility.py'
$oldContext = [IntPtr]::Zero
$beforeContrast = $null
$originalMode = $null
$device = $null
$modeChanged = $false
$contrastTouched = $false
$report = [ordered]@{schema=1; synthetic=$true; github_run_id=$env:GITHUB_RUN_ID;
    github_run_attempt=$env:GITHUB_RUN_ATTEMPT; github_sha=$env:GITHUB_SHA;
    git_head=(& git rev-parse HEAD); git_tree=(& git rev-parse 'HEAD^{tree}');
    requested_large_display=[bool]$RequestLargeDisplay;
    requested_high_contrast=[bool]$IncludeHighContrast;
    screen_reader_acceptance='NOT TESTED: Narrator and NVDA require operator speech/navigation checks';
    cross_monitor_acceptance='NOT TESTED: actual movement between distinct-DPI monitors is required';
    system_scale_changed=$false;
    high_contrast_observation='Fresh windows after native setting change; live-window theme switching is not exercised';
    cases=@(); failures=@(); restoration=@{}}
try {
    Write-Phase 'initial-report-before-native-queries'
    $oldContext = [SptAccessNative]::SetThreadDpiAwarenessContext([IntPtr](-4))
    if ($oldContext -eq [IntPtr]::Zero) { throw 'Physical-pixel observer DPI context could not be established.' }
    Write-Phase 'query-display-inventory'
    $report.monitors_before = @([SptAccessNative]::Monitors())
    $primary = @($report.monitors_before | Where-Object Primary)[0]
    $device = $primary.Device
    $originalMode = [SptAccessNative]::Mode($device,-1)
    $modes = @([SptAccessNative]::Modes($device))
    $report.display_modes = $modes
    $report.original_mode = $originalMode
    Write-Phase 'query-original-high-contrast'
    $beforeContrast = [SptAccessNative]::GetContrast()
    $report.high_contrast_before = $beforeContrast
    Write-Phase 'original-native-settings-recorded'
    if ($RequestLargeDisplay) {
        $report.display_attempts = @()
        $candidates = @($modes | Where-Object { $_.BitsPerPel -eq 32 -and
                $_.PelsWidth -ge $originalMode.PelsWidth -and $_.PelsHeight -ge $originalMode.PelsHeight } |
            Sort-Object @{Expression={$_.PelsWidth * $_.PelsHeight}} -Descending)
        foreach ($candidate in $candidates) {
            $testResult = [SptAccessNative]::ChangeDisplaySettingsExW($device,[ref]$candidate,[IntPtr]::Zero,2,[IntPtr]::Zero)
            $attempt = @{width=$candidate.PelsWidth; height=$candidate.PelsHeight; test_result=$testResult}
            if ($testResult -eq 0) {
                $applyResult = [SptAccessNative]::ChangeDisplaySettingsExW($device,[ref]$candidate,[IntPtr]::Zero,0,[IntPtr]::Zero)
                $attempt.apply_result = $applyResult
                if ($applyResult -eq 0) {
                    $modeChanged = $true
                    $report.selected_mode = $candidate
                }
            }
            $report.display_attempts += $attempt
            if ($modeChanged) { Start-Sleep -Seconds 2; break }
        }
        $report.large_display_request_succeeded = ($modeChanged -and
            $report.selected_mode.PelsWidth -ge 2560 -and $report.selected_mode.PelsHeight -ge 1800)
        $report.supported_fallback_applied = ($modeChanged -and -not $report.large_display_request_succeeded)
        $report.full_size_200_percent_display_prerequisite = if ($report.large_display_request_succeeded) {
            'Large resolution applied; actual 200% scale and attained client geometry must still be verified'
        } else { 'UNATTAINED: no applied display mode meets the sufficiently large 200% prerequisite' }
    }
    $report.monitors_observed = @([SptAccessNative]::Monitors())
    Write-Phase 'display-selection-complete'
    $modesToObserve = @('original')
    if ($IncludeHighContrast) { $modesToObserve += 'high-contrast' }
    foreach ($contrastMode in $modesToObserve) {
        if ($contrastMode -eq 'high-contrast') {
            $contrast = New-Object SptAccessNative+Contrast
            $contrast.Flags = $beforeContrast.Flags -bor 1
            $contrast.Scheme = $beforeContrast.Scheme
            $contrastTouched = $true
            Write-Phase 'enable-high-contrast'
            [SptAccessNative]::SetContrast($contrast)
            Start-Sleep -Seconds 2
            $report.high_contrast_after_enable = [SptAccessNative]::GetContrast()
            Write-Evidence (Join-Path $output 'report.json') $report
            if (-not $report.high_contrast_after_enable.Enabled) { throw 'High Contrast did not become active.' }
        }
        foreach ($scenario in @('main','selection','overwrite')) {
            foreach ($layout in @('normal','compact')) {
                $caseDirectory = Join-Path $output "$contrastMode-$scenario-$layout"
                [void](New-Item -ItemType Directory -Path $caseDirectory)
                $start = New-Object Diagnostics.ProcessStartInfo
                $start.FileName = $pythonPath
                $start.Arguments = '"' + $hostPath + '" --directory "' + $caseDirectory + '" --scenario ' + $scenario + ' --layout ' + $layout
                $start.UseShellExecute = $false
                $start.CreateNoWindow = $true
                $child = [Diagnostics.Process]::Start($start)
                $ownedHost = $null
                $case = @{scenario=$scenario; layout=$layout; contrast=$contrastMode; snapshots=@()}
                try {
                    for ($step=0; $step -lt 6; $step++) {
                        Write-Phase "$contrastMode/$scenario/$layout/$step-await-host"
                        if ($step -gt 0) { Write-Evidence (Join-Path $caseDirectory 'command.json') @{sequence=$step; action='tab'} }
                        $snapshot = Wait-HostSnapshot $child $caseDirectory $step
                        $ownership = Confirm-OwnedHost $child ([int]$snapshot.pid) ([IntPtr]$snapshot.hwnd)
                        if ($null -eq $ownedHost) { $ownedHost = [Diagnostics.Process]::GetProcessById([int]$snapshot.pid) }
                        elseif ($ownedHost.Id -ne [int]$snapshot.pid) { throw 'Synthetic host identity changed during observation.' }
                        $case.ownership = $ownership
                        [void][SptAccessNative]::SetForegroundWindow([IntPtr]$snapshot.hwnd)
                        Start-Sleep -Milliseconds 150
                        Write-Phase "$contrastMode/$scenario/$layout/$step-read-uia"
                        $uia = Read-UiaTree ([IntPtr]$snapshot.hwnd) ([int]$snapshot.pid)
                        Write-Phase "$contrastMode/$scenario/$layout/$step-read-high-contrast"
                        $snapshot | Add-Member -NotePropertyName high_contrast -NotePropertyValue ([SptAccessNative]::GetContrast())
                        $snapshot | Add-Member -NotePropertyName monitors -NotePropertyValue @([SptAccessNative]::Monitors())
                        Write-Evidence (Join-Path $caseDirectory "observation-$step.json") @{host=$snapshot; uia=$uia}
                        Write-Phase "$contrastMode/$scenario/$layout/$step-capture-frame"
                        $frame = Save-NativeFrame ([IntPtr]$snapshot.hwnd) ([int]$snapshot.pid) (Join-Path $caseDirectory "frame-$step.png")
                        $case.snapshots += @{sequence=$step; frame=$frame; uia_node_count=$uia.nodes.Count;
                            uia_exposure=$uia.exposure;
                            nominal_geometry_attained=$snapshot.nominal_geometry_attained}
                        Write-Phase "$contrastMode/$scenario/$layout/$step-observed"
                    }
                } catch {
                    $case.error = $_.Exception.Message
                    $report.failures += "$contrastMode/$scenario/$layout : $($_.Exception.Message)"
                } finally {
                    try {
                        if (-not $child.HasExited) {
                            try { Write-Evidence (Join-Path $caseDirectory 'command.json') @{sequence=1000; action='close'} }
                            catch { $report.failures += "Host close command failed: $($_.Exception.Message)" }
                            if (-not $child.WaitForExit(5000)) {
                                $case.forced_cleanup = $true
                                $report.failures += "$contrastMode/$scenario/$layout required forced synthetic-host cleanup"
                                if ($null -ne $ownedHost -and -not $ownedHost.HasExited) {
                                    $ownedHost.Kill()
                                    if (-not $ownedHost.WaitForExit(5000)) { throw 'Owned synthetic interpreter remained alive.' }
                                }
                                if (-not $child.HasExited) { $child.Kill() }
                                if (-not $child.WaitForExit(5000)) { throw 'Synthetic host remained alive after forced cleanup.' }
                            }
                        }
                        $case.exit_code = $child.ExitCode
                        if ($null -ne $ownedHost -and -not $ownedHost.HasExited) {
                            $ownedHost.Kill()
                            [void]$ownedHost.WaitForExit(5000)
                            $report.failures += 'Owned synthetic interpreter outlived its launcher and required cleanup.'
                        }
                        if ($child.ExitCode -ne 0) { $report.failures += "$contrastMode/$scenario/$layout host exit $($child.ExitCode)" }
                    } catch { $report.failures += "Synthetic host cleanup failed: $($_.Exception.Message)" }
                    finally {
                        if ($null -ne $ownedHost) { $ownedHost.Dispose() }
                        $child.Dispose()
                        $report.cases += $case
                        Write-Evidence (Join-Path $output 'report.json') $report
                    }
                }
            }
        }
    }
} catch {
    $report.failures += $_.Exception.Message
    [Console]::Error.WriteLine("Diagnostic failure: " + $_.Exception.Message)
} finally {
    $report.restoration['started'] = $true
    $report.restoration['high_contrast_requested'] = $contrastTouched
    $report.restoration['display_requested'] = $modeChanged
    Write-RestorationCheckpoint
    if ($contrastTouched -and $null -ne $beforeContrast) {
        try {
            $report.restoration['high_contrast_before_restore'] = [SptAccessNative]::GetContrast()
            Write-RestorationCheckpoint
            [SptAccessNative]::SetContrast($beforeContrast)
            $restored = [SptAccessNative]::GetContrast()
            $report.restoration['high_contrast'] = $restored
            Write-RestorationCheckpoint
            if ($restored.Flags -ne $beforeContrast.Flags -or $restored.Scheme -ne $beforeContrast.Scheme) {
                $report.failures += 'High Contrast restoration did not exactly match original flags/scheme.'
            }
        } catch {
            $report.failures += "High Contrast restoration failed: $($_.Exception.Message)"
            [Console]::Error.WriteLine("High Contrast restoration failed: " + $_.Exception.Message)
        }
    }
    if ($modeChanged) {
        try {
            $report.restoration.display_result = [SptAccessNative]::ChangeDisplaySettingsExW($device,[ref]$originalMode,[IntPtr]::Zero,0,[IntPtr]::Zero)
            $report.restoration.display = [SptAccessNative]::Mode($device,-1)
            if ($report.restoration.display_result -ne 0 -or
                $report.restoration.display.PelsWidth -ne $originalMode.PelsWidth -or
                $report.restoration.display.PelsHeight -ne $originalMode.PelsHeight -or
                $report.restoration.display.BitsPerPel -ne $originalMode.BitsPerPel -or
                $report.restoration.display.DisplayFrequency -ne $originalMode.DisplayFrequency -or
                $report.restoration.display.Orientation -ne $originalMode.Orientation) {
                $report.failures += 'Display restoration did not match the original resolution, depth, frequency or orientation.'
            }
        } catch {
            $report.failures += "Display restoration failed: $($_.Exception.Message)"
            [Console]::Error.WriteLine("Display restoration failed: " + $_.Exception.Message)
        }
    }
    if ($oldContext -ne [IntPtr]::Zero) { [void][SptAccessNative]::SetThreadDpiAwarenessContext($oldContext) }
    $report.restoration['finished'] = $true
    $report.diagnostic_completed = ($report.failures.Count -eq 0)
    $report.screenshot_capture_count = @($report.cases | ForEach-Object { $_.snapshots } |
        Where-Object { $_.frame.captured }).Count
    $report.observations_without_expected_uia_input_or_table_roles = @($report.cases |
        ForEach-Object { $_.snapshots } | Where-Object { $_.uia_exposure.edit_roles -eq 0 -and
            $_.uia_exposure.tree_table_grid_roles -eq 0 }).Count
    $report.accessibility_acceptance = 'UNRESOLVED: inspect native UIA evidence; operator screen-reader and cross-monitor checks remain required'
    Write-Evidence (Join-Path $output 'report.json') $report
}
if ($report.failures.Count -gt 0) { throw 'Accessibility diagnostic has failures; inspect report.json.' }
