# Script de Configuración Local - Agente BI (Windows PowerShell)

Write-Host "🔧 Iniciando configuración de entorno local..." -ForegroundColor Cyan

# 1. Configuración del Servidor
Write-Host "`n📡 Configurando Servidor..." -ForegroundColor Green
cd server
if (-not (Test-Path ".venv")) {
    Write-Host "📦 Creando entorno virtual..."
    python -m venv .venv
}
Write-Host "📥 Instalando dependencias de Python..."
& ".\.venv\Scripts\pip" install -r requirements.txt

if (-not (Test-Path ".env")) {
    Write-Host "📄 Creando .env desde .env.example..."
    Copy-Item ".env.example" ".env"
}
cd ..

# 2. Configuración del Cliente
Write-Host "`n💻 Configurando Cliente..." -ForegroundColor Green
cd client
Write-Host "📥 Instalando dependencias de Node..."
npm install

if (-not (Test-Path ".env.local")) {
    Write-Host "📄 Creando .env.local desde .env.local.example..."
    Copy-Item ".env.local.example" ".env.local"
}
cd ..

Write-Host "`n✅ Configuración completada!" -ForegroundColor Cyan
Write-Host "🚀 Para iniciar el proyecto, ejecuta: python run_dev.py" -ForegroundColor Yellow
