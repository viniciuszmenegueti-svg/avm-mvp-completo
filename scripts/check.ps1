$ErrorActionPreference = "Stop"

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Title,

        [Parameter(Mandatory = $true)]
        [scriptblock]$Command
    )

    Write-Host ""
    Write-Host $Title

    & $Command

    if ($LASTEXITCODE -ne 0) {
        throw "A etapa falhou com codigo de saida $LASTEXITCODE."
    }
}

try {
    Invoke-Step "1/5 Auditando dependencias de producao..." {
        python -m pip_audit -r requirements.txt
    }

    Invoke-Step "2/5 Verificando qualidade do codigo..." {
        ruff check .
    }

    Invoke-Step "3/5 Verificando formatacao do codigo..." {
        ruff format --check .
    }

    Invoke-Step "4/5 Verificando tipos com MyPy..." {
        python -m mypy
    }

    Invoke-Step "5/5 Executando testes com cobertura..." {
        python -m pytest
    }

    Write-Host ""
    Write-Host "Todas as verificacoes foram concluidas com sucesso."
    exit 0
}
catch {
    Write-Host ""
    Write-Error "Falha nas verificacoes: $($_.Exception.Message)"
    exit 1
}