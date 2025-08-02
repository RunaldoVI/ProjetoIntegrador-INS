[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

if (-not (Get-ComputerInfo | Where-Object { $_.OsName -like '*Windows*' })) {
    Write-Host ' Este script é apenas para Windows com WSL. No macOS, a GPU não é suportada com Docker + CUDA.'
    Write-Host ' Podes correr o sistema normalmente com CPU, sem instalar este toolkit.'
    exit 0
}

Write-Host ' Script de instalação do ambiente completo para uso com Docker + GPU'
Write-Host '  Este script verifica e instala WSL2, Ubuntu 22.04, Docker Desktop e suporte a GPU (CUDA para Docker).'
Write-Host ''

# [0/8] Verifica se tens GPU NVIDIA
Write-Host ' [0/8] A verificar se tens GPU NVIDIA...'
$hasNvidia = Get-CimInstance Win32_VideoController | Where-Object { $_.Name -like "*NVIDIA*" }

if (-not $hasNvidia) {
    Write-Host ' ⚠️ Não foi detetada GPU NVIDIA. O sistema irá correr com CPU (mais lento).'
    $gpuAvailable = $false
} else {
    Write-Host " ✅ GPU NVIDIA encontrada: $($hasNvidia.Name)"
    $gpuAvailable = $true
}

# 1. Verifica WSL
Write-Host ' [1/8] A verificar se o WSL está instalado...'
$wslVersion = wsl.exe --version 2>$null
if (-not $wslVersion) {
    Write-Host ' A instalar o WSL com Ubuntu 22.04...'
    wsl --install -d Ubuntu-22.04
    Start-Sleep -Seconds 10
} else {
    Write-Host ' WSL já está instalado.'
}

# 2. Verifica se o WSL 2 está ativo
Write-Host ' [2/8] A verificar se o WSL 2 está ativo...'
$kernelVersion = (wsl --status) -match 'Default Version: 2'
if (-not $kernelVersion) {
    Write-Host ' A definir WSL 2 como padrão...'
    wsl --set-default-version 2
}

# 3. Verifica instalação do Ubuntu
Write-Host ' [3/8] A verificar se o Ubuntu 22.04 está instalado...'
$distros = wsl -l
if ($distros -notmatch 'Ubuntu-22.04') {
    Write-Host ' A instalar Ubuntu 22.04...'
    wsl --install -d Ubuntu-22.04
    Start-Sleep -Seconds 15
} else {
    Write-Host ' Ubuntu 22.04 já está instalado no WSL.'
}

# 4. Verifica Docker Desktop
Write-Host ' [4/8] A verificar se o Docker Desktop está instalado...'
$dockerPath = 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
if (-not (Test-Path $dockerPath)) {
    Write-Host ' ❌ Docker Desktop não encontrado. Instala manualmente: https://www.docker.com/products/docker-desktop/'
    exit 1
}

# 5. Inicia Docker Desktop se necessário
Write-Host ' [5/8] A iniciar Docker Desktop (se necessário)...'
$dockerRunning = Get-Process -Name 'Docker Desktop' -ErrorAction SilentlyContinue
if (-not $dockerRunning) {
    Start-Process $dockerPath
    Start-Sleep -Seconds 10
}

# 6. Aguarda Docker Engine
Write-Host ' [6/8] A aguardar Docker Engine...'
$maxTries = 30
$tries = 0
do {
    $dockerInfo = docker info 2>$null
    if ($dockerInfo) {
        Write-Host ' ✅ Docker está pronto!'
        break
    }
    Write-Host " ⏳ Esperando Docker... ($tries/$maxTries)"
    Start-Sleep -Seconds 2
    $tries++
} while ($tries -lt $maxTries)

if (-not $dockerInfo) {
    Write-Host ' ❌ Docker não arrancou corretamente. Aborta.'
    exit 1
}

# 7. Instala NVIDIA Container Toolkit dentro do Ubuntu (só se houver GPU)
if ($gpuAvailable) {
    Write-Host ' [7/8] A instalar NVIDIA Container Toolkit dentro do Ubuntu (via WSL)...'
    $bashScript = @'
#!/bin/bash
set -e

echo '🔍 Verificando nvidia-smi dentro do WSL...'
if ! command -v nvidia-smi &>/dev/null; then
    echo "'nvidia-smi' não disponível. Instala os drivers no Windows primeiro."
    exit 1
fi
echo " GPU visível: $(nvidia-smi --query-gpu=name --format=csv,noheader)"

if dpkg -l | grep -q nvidia-container-toolkit; then
    echo ' NVIDIA Container Toolkit já está instalado.'
    exit 0
fi

distribution=$(. /etc/os-release; echo $ID$VERSION_ID)

curl -fsSL https://nvidia.github.io/nvidia-docker/gpgkey | gpg --dearmor | sudo tee /usr/share/keyrings/nvidia-docker.gpg > /dev/null
distribution="ubuntu22.04"
echo "deb [signed-by=/usr/share/keyrings/nvidia-docker.gpg] https://nvidia.github.io/nvidia-docker/$distribution/x86_64 stable" | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt update
sudo apt install -y nvidia-container-toolkit

echo ' A reiniciar serviços...'
sudo systemctl restart docker || true
'@

    $bashScript = $bashScript -replace '`r', ''
    $encoded = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($bashScript))
    wsl -d Ubuntu-22.04 -- bash -c "echo $encoded | base64 -d | bash"

    # Reinicia WSL (opcional mas recomendado)
    Write-Host ' 🔄 A reiniciar o WSL para garantir que o Docker usa o runtime da NVIDIA... '
    wsl --shutdown
    Start-Sleep -Seconds 5
} else {
    Write-Host ' [7/8] Ignorado: Sem GPU NVIDIA disponível — a correr com CPU.'
}

# 8. Testa GPU com Docker
Write-Host ' [8/8] A testar suporte à GPU (docker run com CUDA)...'
try {
    docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
    Write-Host ' ✅ GPU detectada e ativa para Docker.'
} catch {
    Write-Host ' ⚠️ GPU não disponível para Docker. O sistema irá correr com o CPU (mais lento).'
}

Write-Host ''
Write-Host ' 🔄 Nota: Se não tens GPU compatível, o sistema continuará a funcionar com CPU (mais lento).'
Write-Host ' 💾 Certifica-te de que tens memória suficiente (~8GB ou mais).'
Write-Host ' ✅ Tudo pronto! Corre agora: docker compose up --build'
