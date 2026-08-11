import logging

logger = logging.getLogger(__name__)

WEEKLY_SCHEDULE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "tage": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "tag": {"type": "STRING"},
                    "stunden": {"type": "STRING"},
                    "zeit": {"type": "ARRAY", "items": {"type": "STRING"}},
                },
                "required": ["tag", "stunden", "zeit"],
            },
        }
    },
    "required": ["tage"],
}


def extract_shift_plan(client, file_bytes: bytes, mime_type: str, target_person: str) -> dict:
    from google.genai import types

    prompt = f"""
    Du bist ein praeziser Daten-Extraktor. Extrahiere die Arbeitszeiten fuer die Person {target_person}
    aus dem bereitgestellten Dienstplan. Antworte ausschliesslich im JSON-Format.

    WICHTIG FUER DAS DATUMSFORMAT:
    - Nutze fuer den Tag das Format "Kurztag TT. Monat" (z.B. "Mo 20. April", "Di 21. Mai").
    - Nutze Kurzformen fuer Wochentage: Mo, Di, Mi, Do, Fr, Sa, So.
    - Lass das Jahr komplett weg.

    WEITERE REGELN:
    - Wenn eine Schicht den Zusatz "Servi" traegt, fuege dies hinten an der Schichtzeit als "S" an.
      Beispiel: "9:00 - 13:00 S".
    - Extrahiere die totale Anzahl Arbeitsstunden fuer diesen Tag im Format "X.XXh".
      Wenn keine Arbeit stattfindet, setze "0h".
    - Wenn an einem Tag keine Arbeit stattfindet, setze Zeit auf ["Kein Einsatz"].
    """

    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=[
                types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                prompt,
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=WEEKLY_SCHEDULE_SCHEMA,
            ),
        )
    except Exception as exc:
        logger.error("Gemini request failed: %s", exc)
        raise

    if not response.parsed:
        logger.error("Gemini failed to parse response. Raw text: %s", response.text)
        raise ValueError("Gemini konnte die Daten nicht extrahieren.")

    return response.parsed
