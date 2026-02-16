#!/bin/bash

# Script de Despliegue Automático - Agente BI
# Sistema: Ubuntu 22.04 LTS

echo "🚀 Iniciando despliegue de Agente BI..."

# 1. Actualizar sistema
sudo apt update && sudo apt upgrade -y

# 2. Instalar dependencias base
sudo apt install -y python3-pip python3-venv nginx git certbot python3-certbot-nginx

# 3. Preparar directorio y entorno
mkdir -p ~/agente_bi
cd ~/agente_bi
python3 -m venv venv
source venv/bin/activate

# 4. Instalar dependencias de Python
pip install --upgrade pip
# Nota: El usuario debe subir sus archivos antes o clonar desde git
# pip install -r requirements.txt

echo "✅ Entorno base preparado."
echo "⚠️  IMPORTANTE: Sube tus archivos (app.py, src/, .env, client_secret.json) a ~/agente_bi"
echo "Luego ejecuta: source venv/bin/activate && pip install -r requirements.txt"
