$ErrorActionPreference = "Stop"

$BaseUrl = "http://localhost:8000"
$RequestId = "smoke-test-local"

function Invoke-SmokeRequest {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    return Invoke-WebRequest `
        -Uri "$BaseUrl$Path" `
        -Method Get `
        -Headers @{
            "X-Request-ID" = $RequestId
        } `
        -UseBasicParsing
}

Write-Host "Verificando liveness..."
$liveResponse = Invoke-SmokeRequest -Path "/health/live"
$liveBody = $liveResponse.Content | ConvertFrom-Json

if ($liveResponse.StatusCode -ne 200) {
    throw "Liveness retornou status inesperado."
}

if ($liveBody.status -ne "ok") {
    throw "Liveness não retornou status ok."
}

Write-Host "Verificando readiness..."
$readyResponse = Invoke-SmokeRequest -Path "/health/ready"
$readyBody = $readyResponse.Content | ConvertFrom-Json

if ($readyResponse.StatusCode -ne 200) {
    throw "Readiness retornou status inesperado."
}

if ($readyBody.database -ne "ok") {
    throw "Banco de dados não está disponível."
}

Write-Host "Verificando cidades..."
$citiesResponse = Invoke-SmokeRequest -Path "/cities"
$citiesBody = $citiesResponse.Content | ConvertFrom-Json

if ($citiesResponse.StatusCode -ne 200) {
    throw "Consulta de cidades retornou status inesperado."
}

if ($citiesBody.Count -ne 10) {
    throw "Quantidade inesperada de cidades: $($citiesBody.Count)."
}

Write-Host "Verificando Request ID..."
$responseRequestId = $citiesResponse.Headers[
    "X-Request-ID"
]

if ($responseRequestId -ne $RequestId) {
    throw "A API não preservou o X-Request-ID."
}

Write-Host ""
Write-Host "Smoke test concluído com sucesso."
Write-Host "API: ok"
Write-Host "Banco: ok"
Write-Host "Cidades: $($citiesBody.Count)"
Write-Host "Request ID: $responseRequestId"
