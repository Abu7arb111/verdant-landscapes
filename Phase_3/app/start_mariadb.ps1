# Starts the Landscaping portal against the MariaDB database on VT Discovery,
# so every change made on the website shows up in phpMyAdmin.
#
#   powershell -ExecutionPolicy Bypass -File Phase_3\app\start_mariadb.ps1
#
# Needs: kubectl, and the Discovery KubeConfig saved as %USERPROFILE%\.kube\config.
# The server asks for the MariaDB user/password unless they are in the environment
# or in db_config.local.json (see db_config.local.example.json).

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$localPort = 3307

function Test-Port([int]$port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try { $client.ConnectAsync('127.0.0.1', $port).Wait(500) -and $client.Connected } catch { $false } finally { $client.Dispose() }
}

$forward = $null
if (Test-Port $localPort) {
    Write-Host "Port $localPort is already open; using the existing port-forward."
} else {
    if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
        Write-Host "kubectl is not installed. Install it, then open a new terminal and run this again:" -ForegroundColor Red
        Write-Host "    winget install -e --id Kubernetes.kubectl"
        exit 1
    }
    if (-not $env:KUBECONFIG -and -not (Test-Path "$HOME\.kube\config")) {
        Write-Host "No KubeConfig found. On the Discovery cluster dashboard click 'Copy KubeConfig'" -ForegroundColor Red
        Write-Host "and save it as $HOME\.kube\config, then run this again."
        exit 1
    }
    Write-Host "Starting port-forward: localhost:$localPort -> svc/mariadb:3306 ..."
    $forward = Start-Process kubectl -ArgumentList '-n', 'ai-landscaping-db', 'port-forward', 'svc/mariadb', "${localPort}:3306" `
        -WindowStyle Minimized -PassThru
    $deadline = (Get-Date).AddSeconds(20)
    while (-not (Test-Port $localPort)) {
        if ($forward.HasExited -or (Get-Date) -gt $deadline) {
            Write-Host "The port-forward did not start. Run this to see the error:" -ForegroundColor Red
            Write-Host "    kubectl -n ai-landscaping-db port-forward svc/mariadb ${localPort}:3306"
            exit 1
        }
        Start-Sleep -Milliseconds 500
    }
}

$env:DB_HOST = '127.0.0.1'
$env:DB_PORT = "$localPort"
if (-not $env:DB_NAME) { $env:DB_NAME = 'landscaping_db' }

# Ask for the MariaDB login here (PowerShell's prompt shows *** and accepts paste),
# unless it is already in the environment or in db_config.local.json.
$configFile = Join-Path $here 'db_config.local.json'
$config = if (Test-Path $configFile) { Get-Content $configFile -Raw | ConvertFrom-Json } else { $null }
if (-not $env:DB_USER) {
    if ($config -and $config.DB_USER -and $config.DB_USER -ne 'YOUR_DB_USER') { $env:DB_USER = $config.DB_USER }
    else { $env:DB_USER = (Read-Host 'MariaDB username').Trim() }
}
$setPass = $false
if (-not $env:DB_PASS -and -not ($config -and $config.DB_PASS)) {
    $secure = Read-Host "MariaDB password for $($env:DB_USER) (paste with right-click or Ctrl+V)" -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try { $env:DB_PASS = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
    $setPass = $true
}

$python = Join-Path $here '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { $python = (Get-Command py -ErrorAction SilentlyContinue).Source }
if (-not $python) { $python = (Get-Command python).Source }
& $python -c "import pymysql" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing the MariaDB driver (PyMySQL)..."
    & $python -m pip install -r (Join-Path $here 'requirements.txt')
}

try {
    & $python (Join-Path $here 'server.py')
} finally {
    if ($setPass) { Remove-Item Env:DB_PASS -ErrorAction SilentlyContinue }
    if ($forward -and -not $forward.HasExited) {
        Stop-Process -Id $forward.Id -ErrorAction SilentlyContinue
        Write-Host "Port-forward stopped."
    }
}
