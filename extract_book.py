#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import argparse
import re
from pathlib import Path
import warnings

# Unterdrücken von XML-Parsing-Warnungen von ebooklib (optional)
warnings.filterwarnings("ignore", category=UserWarning, module='ebooklib')

try:
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup
except ImportError as e:
    print(f"Fehler: Fehlende Bibliothek. Bitte installiere sie mit: pip install ebooklib beautifulsoup4")
    print(f"Details: {e}")
    sys.exit(1)


class EpubChapterExtractor:
    """
    Eine Klasse zum Extrahieren von Kapiteln aus einer EPUB-Datei in einzelne Textdateien.

    Attribute:
        epub_path (Path): Der Pfad zur EPUB-Datei.
        output_dir (Path): Das Verzeichnis, in dem die Textdateien gespeichert werden.
    """

    def __init__(self, epub_path, output_dir=None, log_callback=None, progress_callback=None):
        """
        Initialisiert den Extractor.

        Args:
            epub_path (str): Pfad zur Eingabe-EPUB-Datei.
            output_dir (str, optional): Pfad zum Ausgabeordner. Wenn None, wird ein Ordner
                                        basierend auf dem Dateinamen erstellt.
            log_callback (func, optional): Funktion zum Protokollieren von Nachrichten.
            progress_callback (func, optional): Funktion(current, total) für Fortschritt.
        """
        self.epub_path = Path(epub_path)
        self.log_callback = log_callback
        self.progress_callback = progress_callback

        if not self.epub_path.exists():
            raise FileNotFoundError(f"Die Datei '{self.epub_path}' wurde nicht gefunden.")

        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            # Erstelle einen Ordner mit dem Namen des Ebooks im gleichen Verzeichnis
            self.output_dir = self.epub_path.parent / self.epub_path.stem

    def _log(self, message):
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)

    def _sanitize_filename(self, filename):
        """
        Bereinigt einen String, damit er als Dateiname verwendet werden kann.
        Entfernt Zeichen, die in Dateisystemen nicht erlaubt sind (z.B. /, :, ?).

        Args:
            filename (str): Der gewünschte Dateiname (z.B. Kapitelüberschrift).

        Returns:
            str: Der bereinigte Dateiname.
        """
        # Ersetze ungültige Zeichen durch Unterstriche oder entferne sie
        # Windows verbietet: < > : " / \ | ? *
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        # Entferne führende/nachfolgende Leerzeichen und ersetze Tabs/Newlines
        filename = " ".join(filename.split())
        return filename[:100]  # Begrenze Länge auf 100 Zeichen

    def _html_to_text(self, html_content):
        """
        Konvertiert HTML-Inhalt in formatierten Text.
        Versucht, Absätze und Zeilenumbrüche beizubehalten.

        Args:
            html_content (bytes/str): Der HTML-Inhalt des Kapitels.

        Returns:
            str: Der extrahierte Reintext.
            str: Ein gefundener Titel (oder None).
        """
        soup = BeautifulSoup(html_content, 'html.parser')

        # Versuche, einen Titel für das Kapitel zu finden (meistens h1 oder h2)
        title_tag = soup.find(['h1', 'h2', 'title'])
        chapter_title = title_tag.get_text(strip=True) if title_tag else None

        # Formatierung beibehalten:
        # Ersetze <br> durch newline
        for br in soup.find_all("br"):
            br.replace_with("\n")

        # Ersetze Block-Elemente (p, div, h1, etc.) durch Text + Newlines,
        # damit Absätze im Textfile erkennbar bleiben.
        for tag in soup.find_all(['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']):
            tag.insert_after("\n\n")

        # Get text extrahiert den Text, strip=True entfernt überschüssige Whitespaces am Anfang/Ende
        text = soup.get_text()

        # Bereinigung von zu vielen aufeinanderfolgenden Newlines (mehr als 2)
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip(), chapter_title

    def process(self):
        """
        Führt den Extraktionsprozess aus:
        1. Lädt das Buch.
        2. Iteriert durch die Kapitel.
        3. Extrahiert Text und Titel.
        4. Speichert die Dateien.
        """
        self._log(f"Lese Buch: {self.epub_path}")
        book = epub.read_epub(self.epub_path)

        # Erstelle Ausgabeverzeichnis
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._log(f"Extrahiere Dateien nach: {self.output_dir}")

        # Zähler für Kapitel ohne klaren Titel, um Kollisionen zu vermeiden
        count = 1

        # Wir iterieren durch die Dokumente des Buches
        items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
        total_items = len(items)
        processed_count = 0

        for item in items:
            processed_count += 1
            if self.progress_callback:
                self.progress_callback(processed_count, total_items)
            
            # Wir überspringen Navigationsdateien u.ä., falls möglich,
            # aber oft enthalten Dokumente den eigentlichen Text.

            content = item.get_content()
            text, found_title = self._html_to_text(content)

            # Wenn die Datei fast leer ist, überspringen (oft leere Wrapper)
            if len(text.strip()) < 10:
                continue

            # Bestimme den Dateinamen
            if found_title:
                filename = self._sanitize_filename(found_title)
            else:
                filename = f"Kapitel_{count:03d}"

            # Dateiendung hinzufügen
            full_filename = f"{filename}.txt"

            # Überprüfen, ob Datei schon existiert (bei doppelten Kapitelnamen)
            output_file = self.output_dir / full_filename
            dup_counter = 1
            while output_file.exists():
                full_filename = f"{filename}_{dup_counter}.txt"
                output_file = self.output_dir / full_filename
                dup_counter += 1

            # Speichern
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(text)

            self._log(f"Gespeichert: {full_filename}")
            count += 1

        self._log("\nExtraktion abgeschlossen.")


def main():
    """
    Haupteinstiegspunkt für das Skript.
    Verarbeitet Kommandozeilenargumente.
    """
    parser = argparse.ArgumentParser(
        description="Extrahiert Kapitel aus einer EPUB-Datei in separate Textdateien."
    )
    parser.add_argument(
        "epub_datei",
        help="Der Pfad zur .epub Eingabedatei."
    )
    parser.add_argument(
        "-o", "--output",
        help="Optional: Zielordner für die Textdateien.",
        default=None
    )

    args = parser.parse_args()

    try:
        extractor = EpubChapterExtractor(args.epub_datei, args.output)
        extractor.process()
    except Exception as e:
        print(f"Ein Fehler ist aufgetreten: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
