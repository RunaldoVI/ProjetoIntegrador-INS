[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host '⚙️ Script de instalação do ambiente completo para Docker + WSL2 + GPU (opcional)'
Write-Host ''

# [0/8] Verifica se o sistema é Windows
if (-not (Get-ComputerInfo | Where-Object { $_.OsName -like '*Windows*' })) {
    Write-Host '❌ Este script é apenas para Windows com WSL. No macOS não há suporte a GPU com Docker.'
    exit 0
}

# [1/8] Verifica se há GPU NVIDIA no sistema
Write-Host '🔍 [1/8] Verificar presença de GPU NVIDIA no sistema...'
$hasNvidia = Get-CimInstance Win32_VideoController | Where-Object { $_.Name -like "*NVIDIA*" }
$gpuAvailable = $false
if ($hasNvidia) {
    Write-Host "✅ GPU NVIDIA detectada: $($hasNvidia.Name)"
    $gpuAvailable = $true
} else {
    Write-Host '⚠️ Nenhuma GPU NVIDIA detetada. O sistema correrá com CPU.'
}

# [2/8] Verifica WSL
Write-Host '🔍 [2/8] Verificar instalação do WSL...'
$wslVersion = wsl.exe --version 2>$null
if (-not $wslVersion) {
    Write-Host '🔧 A instalar o WSL com Ubuntu 22.04...'
    wsl --install -d Ubuntu-22.04
    Start-Sleep -Seconds 10
} else {
    Write-Host '✅ WSL já está instalado.'
}

# [3/8] Verifica se o WSL 2 está ativo
Write-Host '🔍 [3/8] Verificar se WSL 2 está ativo...'
$kernelVersion = (wsl --status) -match 'Default Version: 2'
if (-not $kernelVersion) {
    Write-Host '🔧 A definir WSL 2 como padrão...'
    wsl --set-default-version 2
} else {
    Write-Host '✅ WSL 2 já está ativo.'
}

# [4/8] Verifica instalação do Ubuntu
Write-Host '🔍 [4/8] Verificar se o Ubuntu 22.04 está instalado no WSL...'
$distros = wsl -l
if ($distros -notmatch 'Ubuntu-22.04') {
    Write-Host '🔧 A instalar Ubuntu 22.04...'
    wsl --install -d Ubuntu-22.04
    Start-Sleep -Seconds 15
} else {
    Write-Host '✅ Ubuntu 22.04 já está instalado.'
}

# [5/8] Verifica Docker Desktop
Write-Host '🔍 [5/8] Verificar instalação do Docker Desktop...'
$dockerPath = 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
if (-not (Test-Path $dockerPath)) {
    Write-Host '❌ Docker Desktop não encontrado. Instala manualmente: https://www.docker.com/products/docker-desktop/'
    exit 1
}

# [6/8] Inicia Docker Desktop se necessário
Write-Host '🖥️ [6/8] A iniciar Docker Desktop (se necessário)...'
$dockerRunning = Get-Process -Name 'Docker Desktop' -ErrorAction SilentlyContinue
if (-not $dockerRunning) {
    Start-Process $dockerPath
    Start-Sleep -Seconds 10
} else {
    Write-Host '✅ Docker já está em execução.'
}

# [7/8] Aguarda Docker Engine
Write-Host '⏳ [7/8] A aguardar Docker Engine...'
$maxTries = 30
$tries = 0
do {
    $dockerInfo = docker info 2>$null
    if ($dockerInfo) {
        Write-Host '✅ Docker está pronto!'
        break
    }
    Write-Host "⌛ Esperando Docker... ($tries/$maxTries)"
    Start-Sleep -Seconds 2
    $tries++
} while ($tries -lt $maxTries)

if (-not $dockerInfo) {
    Write-Host '❌ Docker não arrancou corretamente. Abortar.'
    exit 1
}

# [8/8] Verifica GPU dentro do WSL e instala Toolkit se for utilizável
$gpuFunctional = $false
if ($gpuAvailable) {
    Write-Host '🔍 Verificando se a GPU está acessível dentro do WSL...'

    $gpuTest = wsl -d Ubuntu-22.04 -- nvidia-smi 2>&1
    if ($gpuTest -like "*failed*" -or $gpuTest -like "*not found*" -or $gpuTest -like "*no adapters*" -or $gpuTest -like "*error*") {
        Write-Host '⚠️ GPU não está funcional dentro do WSL. Ignorar instalação do NVIDIA Toolkit.'
    } else {
        Write-Host '✅ GPU detetada dentro do WSL. A instalar NVIDIA Container Toolkit...'
        $gpuFunctional = $true

        $bashScript = @'
#!/bin/bash
set -e
distribution=$(. /etc/os-release; echo $ID$VERSION_ID)

echo '🔧 A instalar NVIDIA Container Toolkit...'
curl -fsSL https://nvidia.github.io/nvidia-docker/gpgkey | gpg --dearmor | sudo tee /usr/share/keyrings/nvidia-docker.gpg > /dev/null
distribution="ubuntu22.04"
echo "deb [signed-by=/usr/share/keyrings/nvidia-docker.gpg] https://nvidia.github.io/nvidia-docker/$distribution/x86_64 stable" | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo systemctl restart docker || true
'@

        $encoded = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($bashScript))
        wsl -d Ubuntu-22.04 -- bash -c "echo $encoded | base64 -d | bash"

        Write-Host '🔁 A reiniciar WSL...'
        wsl --shutdown
        Start-Sleep -Seconds 5
    }
} else {
    Write-Host '⚠️ GPU não disponível — a correr com CPU.'
}

# Gerar ficheiro .env com suporte a GPU (ou não)
$envFilePath = ".env"
if ($gpuFunctional) {
    Write-Host "📝 A gerar ficheiro `.env` com suporte a GPU..."
    Set-Content -Path $envFilePath -Value @"
GPU_DRIVER=nvidia
GPU_COUNT=all
"@
} else {
    Write-Host "📝 A gerar ficheiro `.env` para correr com CPU..."
    Set-Content -Path $envFilePath -Value @"
GPU_DRIVER=none
GPU_COUNT=0
"@
}

# Final
Write-Host ''
Write-Host '✅ Instalação concluída!'
Write-Host '⚡ Podes agora correr: docker compose up --build'
Write-Host '🧠 O sistema usará GPU se disponível, caso contrário, CPU.'

if ($gpuFunctional) {
    Write-Host "⚡ A correr docker-compose com suporte a GPU..."
    docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
} else {
    Write-Host "⚡ A correr docker-compose sem GPU (CPU apenas)..."
    docker compose up --build
}

