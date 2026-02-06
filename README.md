# AI Ebook Translator

![Logo](Gemini_Generated_Image_e5xbase5xbase5xb.png)

A modern, platform-independent GUI application to translate `.epub` ebooks automatically using AI (Moonshot AI / OpenAI API).

## Features

- **Automated Workflow**: Extracts, translates, and recompiles E-Books.
- **Modern User Interface**: Built with PyQt6.
- **Progress Tracking**: Real-time log and progress bar.
- **Resumable**: Skips already translated chapters if interrupted.
- **Configurable**: Choose your AI model, parallel workers, and API endpoint.

## Documentation / Dokumentation

- 🇩🇪 [Deutsches Handbuch (HTML)](doc/manual_de.html) | [Markdown](doc/manual_de.md)
- 🇬🇧 [English Manual (HTML)](doc/manual_en.html)

## Quick Start

```bash
# Install dependencies
pip install PyQt6 openai ebooklib beautifulsoup4 odfpy pyinstaller

# Run
python3 gui_app.py
```

See the [Documentation](doc/manual_en.html) for detailed instructions on creating a standalone executable or desktop shortcut.

---
*Created for von-Platen-IT*
