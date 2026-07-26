# Guia de Execução no Windows

## 1. Preparar o projeto

```powershell
Expand-Archive ".\avm-mvp-completo.zip" -DestinationPath ".\avm-mvp-completo"
Set-Location ".\avm-mvp-completo"
Copy-Item ".env.example" ".env"
```

## 2. Criar o ambiente Python

```powershell
python -m venv ".venv"
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r "requirements-dev.txt"
```

## 3. Iniciar PostgreSQL e aplicar migrations

```powershell
docker compose up -d db
alembic upgrade head
alembic current
```

O `head` esperado é:

```text
c8d7e6f5a4b3
```

## 4. Executar testes

```powershell
python -m pytest -v
python -m ruff check .
python -m ruff format --check .
```

## 5. Iniciar a API

```powershell
uvicorn app.main:app --reload
```

Acesse:

```text
http://localhost:8000/docs
```

## 6. Execução completa por Docker

```powershell
docker compose up -d --build
docker compose ps
```

## Solução rápida de banco dessincronizado

Use somente em ambiente local descartável:

```powershell
docker compose down -v
docker compose up -d --build
```
