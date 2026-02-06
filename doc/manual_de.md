# AI Ebook Translator - Benutzerhandbuch

![Logo](../Gemini_Generated_Image_e5xbase5xbase5xb.png)

Willkommen beim **AI Ebook Translator**. Diese Anwendung ermöglicht es Ihnen, E-Books (im `.epub`-Format) mithilfe moderner KI automatisch ins Deutsche zu übersetzen.

## Schnellstart

### 1. Installation

Stellen Sie sicher, dass alle Abhängigkeiten installiert sind:

```bash
# In Ihrem Terminal:
pip install PyQt6 openai ebooklib beautifulsoup4 odfpy pyinstaller
```

### 2. Programm starten

Sie können das Programm direkt über Python starten:

```bash
python3 gui_app.py
```

Oder, falls Sie eine ausführbare Datei erstellt haben, per Doppelklick auf die Programmdatei.

## Bedienung

### Schritt 1: Konfiguration

Beim ersten Start müssen Sie Ihre KI-Einstellungen vornehmen. Diese finden Sie im Bereich **"AI Konfiguration"**:

*   **API Key**: Hier tragen Sie Ihren API-Schlüssel ein (z.B. von OpenAI oder Moonshot AI).
*   **Base URL**: Die Adresse der API. Standardmäßig ist Moonshot AI eingestellt (`https://api.moonshot.ai/v1`).
*   **Model Name**: Das zu verwendende KI-Modell (z.B. `kimi-k2.5`).
*   **Parallele Worker**: Anzahl der Dateien, die gleichzeitig übersetzt werden sollen. Ein Wert von 3 ist meist optimal.

*Die Einstellungen werden automatisch gespeichert.*

### Schritt 2: Dateien auswählen

1.  Klicken Sie bei **"E-Book (.epub)"** auf "Durchsuchen...", um Ihr Buch auszuwählen.
2.  (Optional) Wählen Sie unter **"Zielordner"** einen Speicherort für die übersetzten Dateien. Wenn Sie nichts auswählen, wird im Ordner des Buches ein neuer Unterordner erstellt.

### Schritt 3: Übersetzung starten

Klicken Sie auf den grünen Button **"Übersetzung Starten"**.

Das Programm führt nun folgende Schritte automatisch aus:
1.  **Extraktion**: Das E-Book wird in einzelne Kapitel zerlegt.
2.  **Übersetzung**: Jedes Kapitel wird von der KI übersetzt.
3.  **Zusammenfügen**: Die übersetzten Texte werden zu einem neuen Dokument (`.odt` für OpenOffice/LibreOffice/Word) zusammengefügt.

## Überwachung & Fehlerbehebung

*   **Verlauf**: Im unteren Fenster sehen Sie genau, was das Programm gerade macht.
*   **Fortschritt**: Der blaue Balken zeigt den Gesamtfortschritt an.
*   **Abbruch**: Sie können den Vorgang jederzeit mit "Abbrechen" stoppen.

### Was passiert bei Fehlern?
*   Falls die Übersetzung einer Datei fehlschlägt, wird eine "Failure"-Datei erstellt (z.B. `Kapitel_05_FAILURE_DE.txt`).
*   Das Programm macht mit den anderen Dateien weiter.
*   Es wird eine **Log-Datei** (`process_log.txt`) im Zielordner erstellt. Dort können Sie bei Problemen nachsehen, was passiert ist.
*   Sie können die Übersetzung einfach erneut starten (im selben Zielordner). Das Programm erkennt bereits übersetzte Dateien (`*_DE.txt`) und überspringt diese, sodass Sie nicht noch einmal dafür bezahlen müssen.

## Systemvoraussetzungen

*   **Betriebssystem**: Linux, Windows oder macOS.
*   **Python**: Version 3.8 oder neuer.
*   **Internetverbindung**: Für die Verbindung zur KI-API erforderlich.
