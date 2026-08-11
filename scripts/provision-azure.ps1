[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$SubscriptionId,

    [Parameter(Mandatory = $true)]
    [string]$ResourceGroupName,

    [Parameter(Mandatory = $true)]
    [string]$FunctionAppName,

    [Parameter(Mandatory = $true)]
    [string]$Location,

    [Parameter(Mandatory = $true)]
    [string]$GitHubRepository,

    [string]$StorageAccountName = "",
    [string]$ManagedIdentityName = "",
    [string]$GitHubBranch = "main"
)

$ErrorActionPreference = "Stop"

if (-not $StorageAccountName) {
    $baseName = ($FunctionAppName -replace '[^a-zA-Z0-9]', '').ToLowerInvariant()
    $suffix = -join ((48..57) + (97..122) | Get-Random -Count 6 | ForEach-Object { [char]$_ })
    $candidate = $baseName + $suffix
    $StorageAccountName = $candidate.Substring(0, [Math]::Min(24, $candidate.Length))
}

if (-not $ManagedIdentityName) {
    $ManagedIdentityName = "$FunctionAppName-github"
}

$requiredSettings = @(
    "GEMINI_API_KEY",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_WEBHOOK_SECRET",
    "ALLOWED_TELEGRAM_IDS",
    "TARGET_PERSON_NAME"
)

$missingSettings = foreach ($settingName in $requiredSettings) {
    if (-not (Get-Item -Path "Env:$settingName" -ErrorAction SilentlyContinue)) {
        $settingName
    }
}
if ($missingSettings.Count -gt 0) {
    throw "Missing required environment variables for app settings: $($missingSettings -join ', ')"
}

az account set --subscription $SubscriptionId | Out-Null

az group create `
    --name $ResourceGroupName `
    --location $Location `
    --output none

az storage account create `
    --name $StorageAccountName `
    --resource-group $ResourceGroupName `
    --location $Location `
    --sku Standard_LRS `
    --allow-blob-public-access false `
    --min-tls-version TLS1_2 `
    --output none

az functionapp create `
    --resource-group $ResourceGroupName `
    --name $FunctionAppName `
    --storage-account $StorageAccountName `
    --flexconsumption-location $Location `
    --runtime python `
    --runtime-version 3.11 `
    --output none

$wallpaperWidth = if ([string]::IsNullOrWhiteSpace($env:WALLPAPER_WIDTH)) { "1170" } else { $env:WALLPAPER_WIDTH }
$wallpaperHeight = if ([string]::IsNullOrWhiteSpace($env:WALLPAPER_HEIGHT)) { "2532" } else { $env:WALLPAPER_HEIGHT }
$fontPath = if ([string]::IsNullOrWhiteSpace($env:FONT_PATH)) { "./fonts/Inter_28pt-Light.ttf" } else { $env:FONT_PATH }

az functionapp config appsettings set `
    --resource-group $ResourceGroupName `
    --name $FunctionAppName `
    --settings `
    "AzureWebJobsFeatureFlags=EnableWorkerIndexing" `
    "PYTHON_ISOLATE_WORKER_DEPENDENCIES=1" `
    "PYTHON_ENABLE_DEBUG_LOGGING=1" `
    "GEMINI_API_KEY=$($env:GEMINI_API_KEY)" `
    "TELEGRAM_BOT_TOKEN=$($env:TELEGRAM_BOT_TOKEN)" `
    "TELEGRAM_WEBHOOK_SECRET=$($env:TELEGRAM_WEBHOOK_SECRET)" `
    "ALLOWED_TELEGRAM_IDS=$($env:ALLOWED_TELEGRAM_IDS)" `
    "TARGET_PERSON_NAME=$($env:TARGET_PERSON_NAME)" `
    "WALLPAPER_WIDTH=$wallpaperWidth" `
    "WALLPAPER_HEIGHT=$wallpaperHeight" `
    "FONT_PATH=$fontPath" `
    --output none

az identity create `
    --resource-group $ResourceGroupName `
    --name $ManagedIdentityName `
    --location $Location `
    --output none

$identity = az identity show `
    --resource-group $ResourceGroupName `
    --name $ManagedIdentityName `
    --output json | ConvertFrom-Json

$functionAppId = az functionapp show `
    --resource-group $ResourceGroupName `
    --name $FunctionAppName `
    --query id `
    --output tsv

az role assignment create `
    --assignee-object-id $identity.principalId `
    --assignee-principal-type ServicePrincipal `
    --role "Website Contributor" `
    --scope $functionAppId `
    --output none

$credentialPayload = @{
    name = "github-$GitHubBranch"
    issuer = "https://token.actions.githubusercontent.com"
    subject = "repo:$GitHubRepository:ref:refs/heads/$GitHubBranch"
    audiences = @("api://AzureADTokenExchange")
} | ConvertTo-Json -Depth 3

$credentialFile = Join-Path $env:TEMP "$FunctionAppName-federated-credential.json"
$credentialPayload | Set-Content -Path $credentialFile -Encoding ascii

az identity federated-credential create `
    --resource-group $ResourceGroupName `
    --identity-name $ManagedIdentityName `
    --name "github-$GitHubBranch" `
    --parameters $credentialFile `
    --output none

$functionHost = az functionapp show `
    --resource-group $ResourceGroupName `
    --name $FunctionAppName `
    --query defaultHostName `
    --output tsv

Write-Host ""
Write-Host "Azure resources provisioned."
Write-Host "Storage account: $StorageAccountName"
Write-Host "Function app URL: https://$functionHost"
Write-Host ""
Write-Host "Set these GitHub repository variables:"
Write-Host "AZURE_CLIENT_ID=$($identity.clientId)"
Write-Host "AZURE_TENANT_ID=$(az account show --query tenantId -o tsv)"
Write-Host "AZURE_SUBSCRIPTION_ID=$SubscriptionId"
Write-Host "AZURE_FUNCTIONAPP_NAME=$FunctionAppName"
