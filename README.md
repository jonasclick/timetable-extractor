# Timetable Extractor

This app receives a shift plan in Telegram and replies with an iPhone wallpaper that shows the extracted shifts.

The architecture is now serverless:

- Telegram sends updates to an Azure Functions HTTP webhook.
- The function downloads the uploaded document or image from Telegram.
- Gemini extracts the shifts as structured JSON.
- Pillow renders the wallpaper.
- The function sends the generated image back to the same Telegram chat.

## Architecture

```text
Telegram -> Azure Function webhook -> Gemini extraction -> Wallpaper render -> Telegram reply
```

This removes the need for a permanently running container and is a much better fit for 1-2 requests per week.

## Project Structure

```text
.
|-- function_app.py
|-- extractor.py
|-- generator.py
|-- requirements.txt
|-- host.json
|-- local.settings.json
|-- .env.example
|-- scripts/
|   |-- provision-azure.ps1
|   `-- set-telegram-webhook.ps1
|-- fonts/
`-- background-image/
```

## Local Development

Prerequisites:

- Python 3.12
- Azure Functions Core Tools v4
- Azure CLI

Install dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Configure `local.settings.json` or a local `.env` file:

```env
GEMINI_API_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_WEBHOOK_SECRET=
AzureWebJobsFeatureFlags=EnableWorkerIndexing
PYTHON_ISOLATE_WORKER_DEPENDENCIES=1
PYTHON_ENABLE_DEBUG_LOGGING=1
ALLOWED_TELEGRAM_IDS=12345678,87654321
TARGET_PERSON_NAME=Max Mustermann
WALLPAPER_WIDTH=1170
WALLPAPER_HEIGHT=2532
FONT_PATH=./fonts/Inter_28pt-Light.ttf
```

Start the function app:

```powershell
func start
```

The local webhook endpoint is:

```text
http://localhost:7071/api/telegram/webhook
```

## Azure Provisioning

The script [scripts/provision-azure.ps1](C:\dev\timetable-extractor\scripts\provision-azure.ps1) creates:

- Resource Group
- Storage Account
- Function App on the Flex Consumption plan
- User-assigned managed identity for GitHub OIDC
- Federated credential for the `main` branch
- Required app settings
- Python worker indexing and dependency isolation settings

Example:

```powershell
$env:GEMINI_API_KEY="..."
$env:TELEGRAM_BOT_TOKEN="..."
$env:TELEGRAM_WEBHOOK_SECRET="..."
$env:ALLOWED_TELEGRAM_IDS="12345678,87654321"
$env:TARGET_PERSON_NAME="Max Mustermann"

.\scripts\provision-azure.ps1 `
  -SubscriptionId "<subscription-id>" `
  -ResourceGroupName "prod-rg-timetable-extractor" `
  -FunctionAppName "timetable-extractor-func" `
  -Location "switzerlandnorth" `
  -GitHubRepository "jonasclick/timetable-extractor"
```

## Telegram Webhook Setup

After the first deployment:

```powershell
.\scripts\set-telegram-webhook.ps1 `
  -BotToken "<telegram-bot-token>" `
  -FunctionBaseUrl "https://<app-name>.azurewebsites.net" `
  -SecretToken "<same-secret-as-app-setting>"
```

## CI/CD

GitHub Actions deploys the app on every push to `main`.

The workflow expects these GitHub repository variables:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`
- `AZURE_FUNCTIONAPP_NAME`

Optional:

- `AZURE_FUNCTIONAPP_PACKAGE_PATH`

The Azure side for OIDC is created by the provisioning script. The GitHub repository variables still need to be set in GitHub.
