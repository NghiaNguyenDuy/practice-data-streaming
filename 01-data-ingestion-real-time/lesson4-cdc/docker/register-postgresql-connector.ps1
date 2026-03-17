$connectorConfigPath = Join-Path $PSScriptRoot "register-postgresql-connector.json"
$connectorConfig = Get-Content $connectorConfigPath -Raw

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8083/connectors/" `
  -ContentType "application/json" `
  -Body $connectorConfig
