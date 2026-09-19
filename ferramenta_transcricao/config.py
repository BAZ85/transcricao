"""Configuração da ferramenta de transcrição: chave de API, modelo e caminhos externos."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

AI_PROVIDER = (os.getenv("AI_PROVIDER") or "openai").strip().lower()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL") or "gpt-5.6-luna"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL") or "gemini-2.5-flash"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL") or "claude-sonnet-5"

TRANSCRIPT_SKILL_SCRIPT = Path(__file__).parent / "scripts" / "transcribe.py"
TRANSCRIPT_MODEL_SIZE = "small"

PROGRESS_TIMEOUT_SECONDS = 10 * 60
