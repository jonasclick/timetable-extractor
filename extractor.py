import logging
from google.genai import types

logger = logging.getLogger(__name__)

# JSON Schema for Gemini (no classes needed)
WEEKLY_SCHEDULE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "woche": {"type": "STRING"},
        "tage": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "tag": {"type": "STRING"},
                    "zeit": {"type": "ARRAY", "items": {"type": "STRING"}}
                },
                "required": ["tag", "zeit"]
            }
        }
    },
    "required": ["woche", "tage"]
}

async def extract_shift_plan(client, file_bytes: bytes, mime_type: str, target_person: str) -> dict:
    """Extracts shift plan data using Gemini 3.5 Flash without Pydantic classes."""
    prompt = f"""
    Du bist ein präziser Daten-Extraktor. Extrahiere die Arbeitszeiten für die Person {target_person} aus dem bereitgestellten Dienstplan. 
    Antworte ausschliesslich im JSON-Format.
    Wenn an einem Tag keine Arbeit stattfindet, setze Zeit auf ["Kein Einsatz"].
    Die Woche sollte im Format "TT.MM.JJJJ - TT.MM.JJJJ" angegeben werden.
    Jeder Tag sollte im Format "Wochentag TT.MM.JJJJ" (z.B. Montag 20.04.2026) angegeben werden.
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=[
                types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                prompt
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=WEEKLY_SCHEDULE_SCHEMA,
            )
        )
        
        # response.parsed will be a dict when response_schema is a dict
        if not response.parsed:
            logger.error(f"Gemini failed to parse. Raw text: {response.text}")
            raise ValueError("Gemini konnte die Daten nicht extrahieren.")
            
        return response.parsed
    except Exception as e:
        logger.error(f"Error in extract_shift_plan: {e}")
        raise
