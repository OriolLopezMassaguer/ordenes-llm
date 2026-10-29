# Instalación en Windows (PowerShell):  .\instalar.ps1
# Si PowerShell bloquea el script:  powershell -ExecutionPolicy Bypass -File .\instalar.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Get-Command uv -ErrorAction SilentlyContinue) {
    Write-Host "Instalando con uv..."
    uv sync --extra anthropic
    Write-Host "`nListo. Ejecuta los scripts con:  uv run python scripts\experimento_fase1.py --help"
    Write-Host "Tests:  uv run pytest"
    exit 0
}

# (sin el operador ?? para que funcione también en Windows PowerShell 5.1)
$py = Get-Command py -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command python -ErrorAction SilentlyContinue }
if (-not $py) { throw "No encuentro Python. Instala Python 3.10+ (python.org) o uv (https://docs.astral.sh/uv/)." }

Write-Host "Instalando con venv + pip..."
& $py.Source -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -e ".[anthropic,dev]"
Write-Host "`nListo. Activa el entorno con:  .\.venv\Scripts\Activate.ps1"
Write-Host "Luego:  python scripts\experimento_fase1.py --help   y   pytest"
