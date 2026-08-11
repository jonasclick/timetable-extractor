[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$BotToken,

    [Parameter(Mandatory = $true)]
    [string]$FunctionBaseUrl,

    [Parameter(Mandatory = $true)]
    [string]$SecretToken
)

$ErrorActionPreference = "Stop"

$webhookUrl = "$($FunctionBaseUrl.TrimEnd('/'))/api/telegram/webhook"
$payload = @{
    url = $webhookUrl
    secret_token = $SecretToken
    allowed_updates = '["message"]'
}

Invoke-RestMethod `
    -Method Post `
    -Uri "https://api.telegram.org/bot$BotToken/setWebhook" `
    -Body $payload `
    -ContentType "application/x-www-form-urlencoded"

Write-Host "Webhook updated: $webhookUrl"
