$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppPath = Join-Path $ScriptDir "app.py"
$RequirementsPath = Join-Path $ScriptDir "requirements.txt"
$PythonInstaller = Join-Path $ScriptDir "python-installer.exe"

function Get-PythonCommand {
    $pyCmd = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCmd) {
        return @($pyCmd.Source, "-3")
    }

    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        return @($pythonCmd.Source)
    }

    return $null
}

function Test-PythonWorks {
    param (
        [string[]]$CommandParts
    )

    if (-not $CommandParts) {
        return $false
    }

    try {
        $output = Invoke-Python -PythonCommand $CommandParts -Arguments @("--version") 2>&1
        return $LASTEXITCODE -eq 0 -and $output
    } catch {
        return $false
    }
}

function Invoke-Python {
    param (
        [string[]]$PythonCommand,
        [string[]]$Arguments
    )

    if (-not $PythonCommand) {
        throw "Python-Befehl fehlt."
    }

    $exe = $PythonCommand[0]
    $prefixArgs = @()
    if ($PythonCommand.Length -gt 1) {
        $prefixArgs = $PythonCommand[1..($PythonCommand.Length - 1)]
    }

    & $exe @prefixArgs @Arguments
}

function Install-PythonWithWinget {
    $wingetCmd = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $wingetCmd) {
        return $false
    }

    Write-Host "Python nicht gefunden. Versuche automatische Installation ueber winget ..."
    & $wingetCmd.Source install --id Python.Python.3.11 -e --source winget --accept-package-agreements --accept-source-agreements
    return $LASTEXITCODE -eq 0
}

function Download-PythonInstaller {
    $pythonUrl = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
    Write-Host "Lade offiziellen Python-Installer herunter ..."
    Invoke-WebRequest -Uri $pythonUrl -OutFile $PythonInstaller
}

function Start-PythonInstaller {
    Write-Host "Starte Python-Installer. Bitte Installation abschliessen und danach dieses Fenster offen lassen."
    Start-Process -FilePath $PythonInstaller -ArgumentList "/passive", "InstallAllUsers=0", "PrependPath=1", "Include_pip=1" -Wait
}

function Ensure-Python {
    $pythonCommand = Get-PythonCommand
    if (Test-PythonWorks -CommandParts $pythonCommand) {
        return $pythonCommand
    }

    $installed = Install-PythonWithWinget
    if ($installed) {
        $pythonCommand = Get-PythonCommand
        if (Test-PythonWorks -CommandParts $pythonCommand) {
            return $pythonCommand
        }
    }

    Download-PythonInstaller
    Start-PythonInstaller

    $pythonCommand = Get-PythonCommand
    if (Test-PythonWorks -CommandParts $pythonCommand) {
        return $pythonCommand
    }

    throw "Python konnte nicht automatisch eingerichtet werden."
}

function Install-Requirements {
    param (
        [string[]]$PythonCommand
    )

    Write-Host "Pruefe pip ..."
    Invoke-Python -PythonCommand $PythonCommand -Arguments @("-m", "ensurepip", "--upgrade") | Out-Host

    Write-Host "Aktualisiere pip ..."
    Invoke-Python -PythonCommand $PythonCommand -Arguments @("-m", "pip", "install", "--upgrade", "pip") | Out-Host

    if (Test-Path $RequirementsPath) {
        $hasPackages = (Get-Content $RequirementsPath | Where-Object {
            $_.Trim() -and -not $_.Trim().StartsWith("#")
        }).Count -gt 0

        if ($hasPackages) {
            Write-Host "Installiere benoetigte Python-Bibliotheken ..."
            Invoke-Python -PythonCommand $PythonCommand -Arguments @("-m", "pip", "install", "-r", $RequirementsPath) | Out-Host
        } else {
            Write-Host "Keine zusaetzlichen Python-Bibliotheken erforderlich."
        }
    }
}

function Start-App {
    param (
        [string[]]$PythonCommand
    )

    Write-Host "Starte Anwendung ..."
    Invoke-Python -PythonCommand $PythonCommand -Arguments @($AppPath)
}

try {
    Set-Location $ScriptDir
    $pythonCommand = Ensure-Python
    Install-Requirements -PythonCommand $pythonCommand
    Start-App -PythonCommand $pythonCommand
} catch {
    Write-Host ""
    Write-Host "Start fehlgeschlagen: $($_.Exception.Message)"
    Write-Host "Druecke Enter zum Beenden ..."
    Read-Host | Out-Null
    exit 1
}
