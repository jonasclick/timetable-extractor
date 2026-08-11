import logging
import os
from typing import Any

import azure.functions as func
import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
ALLOWED_TELEGRAM_IDS = {
    int(raw_id.strip())
    for raw_id in os.getenv("ALLOWED_TELEGRAM_IDS", "").split(",")
    if raw_id.strip()
}
TARGET_PERSON_NAME = os.getenv("TARGET_PERSON_NAME", "Max Mustermann")
WALLPAPER_WIDTH = int(os.getenv("WALLPAPER_WIDTH", "1170"))
WALLPAPER_HEIGHT = int(os.getenv("WALLPAPER_HEIGHT", "2532"))
FONT_PATH = os.getenv("FONT_PATH", "./fonts/Inter_28pt-Light.ttf")
REQUEST_TIMEOUT_SECONDS = 60

client = None


def is_authorized(user_id: int | None) -> bool:
    if user_id is None:
        return False
    return not ALLOWED_TELEGRAM_IDS or user_id in ALLOWED_TELEGRAM_IDS


def telegram_api(
    method: str,
    *,
    data: dict[str, Any] | None = None,
    files: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}",
        data=data,
        files=files,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        raise RuntimeError(f"Telegram API error calling {method}: {payload}")
    return payload


def send_text(chat_id: int, text: str) -> int:
    payload = telegram_api("sendMessage", data={"chat_id": str(chat_id), "text": text})
    return payload["result"]["message_id"]


def edit_text(chat_id: int, message_id: int, text: str) -> None:
    telegram_api(
        "editMessageText",
        data={"chat_id": str(chat_id), "message_id": str(message_id), "text": text},
    )


def delete_message(chat_id: int, message_id: int) -> None:
    telegram_api(
        "deleteMessage",
        data={"chat_id": str(chat_id), "message_id": str(message_id)},
    )


def send_photo(chat_id: int, image_bytes: bytes, caption: str) -> None:
    telegram_api(
        "sendPhoto",
        data={"chat_id": str(chat_id), "caption": caption},
        files={"photo": ("wallpaper.png", image_bytes, "image/png")},
    )


def get_file_bytes(file_id: str) -> tuple[bytes, str]:
    file_info = telegram_api("getFile", data={"file_id": file_id})
    file_path = file_info["result"].get("file_path")
    if not file_path:
        raise ValueError("Telegram returned no file_path for the uploaded file.")

    response = requests.get(
        f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}",
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.content, file_path


def extract_attachment(message: dict[str, Any]) -> tuple[str, str] | None:
    document = message.get("document")
    if document:
        return document["file_id"], document.get("mime_type", "application/octet-stream")

    photos = message.get("photo") or []
    if photos:
        return photos[-1]["file_id"], "image/jpeg"

    return None


def ensure_runtime_configuration() -> None:
    global client

    missing = []
    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")

    if missing:
        raise RuntimeError(f"Missing runtime configuration: {', '.join(missing)}")

    if client is None:
        from google import genai

        client = genai.Client(api_key=GEMINI_API_KEY)


def process_update(update: dict[str, Any]) -> None:
    message = update.get("message")
    if not message:
        logger.info("Ignoring unsupported update type.")
        return

    chat = message.get("chat") or {}
    from_user = message.get("from") or {}
    chat_id = chat.get("id")
    user_id = from_user.get("id")
    text = message.get("text", "")

    if not chat_id:
        logger.info("Ignoring update without chat id.")
        return

    if not is_authorized(user_id):
        send_text(chat_id, "You are not a registered user for this service.")
        return

    if text == "/start":
        send_text(chat_id, f"Hallo! Sende mir einen Schichtplan fuer {TARGET_PERSON_NAME}.")
        return

    attachment = extract_attachment(message)
    if not attachment:
        logger.info("Ignoring message without supported attachment.")
        return

    file_id, mime_type = attachment
    status_message_id = send_text(chat_id, "Verarbeite Schichtplan...")

    try:
        from extractor import extract_shift_plan
        from generator import generate_wallpaper

        file_bytes, file_path = get_file_bytes(file_id)
        logger.info("Downloaded Telegram file: %s", file_path)
        schedule = extract_shift_plan(client, file_bytes, mime_type, TARGET_PERSON_NAME)
        wallpaper_buffer = generate_wallpaper(
            schedule,
            WALLPAPER_WIDTH,
            WALLPAPER_HEIGHT,
            FONT_PATH,
        )
        delete_message(chat_id, status_message_id)
        send_photo(chat_id, wallpaper_buffer.getvalue(), "Hier ist dein Wallpaper.")
    except Exception as exc:
        logger.exception("Schedule processing failed: %s", exc)
        edit_text(chat_id, status_message_id, f"Fehler: {exc}")


@app.function_name(name="health_check")
@app.route(route="health", methods=["GET"])
def health(_: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse("ok", status_code=200)


@app.function_name(name="telegram_webhook_handler")
@app.route(route="telegram/webhook", methods=["POST"])
def telegram_webhook(req: func.HttpRequest) -> func.HttpResponse:
    if TELEGRAM_WEBHOOK_SECRET:
        received_secret = req.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if received_secret != TELEGRAM_WEBHOOK_SECRET:
            logger.warning("Rejected webhook request with invalid secret token.")
            return func.HttpResponse("forbidden", status_code=403)

    try:
        update = req.get_json()
    except ValueError:
        return func.HttpResponse("invalid json", status_code=400)

    try:
        ensure_runtime_configuration()
        process_update(update)
    except Exception as exc:
        logger.exception("Failed to process Telegram update: %s", exc)
        return func.HttpResponse("processing error", status_code=500)

    return func.HttpResponse("ok", status_code=200)
