#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import json
import time
import os
import traceback
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QFileDialog, QTextEdit, 
    QProgressBar, QGroupBox, QFormLayout, QSpinBox, QMessageBox,
    QSplitter
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject

# Importiere Backend-Logik
# Wir gehen davon aus, dass die Dateien im selben Verzeichnis liegen
try:
    from extract_book import EpubChapterExtractor
    from translate_book import KimiTranslator
    from create_open_document import OdtMerger
except ImportError as e:
    print(f"Fehler beim Importieren der Module: {e}")
    print("Bitte stellen Sie sicher, dass extract_book.py, translate_book.py und create_open_document.py im selben Verzeichnis sind.")
    sys.exit(1)


# ==========================================
# Worker Thread (Hintergrundprozess)
# ==========================================

class WorkerSignals(QObject):
    progress = pyqtSignal(int, int, str) # current, total, status_text
    log = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

class Worker(QThread):
    def __init__(self, epub_path, output_dir, api_key, base_url, model_name, workers):
        super().__init__()
        self.epub_path = Path(epub_path)
        self.output_dir = Path(output_dir)
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.workers = workers
        self.signals = WorkerSignals()
        self.is_running = True

    def log_message(self, message):
        self.signals.log.emit(message)
        if self.log_file:
            try:
                # Einfaches Schreiben in die Logdatei
                self.log_file.write(message + "\n")
                self.log_file.flush()
            except Exception:
                pass

    def report_progress(self, current, total, stage=""):
        self.signals.progress.emit(current, total, stage)

    def run(self):
        self.log_file = None
        try:
            # Logdatei erstellen
            self.output_dir.mkdir(parents=True, exist_ok=True)
            log_path = self.output_dir / "process_log.txt"
            self.log_file = open(log_path, "a", encoding="utf-8")
            self.log_file.write(f"\n\n=== NEUER START: {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
            
            self.log_message(f"=== STARTE PROZESS ===")
            self.log_message(f"Datei: {self.epub_path}")
            self.log_message(f"Ziel: {self.output_dir}")
            
            # 1. Extrahieren
            self.log_message("\n--- Phase 1: Extraktion ---")
            
            # Callback Wrapper für Extraktor
            def extract_progress(current, total):
                if not self.is_running: raise Exception("Vom Benutzer abgebrochen.")
                self.report_progress(current, total, f"Extrahiere Kapitel {current}/{total}")

            extractor = EpubChapterExtractor(
                self.epub_path, 
                self.output_dir, 
                log_callback=self.log_message,
                progress_callback=extract_progress
            )
            extractor.process()

            if not self.is_running: return

            # 2. Übersetzen
            self.log_message("\n--- Phase 2: Übersetzung ---")
            
            # Callback Wrapper für Translator
            def translate_progress(current, total):
                if not self.is_running: raise Exception("Vom Benutzer abgebrochen.")
                self.report_progress(current, total, f"Übersetze Datei {current}/{total}")

            translator = KimiTranslator(
                input_dir=extractor.output_dir, # Nutze das Verzeichnis vom Extractor
                api_key=self.api_key,
                base_url=self.base_url,
                model_name=self.model_name,
                max_workers=self.workers,
                log_callback=self.log_message,
                progress_callback=translate_progress
            )
            translator.process_files()

            if not self.is_running: return

            # 3. Zusammenfügen
            self.log_message("\n--- Phase 3: Erstellen des Dokuments ---")
            
            output_odt = extractor.output_dir / f"{self.epub_path.stem}_DE.odt"
            
            # Callback Wrapper für Merger
            def merge_progress(current, total):
                 if not self.is_running: raise Exception("Vom Benutzer abgebrochen.")
                 self.report_progress(current, total, f"Füge Datei {current}/{total} hinzu")

            merger = OdtMerger(
                input_dir=extractor.output_dir,
                output_file=output_odt,
                log_callback=self.log_message,
                progress_callback=merge_progress
            )
            merger.process()

            self.log_message("\n=== FERTIG ===")
            self.signals.finished.emit()

        except Exception as e:
            if str(e) == "Vom Benutzer abgebrochen.":
                 self.log_message("\n!!! ABBRUCH DURCH BENUTZER !!!")
            else:
                self.log_message(f"\n!!! FEHLER: {e} !!!")
                self.log_message(traceback.format_exc())
                self.signals.error.emit(str(e))
    
    def stop(self):
        self.is_running = False


# ==========================================
# GUI Application
# ==========================================

CONFIG_FILE = Path.home() / ".epub_translator_config.json"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("AI Ebook Translator")
        self.resize(900, 750)
        
        # Default Config
        self.config = {
            "api_key": "",
            "base_url": "https://api.moonshot.ai/v1",
            "model_name": "kimi-k2.5",
            "workers": 3,
            "last_epub_dir": str(Path.home()),
            "last_output_dir": str(Path.home())
        }
        self.load_config()

        self.worker = None

        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- Logo ---
        # Image Pfad relativ zum Skript finden
        script_dir = Path(__file__).parent.absolute()
        image_path = script_dir / "Gemini_Generated_Image_e5xbase5xbase5xb.png"
        
        if image_path.exists():
            from PyQt6.QtGui import QPixmap
            logo_label = QLabel()
            pixmap = QPixmap(str(image_path))
            # Skalieren auf eine vernünftige Höhe, z.B. 200px
            scaled_pixmap = pixmap.scaledToHeight(200, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            main_layout.addWidget(logo_label)
        else:
            print(f"Warnung: Bild nicht gefunden unter {image_path}")

        # --- Header ---
        header_label = QLabel("AI Ebook Translator")
        header_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(header_label)

        # --- Input Section ---
        input_group = QGroupBox("Dateien")
        input_layout = QFormLayout()
        
        # EPUB Datei
        self.epub_path_edit = QLineEdit()
        self.epub_path_edit.setPlaceholderText("Bitte EPUB Datei wählen...")
        self.epub_browse_btn = QPushButton("Durchsuchen...")
        self.epub_browse_btn.clicked.connect(self.browse_epub)
        
        epub_row = QHBoxLayout()
        epub_row.addWidget(self.epub_path_edit)
        epub_row.addWidget(self.epub_browse_btn)
        input_layout.addRow("E-Book (.epub):", epub_row)

        # Ausgabe Verzeichnis
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("Standard: Gleicher Ordner wie Datei")
        self.output_browse_btn = QPushButton("Durchsuchen...")
        self.output_browse_btn.clicked.connect(self.browse_output)

        out_row = QHBoxLayout()
        out_row.addWidget(self.output_dir_edit)
        out_row.addWidget(self.output_browse_btn)
        input_layout.addRow("Zielordner (Optional):", out_row)

        input_group.setLayout(input_layout)
        main_layout.addWidget(input_group)

        # --- Settings Section ---
        settings_group = QGroupBox("AI Konfiguration")
        settings_layout = QFormLayout()

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setText(self.config.get("api_key", ""))
        self.api_key_edit.setPlaceholderText("sk-...")
        settings_layout.addRow("API Key:", self.api_key_edit)

        self.base_url_edit = QLineEdit()
        self.base_url_edit.setText(self.config.get("base_url", "https://api.moonshot.ai/v1"))
        settings_layout.addRow("Base URL:", self.base_url_edit)

        self.model_edit = QLineEdit()
        self.model_edit.setText(self.config.get("model_name", "kimi-k2.5"))
        settings_layout.addRow("Model Name:", self.model_edit)

        self.workers_spin = QSpinBox()
        self.workers_spin.setRange(1, 10)
        self.workers_spin.setValue(self.config.get("workers", 3))
        settings_layout.addRow("Parallele Worker:", self.workers_spin)

        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)

        # --- Control Section ---
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("Übersetzung Starten")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.start_btn.clicked.connect(self.start_process)
        
        self.stop_btn = QPushButton("Abbrechen")
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_process)

        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        main_layout.addLayout(btn_layout)

        # --- Progress & Log ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Bereit")
        main_layout.addWidget(self.status_label)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("font-family: monospace; font-size: 10pt;")
        main_layout.addWidget(self.log_view)

    def browse_epub(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "E-Book auswählen", 
            self.config.get("last_epub_dir"), 
            "EPUB Files (*.epub)"
        )
        if file_path:
            self.epub_path_edit.setText(file_path)
            self.config["last_epub_dir"] = str(Path(file_path).parent)
            self.save_config()

    def browse_output(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, 
            "Zielordner auswählen",
            self.config.get("last_output_dir")
        )
        if dir_path:
            self.output_dir_edit.setText(dir_path)
            self.config["last_output_dir"] = dir_path
            self.save_config()

    def start_process(self):
        epub_path = self.epub_path_edit.text()
        output_dir = self.output_dir_edit.text()
        api_key = self.api_key_edit.text()
        base_url = self.base_url_edit.text()
        model_name = self.model_edit.text()
        workers = self.workers_spin.value()

        if not epub_path or not os.path.exists(epub_path):
            QMessageBox.warning(self, "Fehler", "Bitte eine gültige EPUB Datei auswählen.")
            return

        if not api_key:
            QMessageBox.warning(self, "Fehler", "Bitte einen API Key eingeben.")
            return
            
        # Wenn kein Output Dir angegeben, nimm Parent vom EPUB
        if not output_dir:
            output_dir = str(Path(epub_path).parent)

        # Config speichern
        self.config.update({
            "api_key": api_key,
            "base_url": base_url,
            "model_name": model_name,
            "workers": workers
        })
        self.save_config()

        # UI Updates
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.log_view.clear()
        self.progress_bar.setValue(0)
        self.status_label.setText("Starte...")
        
        # Worker starten
        self.worker = Worker(epub_path, output_dir, api_key, base_url, model_name, workers)
        self.worker.signals.log.connect(self.append_log)
        self.worker.signals.progress.connect(self.update_progress)
        self.worker.signals.finished.connect(self.process_finished)
        self.worker.signals.error.connect(self.process_error)
        
        self.worker.start()

    def stop_process(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.status_label.setText("Wird abgebrochen...")
            self.stop_btn.setEnabled(False)

    def append_log(self, text):
        self.log_view.append(text)
        # Auto-Scroll
        sb = self.log_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def update_progress(self, current, total, status_text):
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)
        self.status_label.setText(f"{status_text} ({current}/{total})")

    def process_finished(self):
        self.status_label.setText("Abgeschlossen.")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        QMessageBox.information(self, "Erfolg", "Der Vorgang wurde erfolgreich abgeschlossen.")

    def process_error(self, error_msg):
        self.status_label.setText("Fehler aufgetreten.")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        QMessageBox.critical(self, "Fehler", f"Ein Fehler ist aufgetreten:\n{error_msg}")

    def load_config(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    self.config.update(data)
            except Exception as e:
                print(f"Konnte Config nicht laden: {e}")

    def save_config(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Konnte Config nicht speichern: {e}")


def main():
    app = QApplication(sys.argv)
    
    # Style
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
