[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Sources,
    [Parameter(Mandatory)][string]$OutputDirectory
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_OS -ne 'Windows') { throw 'Native execution is GitHub Windows runner only' }
$output = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $output) { throw 'OutputDirectory must be new; existing artifacts are never replaced' }
$manifest = Get-Content -LiteralPath $Sources -Raw | ConvertFrom-Json
if ($manifest.schema -ne 1) { throw 'Unsupported source manifest' }
$work = Join-Path $env:RUNNER_TEMP ('launcher-build-' + [guid]::NewGuid().ToString('N'))
$stage = Join-Path $work 'runtime'
$evidence = "$output-evidence"
New-Item -ItemType Directory -Path $stage, $evidence | Out-Null
@{ schema = 1; head = $env:GITHUB_SHA; run_id = $env:GITHUB_RUN_ID; phase = 'verified-source-acquisition' } | ConvertTo-Json | Set-Content "$evidence/phase.json"
# Only synthetic native build diagnostics are emitted; no workspace/profile capture.
$roots = @{}
foreach ($source in $manifest.sources) {
    if ($source.revision -notmatch '^[a-f0-9]{40}$' -or $source.sha256 -notmatch '^[a-f0-9]{64}$' -or $source.repo -notmatch '^(python/(cpython|cpython-source-deps|cpython-bin-deps)|tcltk/(tcl|tk))$' -or $source.name -notmatch '^[a-z0-9-]+$') { throw 'Invalid immutable source identity' }
    $archive = Join-Path $work ($source.name + '.zip')
    Invoke-WebRequest -Uri "https://codeload.github.com/$($source.repo)/zip/$($source.revision)" -OutFile $archive
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $source.sha256) { throw "Source archive hash mismatch: $($source.name)" }
    $extracted = Join-Path $work $source.name
    New-Item -ItemType Directory -Path $extracted | Out-Null
    & tar -xf $archive -C $extracted
    if ($LASTEXITCODE -ne 0) { throw "Archive extraction failed: $($source.name)" }
    $directories = @(Get-ChildItem -LiteralPath $extracted -Directory)
    if ($directories.Count -ne 1) { throw 'Unexpected archive root' }
    $roots[$source.name] = $directories[0].FullName
}
# sqlite3.vcxproj derives its resource version from the directory suffix.
# Preserve the immutable archive bytes while satisfying that upstream convention.
$sqliteBuildRoot = Join-Path $work 'sqlite-3.50.4.0'
Copy-Item -LiteralPath $roots.sqlite -Destination $sqliteBuildRoot -Recurse
$roots.sqlite = $sqliteBuildRoot
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
$vs = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -format json | ConvertFrom-Json | Select-Object -First 1
if (-not $vs) { throw 'Missing Visual C++ compiler' }
$vcTools = Get-ChildItem "$($vs.installationPath)/VC/Tools/MSVC" -Directory | Sort-Object { [version]$_.Name } -Descending | Select-Object -First 1
$sdk = Get-ChildItem "${env:ProgramFiles(x86)}/Windows Kits/10/Include" -Directory | Where-Object Name -Match '^10\.' | Sort-Object { [version]$_.Name } -Descending | Select-Object -First 1
$toolset = if ([version]$vcTools.Name -ge [version]'14.50') { 'v145' } else { 'v143' }
$devcmd = Join-Path $vs.installationPath 'Common7/Tools/VsDevCmd.bat'
# Import only the developer command environment into this isolated runner process.
$setupCommand = Join-Path $work 'compiler-environment.cmd'
@("@call `"$devcmd`" -no_logo -arch=x64 -host_arch=x64 -vcvars_ver=$($vcTools.Name) -winsdk=$($sdk.Name) >nul", '@if errorlevel 1 exit /b 1', '@set') | Set-Content -LiteralPath $setupCommand -Encoding ascii
$environment = & $env:ComSpec /d /c $setupCommand
if ($LASTEXITCODE -ne 0) { throw 'Developer command environment failed' }
foreach ($line in $environment) { if ($line -match '^([^=]+)=(.*)$') { [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2], 'Process') } }
$msbuild = Join-Path $vs.installationPath 'MSBuild/Current/Bin/MSBuild.exe'
$compiler = Join-Path $vcTools.FullName 'bin/Hostx64/x64/cl.exe'
$bootstrap = (Get-Command python.exe).Source
$nativeEvidence = [ordered]@{
    schema = 1; head = $env:GITHUB_SHA; run_id = $env:GITHUB_RUN_ID; attempt = $env:GITHUB_RUN_ATTEMPT
    tree = (& git rev-parse 'HEAD^{tree}'); runner_image = $env:ImageVersion
    visual_studio = $vs.installationVersion; vc_tools = $vcTools.Name; toolset = $toolset
    windows_sdk = $sdk.Name; compiler_file_version = (Get-Item -LiteralPath $compiler).VersionInfo.FileVersion
    compiler_sha256 = (Get-FileHash -LiteralPath $compiler).Hash.ToLowerInvariant()
    msbuild_file_version = (Get-Item -LiteralPath $msbuild).VersionInfo.FileVersion
    bootstrap_path = $bootstrap; bootstrap_sha256 = (Get-FileHash -LiteralPath $bootstrap).Hash.ToLowerInvariant()
    sources = $manifest.sources; configuration = 'Release/x64/GIL/BuildForRelease'; patches = @()
}
# Upstream nmake generates manifest.uuid with git when it is absent. ZIP inputs
# have no .git; reproduce that generated input from the verified source revision.
$generatedInputs = @{}
foreach ($kind in @('tcl', 'tk')) {
    $source = $manifest.sources | Where-Object name -EQ $kind
    $template = [IO.File]::ReadAllText("$($roots[$kind])/win/gitmanifest.in")
    $uuidFile = "$($roots[$kind])/manifest.uuid"
    [IO.File]::WriteAllText($uuidFile, $template + $source.revision + "`n", [Text.UTF8Encoding]::new($false))
    $generatedInputs["$kind/manifest.uuid"] = (Get-FileHash -LiteralPath $uuidFile).Hash.ToLowerInvariant()
}
$nativeEvidence.generated_inputs = $generatedInputs
$nativeEvidence | ConvertTo-Json -Depth 12 | Set-Content "$evidence/build.json" -Encoding utf8
Get-Content "$evidence/build.json"
function Invoke-Native([string]$Name, [string]$Executable, [string[]]$Arguments) {
    & $Executable @Arguments *> "$evidence/$Name.log"
    $nativeExit = $LASTEXITCODE
    Get-Content "$evidence/$Name.log" -Tail 35
    if ($nativeExit -ne 0) { throw "$Name failed with exit code $nativeExit; see synthetic build log" }
}
$tclInstall = Join-Path $work 'tcltk-install'
Push-Location "$($roots.tcl)/win"
try {
    Invoke-Native 'tcl-release' 'nmake.exe' @('/nologo', '/f', 'makefile.vc', 'release', 'MACHINE=AMD64', 'OPTS=noembed', "INSTALLDIR=$tclInstall")
    Invoke-Native 'tcl-install' 'nmake.exe' @('/nologo', '/f', 'makefile.vc', 'install', 'MACHINE=AMD64', 'OPTS=noembed', "INSTALLDIR=$tclInstall")
} finally { Pop-Location }
Push-Location "$($roots.tk)/win"
try {
    Invoke-Native 'tk-release' 'nmake.exe' @('/nologo', '/f', 'makefile.vc', 'release', 'MACHINE=AMD64', 'OPTS=noembed', "TCLDIR=$($roots.tcl)", "INSTALLDIR=$tclInstall")
    Invoke-Native 'tk-install' 'nmake.exe' @('/nologo', '/f', 'makefile.vc', 'install', 'MACHINE=AMD64', 'OPTS=noembed', "TCLDIR=$($roots.tcl)", "INSTALLDIR=$tclInstall")
} finally { Pop-Location }
$pythonBuild = Join-Path $roots.cpython 'PCbuild'
Copy-Item -LiteralPath "$($roots.tcl)/license.terms" -Destination "$tclInstall/tcllicense.terms"
Copy-Item -LiteralPath "$($roots.tk)/license.terms" -Destination "$tclInstall/tklicense.terms"
$properties = @('/nologo', '/m:2', '/v:minimal', '/p:Configuration=Release', '/p:Platform=x64', "/p:PlatformToolset=$toolset", "/p:VCToolsVersion=$($vcTools.Name)", "/p:WindowsTargetPlatformVersion=$($sdk.Name)", '/p:BuildForRelease=true', '/p:IncludeExternals=true', '/p:IncludeTests=false', '/p:IncludeUwp=false', '/p:IncludeCTypes=true', '/p:IncludeSSL=true', '/p:IncludeTkinter=true', '/p:UseDisableGil=false', "/p:PythonForBuild=$bootstrap", '/p:TclVersion=9.1.0.0', '/p:TkVersion=9.1.0.0', "/p:tcltkDir=$tclInstall\", "/p:zlibNgDir=$($roots['zlib-ng'])\", "/p:libffiDir=$($roots.libffi)\", "/p:bz2Dir=$($roots.bzip2)\", "/p:mpdecimalDir=$($roots.mpdecimal)\", "/p:sqlite3Dir=$($roots.sqlite)\", "/p:lzmaDir=$($roots.xz)\", "/p:zstdDir=$($roots.zstd)\", "/p:opensslDir=$($roots.openssl)\", "/p:opensslOutDir=$($roots['openssl-bin'])\amd64\")
Invoke-Native 'cpython-build' $msbuild (@("$pythonBuild/pcbuild.proj") + $properties)
$built = Join-Path $pythonBuild 'amd64'
New-Item -ItemType Directory -Path "$stage/DLLs", "$stage/Lib", "$stage/tcl", "$stage/licenses" | Out-Null
foreach ($name in @('python.exe', 'pythonw.exe', 'python314.dll', 'python3.dll', 'vcruntime140.dll', 'vcruntime140_1.dll')) { Copy-Item -LiteralPath "$built/$name" -Destination $stage }
Copy-Item -LiteralPath "$built/LICENSE.txt" -Destination "$stage/LICENSE.txt"
# Literal runtime payload, following PC/layout (no shell-extension/test binaries).
$extensions = @('_asyncio', '_decimal', '_elementtree', '_multiprocessing', '_overlapped', 'pyexpat', '_queue', '_remote_debugging', 'select', 'unicodedata', 'winsound', '_uuid', '_wmi', '_zoneinfo', '_ctypes', '_bz2', '_lzma', '_sqlite3', '_zstd', '_ssl', '_hashlib', '_tkinter', '_socket')
foreach ($name in $extensions) { Copy-Item -LiteralPath "$built/$name.pyd" -Destination "$stage/DLLs" }
foreach ($name in @('libffi-8.dll', 'libcrypto-3.dll', 'libssl-3.dll', 'sqlite3.dll', 'tcl91.dll', 'tcl9tk91.dll', 'zlib1.dll', 'libtommath.dll')) { Copy-Item -LiteralPath "$built/$name" -Destination "$stage/DLLs" }
& robocopy "$($roots.cpython)/Lib" "$stage/Lib" /E /XD test tests __pycache__ /XF '*.pyc' /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { throw 'Cannot copy standard library' }
# CPython 3.13+ keeps these original names in its standalone venv layout.
foreach ($name in @('venvlauncher.exe', 'venvwlauncher.exe')) { Copy-Item -LiteralPath "$built/$name" -Destination "$stage/Lib/venv/scripts/nt" }
& robocopy "$tclInstall/lib" "$stage/tcl" /E /XF '*.lib' '*.a' '*.sh' '*.pdb' /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { throw 'Cannot copy script libraries' }
foreach ($source in $manifest.sources) { if ($source.license) { Copy-Item -LiteralPath (Join-Path $roots[$source.name] $source.license) -Destination "$stage/licenses/$($source.name.Replace('cpython','python')).txt" } }
Copy-Item -LiteralPath "$($roots.tcl)/libtommath/LICENSE" -Destination "$stage/licenses/tommath.txt"
Copy-Item -LiteralPath "$($roots.tcl)/compat/zlib/LICENSE" -Destination "$stage/licenses/tcl-zlib.txt"
Copy-Item -LiteralPath "$($roots.cpython)/PC/crtlicense.txt" -Destination "$stage/licenses/msvc.txt"
foreach ($name in @('PYTHONHOME', 'PYTHONPATH', 'TCL_LIBRARY', 'TK_LIBRARY', 'TCLLIBPATH')) { Remove-Item "Env:$name" -ErrorAction SilentlyContinue }
$env:PYTHONDONTWRITEBYTECODE = '1'
$probe = Join-Path $PSScriptRoot 'probe.py'
$inventory = Join-Path $PSScriptRoot 'inventory.py'
Push-Location $env:RUNNER_TEMP
try {
    Invoke-Native 'runtime-probe' "$stage/python.exe" @('-I', '-B', $probe, '--output', "$evidence/probe.json")
    Invoke-Native 'runtime-inventory' "$stage/python.exe" @('-I', '-B', $inventory, '--root', $stage, '--probe', "$evidence/probe.json")
} finally { Pop-Location }
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $output) | Out-Null
Move-Item -LiteralPath $stage -Destination $output
# Reprobe the final location, outside the source/build checkout.
Push-Location $env:RUNNER_TEMP
try {
    Invoke-Native 'final-probe' "$output/python.exe" @('-I', '-B', $probe, '--output', "$evidence/final-probe.json")
    Invoke-Native 'final-inventory' "$output/python.exe" @('-I', '-B', $inventory, '--root', $output, '--probe', "$evidence/final-probe.json")
} finally { Pop-Location }

Write-Output "Candidate runtime: $output"
