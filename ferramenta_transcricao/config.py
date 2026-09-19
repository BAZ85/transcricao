"""Configuração da ferramenta de transcrição: chave de API, modelo e caminhos externos."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

AI_PROVIDER = (os.getenv("AI_PROVIDER") or "openai").strip().lower()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL") or "gpt-5.6-luna"
# Endpoint alternativo compatível com a API da OpenAI (DeepSeek, Qwen, Grok, etc.).
# Deixe em branco para usar a OpenAI oficial — veja "Usando outros modelos" no README.
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL") or None

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL") or "claude-sonnet-5"

TRANSCRIPT_SKILL_SCRIPT = Path(__file__).parent / "scripts" / "transcribe.py"
TRANSCRIPT_MODEL_SIZE = "small"

PROGRESS_TIMEOUT_SECONDS = 10 * 60
