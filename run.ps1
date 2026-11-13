param(
    [ValidateSet('up', 'ai', 'down', 'stop', 'logs', 'discover', 'rebuild', 'test', 'native', 'help', '-h', '--help')]
    [string]$Command = 'up'
)

$ErrorActionPreference = 'Stop'

# Use Git for Windows, not the unrelated WSL bash.exe from System32.
$candidates = @()
$gitCommand = Get-Command git.exe -ErrorAction SilentlyContinue
if ($gitCommand) {
    $gitRoot = Split-Path (Split-Path $gitCommand.Source -Parent) -Parent
    $candidates += Join-Path $gitRoot 'bin\bash.exe'
}
if ($env:ProgramFiles) { $candidates += Join-Path $env:ProgramFiles 'Git\bin\bash.exe' }
if (${env:ProgramFiles(x86)}) { $candidates += Join-Path ${env:ProgramFiles(x86)} 'Git\bin\bash.exe' }
if ($env:LOCALAPPDATA) { $candidates += Join-Path $env:LOCALAPPDATA 'Programs\Git\bin\bash.exe' }
$gitBash = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
if (-not $gitBash) {
    Write-Error 'Git for Windows is required. Install it and retry run.cmd.'
    exit 1
}

Push-Location $PSScriptRoot
try {
    & $gitBash './run.sh' $Command
    $result = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $result
