#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import argparse
import re
from pathlib import Path

try:
    from odf.opendocument import OpenDocumentText
    from odf.style import Style, TextProperties, ParagraphProperties
    from odf.text import H, P, Span
except ImportError:
    print("Fehler: Die Bibliothek 'odfpy' fehlt.")
    print("Bitte installiere sie mit: pip install odfpy")
    sys.exit(1)


class OdtMerger:
    """
    Klasse zum Zusammenfügen von Textdateien in ein OpenDocument (.odt)
    mit automatischen Seitenumbrüchen zwischen den Dateien.
    """

    def __init__(self, input_dir, output_file, log_callback=None, progress_callback=None):
        """
        Initialisiert den Merger.

        Args:
            input_dir (str): Verzeichnis mit den .txt Dateien.
            output_file (str): Pfad zur Ausgabedatei (.odt).
        """
        self.input_dir = Path(input_dir)
        self.output_file = Path(output_file)
        self.log_callback = log_callback
        self.progress_callback = progress_callback

        if not self.input_dir.exists():
            raise FileNotFoundError(f"Verzeichnis nicht gefunden: {self.input_dir}")

        # Das ODT-Dokument erstellen
        self.doc = OpenDocumentText()

        # Styles vorbereiten
        self._create_styles()

    def _log(self, message):
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)

    def _create_styles(self):
        """
        Definiert die Formatvorlagen für das Dokument, insbesondere
        den Style für Überschriften mit erzwungenem Seitenumbruch.
        """
        # 1. Style für die Kapitelüberschrift (H1) mit Seitenumbruch DAVOR
        self.h1_break_style = Style(name="HeadingWithBreak", family="paragraph")

        # breakbefore="page" erzwingt den Umbruch
        self.h1_break_style.addElement(ParagraphProperties(breakbefore="page"))

        # Schriftart groß und fett für Überschrift
        self.h1_break_style.addElement(TextProperties(fontweight="bold", fontsize="18pt"))

        # Style zum Dokument hinzufügen
        self.doc.automaticstyles.addElement(self.h1_break_style)

        # 2. Standard Text-Absatz Style (optional, für saubere Formatierung)
        self.para_style = Style(name="StandardParagraph", family="paragraph")
        self.para_style.addElement(ParagraphProperties(marginbottom="0.2cm"))
        self.doc.automaticstyles.addElement(self.para_style)

    def _natural_sort_key(self, path):
        """
        Hilfsfunktion für natürliche Sortierung (z.B. damit 'Kapitel 2' vor 'Kapitel 10' kommt).
        Zerlegt den Dateinamen in Text- und Zahlenblöcke.
        """
        return [int(text) if text.isdigit() else text.lower()
                for text in re.split(r'(\d+)', path.name)]

    def process(self):
        """
        Liest die Dateien, fügt sie hinzu und speichert das ODT.
        """
        # Suche nur nach den erfolgreich übersetzten deutschen Dateien
        files = list(self.input_dir.glob("*_DE.txt"))

        # Sortiere natürlich (wichtig bei Kapitel 1, 2, 10...)
        files.sort(key=self._natural_sort_key)

        if not files:
            self._log("Keine Dateien mit der Endung '_DE.txt' gefunden.")
            return

        total_files = len(files)
        self._log(f"Füge {total_files} Dateien zusammen...")

        for index, file_path in enumerate(files):
            self._log(f" -> Verarbeite: {file_path.name}")
            
            if self.progress_callback:
                self.progress_callback(index + 1, total_files)

            # Titel aus dem Dateinamen ableiten (ohne _DE.txt)
            chapter_title = file_path.name.replace("_DE.txt", "").replace("_", " ")

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Füge die Kapitelüberschrift hinzu
            # Beim allerersten Kapitel brauchen wir vielleicht keinen Seitenumbruch,
            # aber für Konsistenz wenden wir den Style meistens ab dem zweiten an.
            # Hier wenden wir ihn immer an (erste Seite ist eh leer/neu).
            h = H(outlinelevel=1, stylename=self.h1_break_style, text=chapter_title)
            self.doc.text.addElement(h)

            # Füge den Inhalt Absatz für Absatz hinzu
            lines = content.splitlines()
            for line in lines:
                # Leere Zeilen ignorieren oder als leeren Absatz einfügen?
                # Wir fügen sie hinzu, wenn sie nicht komplett leer sind, um Formatierung zu wahren.
                if line.strip():
                    p = P(stylename=self.para_style, text=line)
                    self.doc.text.addElement(p)
                else:
                    # Optional: Leere Absätze für Abstände im Text
                     self.doc.text.addElement(P(stylename=self.para_style))

        # Speichern
        self.doc.save(self.output_file)
        self._log(f"\nErfolg! Buch gespeichert unter: {self.output_file}")


def main():
    parser = argparse.ArgumentParser(description="Fügt Textdateien zu einem ODT-Dokument zusammen.")
    parser.add_argument("ordner", help="Pfad zum Ordner mit den '_DE.txt' Dateien.")
    parser.add_argument("-o", "--output", help="Name der Ausgabedatei.", default="Mein_Uebersetztes_Buch.odt")

    args = parser.parse_args()

    try:
        merger = OdtMerger(args.ordner, args.output)
        merger.process()
    except Exception as e:
        print(f"Ein Fehler ist aufgetreten: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
