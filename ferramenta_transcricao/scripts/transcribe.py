"""Transcreve um arquivo de áudio/vídeo para .srt usando faster-whisper.

Roda como subprocesso, invocado por transcritor_local.py. Na primeira execução,
instala a dependência faster-whisper via pip caso ainda não esteja disponível.

Uso: python transcribe.py <audio_path> <output_srt> [model_size]
"""

import sys
import subprocess
import os
import time
import math

def format_timestamp(seconds: float):
    td_hours = int(seconds // 3600)
    td_mins = int((seconds % 3600) // 60)
    td_secs = int(seconds % 60)
    td_millis = int((seconds % 1) * 1000)
    return f"{td_hours:02}:{td_mins:02}:{td_secs:02},{td_millis:03}"

def detect_gpu():
    try:
        subprocess.check_output(['nvidia-smi'], stderr=subprocess.STDOUT)
        return True
    except Exception:
        return False

def install_pip_package(package_name):
    print(f"Checking dependency: {package_name}...")
    try:
        if package_name == "faster-whisper":
            import faster_whisper
        elif package_name == "openai-whisper":
            import whisper
        else:
            __import__(package_name)
    except ImportError:
        print(f"Installing {package_name}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])

def transcribe_with_faster_whisper(audio_path, model_size, output_srt, device="cpu"):
    from faster_whisper import WhisperModel

    compute_type = "float16" if device == "cuda" else "int8"
    print(f"Loading faster-whisper model '{model_size}' on {device} (compute_type={compute_type})...")
    model = WhisperModel(model_size, device=device, compute_type=compute_type)

    segments, info = model.transcribe(audio_path, beam_size=5)

    print(f"Detected language: {info.language} (probability: {info.language_probability:.2f})")

    with open(output_srt, "w", encoding="utf-8") as f:
        for i, segment in enumerate(segments, start=1):
            start_str = format_timestamp(segment.start)
            end_str = format_timestamp(segment.end)
            text = segment.text.strip()

            f.write(f"{i}\n{start_str} --> {end_str}\n{text}\n\n")
            f.flush()

            print(f"[{start_str} --> {end_str}] {text}")

def main():
    if len(sys.argv) < 3:
        print("Usage: python transcribe.py <audio_path> <output_srt> [model_size]")
        sys.exit(1)

    audio_path = sys.argv[1]
    output_srt = sys.argv[2]
    model_size = sys.argv[3] if len(sys.argv) > 3 else "small"

    gpu_present = detect_gpu()

    install_pip_package("faster-whisper")

    if gpu_present:
        print("NVIDIA GPU detected.")
        transcribe_with_faster_whisper(audio_path, model_size, output_srt, device="cuda")
    else:
        print("No NVIDIA GPU detected. Using CPU mode (faster-whisper).")
        transcribe_with_faster_whisper(audio_path, model_size, output_srt, device="cpu")

if __name__ == "__main__":
    main()
