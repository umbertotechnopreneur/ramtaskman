[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string] $Msi,
    [Parameter(Mandatory)] [string] $Version,
    [string] $PreviousMsi,
    [string] $PreviousVersion
)

$ErrorActionPreference = 'Stop'
$installFolder = Join-Path $env:LOCALAPPDATA 'Ram Taskman'
$executable = Join-Path $installFolder 'ramtaskman.exe'
$shortcut = Join-Path ([Environment]::GetFolderPath('Programs')) 'Ram Taskman.lnk'
$uninstallKeys = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
    'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*'
$msi = (Resolve-Path -LiteralPath $Msi).Path
if ([bool] $PreviousMsi -ne [bool] $PreviousVersion) {
    throw 'Supply both PreviousMsi and PreviousVersion for the upgrade check.'
}
if ($PreviousMsi) {
    $PreviousMsi = (Resolve-Path -LiteralPath $PreviousMsi).Path
}

function Get-PathEntries([string] $Value) {
    $Value -split ';' | Where-Object { $_ } | ForEach-Object { $_.TrimEnd('\') }
}

function Invoke-Installer([string] $Action, [string] $Package) {
    $process = Start-Process msiexec.exe -ArgumentList @($Action, ('"' + $Package + '"'), '/qn', '/norestart') -WindowStyle Hidden -Wait -PassThru
    if ($process.ExitCode -ne 0) {
        throw "msiexec $Action failed with exit code $($process.ExitCode) for $Package"
    }
}

function Assert-Path([int] $ExpectedCount) {
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $entries = @(Get-PathEntries $userPath)
    $count = @($entries | Where-Object { $_ -ieq $installFolder }).Count
    if ($count -ne $ExpectedCount) {
        throw "Expected $ExpectedCount Ram Taskman entries in the user PATH, found $count."
    }
    $otherEntries = @($entries | Where-Object { $_ -ine $installFolder })
    if (($otherEntries -join ';') -cne ($originalUserEntries -join ';')) {
        throw 'The installer changed unrelated user PATH entries.'
    }
    if ([Environment]::GetEnvironmentVariable('Path', 'Machine') -cne $originalMachinePath) {
        throw 'The installer changed the machine PATH.'
    }
}

function Assert-Installed([string] $ExpectedVersion) {
    Assert-Path 1
    if (!(Test-Path -LiteralPath $shortcut -PathType Leaf)) {
        throw 'Missing user Start menu shortcut.'
    }
    $machinePath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = "$machinePath;$userPath"
    $resolved = (Get-Command ramtaskman.exe -CommandType Application).Source
    if ($resolved -ine $executable) {
        throw "PATH resolved Ram Taskman to $resolved"
    }
    $actualVersion = & ramtaskman.exe --version
    if ($LASTEXITCODE -ne 0 -or $actualVersion -ne $ExpectedVersion) {
        throw "Expected version $ExpectedVersion on PATH, found $actualVersion"
    }
    & ramtaskman.exe --verify-bundle
    if ($LASTEXITCODE -ne 0) { throw 'Installed bundle verification failed.' }
}

function Assert-Removed {
    Assert-Path 0
    if ((Test-Path -LiteralPath $executable) -or (Test-Path -LiteralPath $shortcut)) {
        throw 'Uninstall left the executable or the Start menu shortcut behind.'
    }
    $registered = Get-ItemProperty -Path $uninstallKeys -ErrorAction SilentlyContinue |
        Where-Object { $_.DisplayName -like 'Ram Taskman *' }
    if ($registered) { throw 'A Ram Taskman installer registration is still present.' }
}

$originalProcessPath = $env:Path
$originalMachinePath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
$originalUserEntries = @(Get-PathEntries ([Environment]::GetEnvironmentVariable('Path', 'User')))
Assert-Removed

$installedPackage = $null
try {
    Invoke-Installer '/i' $msi
    $installedPackage = $msi
    Assert-Installed $Version
    Invoke-Installer '/x' $installedPackage
    $installedPackage = $null
    Assert-Removed
    Write-Host "Clean install and uninstall of $Version passed, including PATH and Start menu."

    if ($PreviousMsi) {
        Invoke-Installer '/i' $PreviousMsi
        $installedPackage = $PreviousMsi
        Assert-Installed $PreviousVersion
        Invoke-Installer '/i' $msi
        $installedPackage = $msi
        Assert-Installed $Version
        $oldVersion = Get-ItemProperty -Path $uninstallKeys -ErrorAction SilentlyContinue |
            Where-Object { $_.DisplayName -eq "Ram Taskman $PreviousVersion (per-user)" }
        if ($oldVersion) { throw "The old version $PreviousVersion is still registered." }
        Invoke-Installer '/x' $installedPackage
        $installedPackage = $null
        Assert-Removed
        Write-Host "Upgrade from $PreviousVersion to $Version and uninstall passed, including PATH and Start menu."
    }
} finally {
    $env:Path = $originalProcessPath
    if ($installedPackage) {
        Invoke-Installer '/x' $installedPackage
    }
}
