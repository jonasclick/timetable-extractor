# ShiftPlan to iPhone Wallpaper Generator 📱📅

Dieses Projekt automatisiert die Umwandlung von unübersichtlichen Schichtplänen (PDFs) in ein perfekt formatiertes, vertikales iPhone-Wallpaper. 

Die Pipeline nutzt ein Large Language Model (LLM), um die spezifischen Arbeitszeiten einer Person deterministisch als JSON zu extrahieren, und generiert anschliessend mithilfe von Python (`Pillow`) ein cleanes, perfekt lesbares Hintergrundbild für den Sperrbildschirm.

---

## 🚀 Features

* **Präzise Datenextraktion:** Extrahiert Teilschichten (mehrere Blöcke pro Tag) fehlerfrei aus komplexen PDF-Tabellen.
* **Deterministisches JSON-Format:** Zwingt das LLM zu einer strukturierten Ausgabe ohne störenden Fliesstext oder Markdown-Blöcke.
* **iPhone-optimiertes Layout:** Generiert ein Wallpaper im Hochformat (z. B. 1170 x 2532 px). Der obere Bereich bleibt frei für die iOS-Uhrzeit/Widgets, um visuelle Überlagerungen zu vermeiden.
* **Automatisierbar:** Perfekt geeignet, um über Apple Kurzbefehle (Shortcuts) direkt das neueste Wallpaper aus der iCloud auf den Sperrbildschirm zu laden.

---

## 🛠️ Funktionsweise

Das Projekt ist in zwei Hauptschritte unterteilt:

### 1. LLM Parsing (PDF ➡️ JSON)
Das Schichtplan-PDF (oder ein Screenshot davon) wird an ein LLM übergeben. Der System-Prompt erzwingt eine strikte JSON-Struktur, die auch Tage mit mehreren Arbeitsblöcken (durch Pausen unterbrochen) sauber in einem Array abbildet.

**Verwendeter Prompt:**
> Siehe unten.

### 2. Bildgenerierung (JSON ➡️ PNG)
Das generierte JSON wird vom Python-Skript eingelesen. Mittels der Bibliothek `Pillow` wird ein Bild mit dunklem Hintergrund erzeugt, auf dem die Tage und Schichtzeiten vertikal untereinander sauber platziert werden.

---

## 📋 Prompt inkl. JSON-Datenstruktur

Du bist ein präziser Daten-Extraktor. Extrahiere die Arbeitszeiten für die Person [Person] aus dem bereitgestellten Dienstplan. Antworte ausschliesslich im folgenden JSON-Format, ohne Markdown-Blockierung (keine ```json), ohne Einleitung und ohne Nachwort. Wenn an einem Tag keine Arbeit stattfindet, setze Zeit auf "Kein Einsatz.

Gewünschtes JSON-Format:
```json
{
  "woche": "20.04.2026 - 26.04.2026",
  "tage": [
    {
      "tag": "Montag 20.04.2026",
      "zeit": [
        "11:00 - 16:00",
        "17:00 - 21:00"
      ]
    },
    {
      "tag": "Dienstag 21.04.2026",
      "zeit": [
        "11:00 - 16:00",
        "17:00 - 21:00"
      ]
    },
    {
      "tag": "Mittwoch 22.04.2026",
      "zeit": [
        "12:00 - 16:00",
        "16:30 - 21:15"
      ]
    },
    {
      "tag": "Donnerstag 23.04.2026",
      "zeit": [
        "11:00 - 16:00",
        "17:00 - 21:00"
      ]
    },
    {
      "tag": "Freitag 24.04.2026",
      "zeit": [
        "09:00 - 13:00",
        "13:30 - 17:00",
        "17:30 - 21:15"
      ]
    },
    {
      "tag": "Samstag 25.04.2026",
      "zeit": [
        "Kein Einsatz"
      ]
    },
    {
      "tag": "Sonntag 26.04.2026",
      "zeit": [
        "Kein Einsatz"
      ]
    }
  ]
}
```

## Interface
The user interface should be a telegram bot: The user uploads the pdf to the telegram bot and the bot will return the generated jpg / png of the wallpaper.


## 🌍 Deployment & Infrastruktur (Railway)

* **Laufzeit-Infrastruktur:** Der Telegram-Bot muss **24/7 aktiv sein** und auf eingehende Nachrichten lauschen. Das Projekt wird daher auf **Railway.app** (oder einer vergleichbaren PaaS wie Render) als dauerhafter Hintergrunddienst gehostet.
* **Bot-Mechanismus:** Der Bot nutzt einfaches **Polling** (`updater.start_polling()`), um Updates von den Telegram-Servern abzurufen. Dies vereinfacht das lokale Testen und benötigt keine feste Webhook-URL mit HTTPS-Zertifikats-Handling auf Railway.
* **Rolle von GitHub Actions:** GitHub Actions wird **nicht** für das Ausführen des Bots genutzt (da Jobs nach max. 6 Stunden abbrechen). Es dient exklusiv als CI/CD-Pipeline, um bei einem `push` das Deployment auf Railway zu triggern.

---

## 📁 Schriftarten & Assets (Font Handling)

Da Linux-Serverumgebungen (wie die Container auf Railway) standardmäßig keine iOS-typischen oder visuell ansprechenden TrueType-Schriften vorinstalliert haben, gilt folgende Konvention:
* Im Repository existiert ein Ordner `/fonts` (z. B. mit einer lizenzfreien `.ttf`-Datei wie *Inter* oder *Roboto*).
* Pillow greift beim Zeichnen des Textes direkt auf diesen relativen Pfad zu, um plattformunabhängig ein identisches Schriftbild zu garantieren.



## 🔑 Umgebungsvariablen (.env Konfiguration)

Die `.env`-Datei hält das Repository komplett frei von Secrets und hardcodierten Layout-Werten. Folgende Struktur ist zwingend erforderlich:

```env
# API-Schlüssel & Tokens
GEMINI_API_KEY=AIzaSy...
TELEGRAM_BOT_TOKEN=1234567890:ABC...

# Extraktions-Ziel
TARGET_PERSON_NAME="Max Mustermann"

# Wallpaper-Spezifikationen (iPhone-Optimierung)
WALLPAPER_WIDTH=1170
WALLPAPER_HEIGHT=2532

# Asset-Pfade
FONT_PATH="./fonts/Your-Selected-Font.ttf"

# Laufzeit-Modus (production / development)
ENV_MODE=production
```


# Context

---

## Verwendete Technologien (Tech Stack)

Für dein Python-Skript kommen im Kern drei bewährte Open-Source- bzw. cloudbasierte Komponenten zum Einsatz, die perfekt ineinandergreifen:

* **`google-genai` (Das offizielle Google SDK):** Dies ist die native Bibliothek von Google, um direkt mit den Gemini-Modellen zu kommunizieren. Sie übernimmt im Hintergrund das HTTP-Handling, das Datei-Streaming (File API) für dein PDF und die sichere Authentifizierung über deinen API-Schlüssel.
* **Pydantic (Datenvalidierung & Typisierung):** Pydantic ist der Industriestandard in Python, um Datenstrukturen zu definieren. Anstatt dem LLM einfach nur Freitext zu entlocken, liest Gemini das Pydantic-Schema aus, validiert die extrahierten Daten dagegen und liefert dir ein garantiertes, sauberes JSON-Objekt zurück.
* **Gemini 2.5 Flash (Das KI-Modell):** Ein sogenanntes "multimodales" Modell. Das bedeutet strategisch für dich: Es kann Text, Bilder und Dokumente nativ ohne vorgeschaltete OCR-Software (wie Tesseract) verarbeiten. Es analysiert das PDF direkt als visuelles Dokument, was Fehler bei Tabellen oder komplexen Layouts drastisch reduziert.

---

## Projektstrategie & Workflow

Damit dein Skript stabil läuft und du nicht in die Ratenbegrenzung (Rate Limits) läufst, empfiehlt sich eine **Batch-Processing-Strategie** (schrittweise Verarbeitung in einer Schleife).

Der Ablauf für dein Skript sieht strategisch so aus:

```
[Lokales PDF] ──> [Google File API Upload] ──> [Gemini 2.5 Flash + Pydantic Schema]
                                                               │
[Lokales JSON / DB] <── [Google File API Delete] <── [Strukturiertes JSON-Ergebnis]

```

### Die Kernschritte im Detail:

1. **Upload statt Inline-Daten:** Große PDFs sollten nicht direkt als roher Text oder Base64-String in den Prompt geworfen werden. Die Strategie nutzt Googles `client.files.upload()`. Das lädt das Dokument sicher auf Googles Server hoch und übergibt dem Modell nur eine schlanke Referenz-URI.
2. **Die "Zero-Cost"-Sicherung:** Da du das Projekt komplett kostenlos betreiben willst, implementierst du nach jedem erfolgreichen Durchlauf einen automatischen Löschbefehl (`client.files.delete()`). So bleibt dein kostenloser Cloud-Speicher bei Google AI Studio immer sauber und leer.
4. **Fehlertoleranz (Robustness):** Da Netzwerkabbrüche oder kurze API-Aussetzer immer vorkommen können, verpackst du den Extraktionsschritt idealerweise in einen `try-except`-Block. Schlägt ein Dokument fehl, loggt das Skript den Fehler und macht automatisch mit dem nächsten PDF weiter, anstatt komplett abzustürzen.

Mit dieser Kombination aus dem extrem schnellen Gemini 2.5 Flash und Pydantic hast du ein produktionsreifes System gebaut, das komplett im Free Tier läuft.

---

## Projektstruktur

```
.
├── main.py                 # Telegram-Bot
├── extractor.py            # Gemini-Extraktion
├── generator.py            # Wallpaper-Rendering
├── requirements.txt
├── .env.example
├── fonts/                  # TrueType-Schrift
└── background-image/       # Optionaler Hintergrund
```
