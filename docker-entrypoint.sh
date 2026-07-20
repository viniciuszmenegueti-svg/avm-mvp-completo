#!/bin/sh
set -e

echo "Aplicando migrations do banco de dados..."
alembic upgrade head

echo "Iniciando a API..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000