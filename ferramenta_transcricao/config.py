"""Configuração da ferramenta de transcrição: chave de API, modelo e caminhos externos."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-5.6-luna"

TRANSCRIPT_SKILL_SCRIPT = Path(r"C:\pythonprojects\skills\transcript-skill\scripts\transcribe.py")
TRANSCRIPT_MODEL_SIZE = "small"

PROGRESS_TIMEOUT_SECONDS = 10 * 60
