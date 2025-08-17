[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host '⚙️ Instalação do ambiente (Docker + WSL2) sem reiniciar o Docker'
Write-Host ''

# [0/8] Windows?
if (-not (Get-ComputerInfo | Where-Object { $_.OsName -like '*Windows*' })) {
    Write-Host '❌ Este script é apenas para Windows com WSL.'
    exit 0
}

# [1/8] GPU NVIDIA presente no Windows?
Write-Host '🔍 [1/8] Verificar GPU NVIDIA no Windows...'
$hasNvidia = Get-CimInstance Win32_VideoController | Where-Object { $_.Name -like "*NVIDIA*" }
$gpuOnWindows = $false
if ($hasNvidia) {
    Write-Host "✅ GPU NVIDIA detetada: $($hasNvidia.Name)"
    $gpuOnWindows = $true
} else {
    Write-Host '⚠️ Nenhuma GPU NVIDIA detetada no Windows — seguiremos em CPU.'
}

# [2/8] WSL instalado?
Write-Host '🔍 [2/8] Verificar WSL...'
$wslVersion = wsl.exe --version 2>$null
if (-not $wslVersion) {
    Write-Host '🔧 A instalar o WSL com Ubuntu 22.04...'
    wsl --install -d Ubuntu-22.04
    Start-Sleep -Seconds 10
} else {
    Write-Host '✅ WSL já está instalado.'
}

# [3/8] WSL 2 ativo?
Write-Host '🔍 [3/8] Verificar WSL 2...'
$defaultIsV2 = (wsl --status) -match 'Default Version: 2'
if (-not $defaultIsV2) {
    Write-Host '🔧 A definir WSL 2 como padrão...'
    wsl --set-default-version 2
} else {
    Write-Host '✅ WSL 2 já está ativo.'
}

# [4/8] Ubuntu 22.04 disponível?

Write-Host '🔍 [4/8] Verificar Ubuntu no WSL...'

# Lista “limpa” das distros (sem o asterisco do default, sem espaços)
$distros = (& wsl.exe -l -q 2>$null) | ForEach-Object { $_.Trim().TrimStart('*').Trim() }

$hasUbuntu2204 = $distros -contains 'Ubuntu-22.04'
$hasUbuntu      = $hasUbuntu2204 -or ($distros -contains 'Ubuntu')

if ($hasUbuntu) {
    Write-Host '✅ Ubuntu já está instalado no WSL.'
    # Garante que é WSL2 e define como default (não abre shell)
    try {
        # Se a distro “Ubuntu” existir mas não “Ubuntu-22.04”, ainda assim força V2 e default
        $distroName = if ($hasUbuntu2204) { 'Ubuntu-22.04' } else { 'Ubuntu' }
        wsl.exe -l -v | Out-Null  # aquece
        wsl.exe --set-version $distroName 2 | Out-Null
        wsl.exe --set-default $distroName  | Out-Null
    } catch { }
}
else {
    Write-Host '⚠️ Ubuntu 22.04 não encontrado.'
    Write-Host '   Vai instalar agora (apenas esta 1ª vez poderás ver uma shell; se aparecer, escreve "exit" no fim).'
    Start-Process -FilePath "wsl.exe" -ArgumentList "--install -d Ubuntu-22.04" -NoNewWindow -Wait
    Start-Sleep -Seconds 15
    Write-Host '✅ Ubuntu 22.04 instalado.'
    # Depois da instalação, define default e V2 sem abrir shell
    try {
        wsl.exe --set-default Ubuntu-22.04 | Out-Null
        wsl.exe --set-version Ubuntu-22.04 2 | Out-Null
    } catch { }
}

# [5/8] Docker Desktop instalado e a correr?
Write-Host '🔍 [5/8] Verificar Docker Desktop...'
$dockerPath = 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
if (-not (Test-Path $dockerPath)) {
    Write-Host '❌ Docker Desktop não encontrado. Instala a partir de docker.com.'
    exit 1
}

Write-Host '🖥️ [6/8] A iniciar Docker Desktop se necessário...'
$dockerRunning = Get-Process -Name 'Docker Desktop' -ErrorAction SilentlyContinue
if (-not $dockerRunning) {
    Start-Process $dockerPath
    Start-Sleep -Seconds 10
} else {
    Write-Host '✅ Docker Desktop já está em execução.'
}

# [7/8] Aguardar Docker Engine (sem reiniciar)
Write-Host '⏳ [7/8] A aguardar Docker Engine...'
$maxTries = 60
$tries = 0
do {
    $dockerInfo = docker version 2>$null
    if ($dockerInfo) { break }
    Start-Sleep -Seconds 2
    $tries++
    if ($tries % 5 -eq 0) { Write-Host "⌛ Aguardando Docker... ($tries/$maxTries)" }
} while ($tries -lt $maxTries)

if (-not $dockerInfo) {
    Write-Host '❌ Docker não ficou pronto. Abortar sem reiniciar.'
    exit 1
}
Write-Host '✅ Docker está pronto!'

# [8/8] Teste de GPU por container (sem instalar toolkit no WSL e sem reiniciar)
$useGpu = $false
if ($gpuOnWindows) {
    Write-Host '🔍 Testar acesso à GPU via Docker (Docker Desktop + WSL2)...'
    try {
        # Pull rápido e teste de nvidia-smi; se falhar, seguimos em CPU
        docker pull --quiet nvidia/cuda:12.2.0-base-ubuntu22.04 | Out-Null
        $gpuTest = docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi 2>&1
        if ($LASTEXITCODE -eq 0 -and $gpuTest -match "NVIDIA-SMI") {
            Write-Host '✅ GPU acessível dentro de containers.'
            $useGpu = $true
        } else {
            Write-Host '⚠️ GPU não acessível via Docker neste momento. Vamos seguir em CPU sem reiniciar o Docker.'
            Write-Host 'ℹ️ Verifica no Docker Desktop: Settings > Resources > WSL integration (ativar Ubuntu) e GPU support.'
        }
    } catch {
        Write-Host '⚠️ Falha no teste de GPU. Vamos seguir em CPU.'
    }
} else {
    Write-Host 'ℹ️ Sem GPU no Windows → CPU.'
}

# Lançar os serviços com/sem GPU (sem reiniciar nada)
Write-Host ''
if ($useGpu) {
    if (Test-Path "docker-compose.gpu.yml") {
        Write-Host "⚡ A correr docker compose com GPU (sem reinício do Docker)..."
        docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
    } else {
        Write-Host "⚡ A correr docker compose (GPU via --gpus all nos serviços que suportem)..."
        docker compose up --build
    }
} else {
    Write-Host "⚡ A correr docker compose (CPU apenas, sem reinício do Docker)..."
    docker compose up --build
}
