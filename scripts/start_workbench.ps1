param(
    [ValidateRange(1, 65535)][int]$Port = 8765,
    [switch]$Build
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Project .venv is missing. Create the Python environment first.'
}
Push-Location $projectRoot
try {
    if ($Build -or -not (Test-Path -LiteralPath 'frontend/dist/index.html')) {
        if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
            throw 'Node.js and npm are required to build the frontend.'
        }
        Push-Location 'frontend'
        try {
            & npm.cmd ci --no-fund --no-audit
            if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
            & npm.cmd run build
            if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
        } finally { Pop-Location }
    }
    Write-Host "Open http://127.0.0.1:$Port (Ctrl+C to stop)"
    & $pythonPath -m workbench.server --port $Port
    if ($LASTEXITCODE -ne 0) { throw 'Workbench server exited with an error.' }
} finally { Pop-Location }
