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

