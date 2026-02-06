import glob
import sys
import argparse
from pathlib import Path
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed

class KimiTranslator:
    def __init__(self, input_dir, api_key, base_url="https://api.moonshot.ai/v1", 
                 model_name="kimi-k2.5", max_workers=3, 
                 system_prompt=None, log_callback=None, progress_callback=None):
        self.input_dir = Path(input_dir)
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.max_workers = max_workers
        self.log_callback = log_callback
        self.progress_callback = progress_callback # Funktion(current, total)

        if not self.input_dir.exists():
            raise FileNotFoundError(f"Verzeichnis nicht gefunden: {self.input_dir}")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

        self.system_prompt = system_prompt
        if not self.system_prompt:
             self.system_prompt = (
                "You are a professional book translator. Translate the following text "
                "from the original language into German. Maintain the original tone, style, and formatting. "
                "Output ONLY the translated text, no introductory or concluding remarks."
            )
        self.max_chunk_size = 3000

    def _log(self, message):
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)

    def _split_text_into_chunks(self, text, max_size):
        lines = text.splitlines(keepends=True)
        chunks = []
        current_chunk = []
        current_length = 0

        for line in lines:
            if current_length + len(line) > max_size:
                chunks.append("".join(current_chunk))
                current_chunk = []
                current_length = 0

            current_chunk.append(line)
            current_length += len(line)

        if current_chunk:
            chunks.append("".join(current_chunk))

        return chunks

    def _translate_chunk(self, text_chunk):
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": text_chunk}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            raise e

    def _process_single_file(self, file_path):
        """
        Diese Funktion wird parallel ausgeführt.
        """
        file_name = file_path.name
        target_file = file_path.parent / f"{file_path.stem}_DE.txt"
        failure_file = file_path.parent / f"{file_path.stem}_FAILURE_DE.txt"

        if target_file.exists():
            return f"Übersprungen (existiert): {file_name}"

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if not content.strip():
                return f"Übersprungen (leer): {file_name}"

            chunks = self._split_text_into_chunks(content, self.max_chunk_size)
            translated_parts = []

            for chunk in chunks:
                translated_text = self._translate_chunk(chunk)
                translated_parts.append(translated_text)

            full_translation = "\n".join(translated_parts)

            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(full_translation)

            return f"ERFOLG: {file_name}"

        except Exception as e:
            try:
                with open(file_path, 'r', encoding='utf-8') as f_src:
                    original_content = f_src.read()
                with open(failure_file, 'w', encoding='utf-8') as f_dest:
                    f_dest.write(original_content)
                return f"FEHLER (Original kopiert): {file_name} -> {e}"
            except Exception as io_e:
                return f"KRITISCHER FEHLER: {file_name} -> {io_e}"

    def process_files(self):
        files = list(self.input_dir.glob("*.txt"))

        # Filter
        files_to_process = [
            f for f in files
            if not f.name.endswith("_DE.txt") and not f.name.endswith("_FAILURE_DE.txt")
        ]

        total_files = len(files_to_process)
        self._log(f"Starte parallele Übersetzung für {total_files} Dateien mit {self.max_workers} Workern...")

        if total_files == 0:
            return

        completed_count = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {
                executor.submit(self._process_single_file, f): f
                for f in files_to_process
            }

            for future in as_completed(future_to_file):
                result_message = future.result()
                self._log(result_message)
                
                completed_count += 1
                if self.progress_callback:
                    self.progress_callback(completed_count, total_files)

def main():
    parser = argparse.ArgumentParser(description="Übersetzt Textdateien parallel mit Kimi.")
    parser.add_argument("ordner", help="Pfad zum Ordner mit den extrahierten Textdateien.")
    parser.add_argument("--api_key", required=True, help="Der API Key.")
    parser.add_argument("--base_url", default="https://api.moonshot.ai/v1", help="Basis URL der API.")
    parser.add_argument("--model", default="kimi-k2.5", help="Modellname.")
    parser.add_argument("--workers", type=int, default=3, help="Anzahl Arbeiter.")
    
    args = parser.parse_args()

    try:
        translator = KimiTranslator(
            input_dir=args.ordner,
            api_key=args.api_key,
            base_url=args.base_url,
            model_name=args.model,
            max_workers=args.workers
        )
        translator.process_files()
    except Exception as e:
        print(f"Abbruch: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
