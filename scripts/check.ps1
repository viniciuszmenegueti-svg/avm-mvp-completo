$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "1/5 Auditando dependencias de producao..."
pip-audit -r requirements.txt

Write-Host ""
Write-Host "2/5 Verificando qualidade do codigo..."
ruff check .

Write-Host ""
Write-Host "3/5 Verificando formatacao do codigo..."
ruff format --check .

Write-Host ""
Write-Host "4/5 Verificando tipos com MyPy..."
python -m mypy

Write-Host ""
Write-Host "5/5 Executando testes com cobertura..."
python -m pytest

Write-Host ""
Write-Host "Todas as verificacoes foram concluidas com sucesso."