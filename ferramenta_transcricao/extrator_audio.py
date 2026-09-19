"""Extração de áudio de vídeos .mp4 via ffmpeg."""

import subprocess
from pathlib import Path


class ExtracaoAudioError(Exception):
    """Levantado quando o ffmpeg falha ao extrair o áudio de um vídeo."""


def extrair_audio(caminho_video: Path) -> Path:
    """Extrai o áudio de um vídeo .mp4 para .mp3 na mesma pasta, via ffmpeg."""
    caminho_video = Path(caminho_video)
    caminho_audio = caminho_video.with_suffix(".mp3")

    comando = [
        "ffmpeg", "-y", "-i", str(caminho_video),
        "-vn", "-acodec", "libmp3lame", "-q:a", "2",
        str(caminho_audio),
    ]
    resultado = subprocess.run(comando, capture_output=True, text=True)

    if resultado.returncode != 0:
        raise ExtracaoAudioError(
            f"ffmpeg falhou ao extrair áudio de {caminho_video}: {resultado.stderr.strip()}"
        )

    return caminho_audio
