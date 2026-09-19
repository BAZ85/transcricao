"""Transcrição local via transcript-skill, com timeout por ausência de progresso
e detecção/correção de transcrição truncada antes do fim real do áudio."""

import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

from ferramenta_transcricao import config

_PADRAO_TEMPO_SRT = re.compile(
    r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})"
)

_GAP_MINIMO_PARA_COMPLETAR = 10.0  # segundos
_SOBREPOSICAO_RETRANSCRICAO = 5.0  # segundos, contexto antes do ponto de corte
_MAX_TENTATIVAS_COMPLETAR = 5


class TranscricaoTimeoutError(Exception):
    """Levantado quando o .srt de saída fica sem progresso por tempo demais."""


class TranscricaoError(Exception):
    """Levantado quando transcript-skill encerra com falha (fora do caso de timeout)."""


def _duracao_audio(caminho_audio: Path) -> float:
    saida = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(caminho_audio),
    ], text=True)
    return float(saida.strip())


def _tempo_para_segundos(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def _segundos_para_tempo_srt(segundos: float) -> str:
    segundos = max(0.0, segundos)
    horas = int(segundos // 3600)
    minutos = int((segundos % 3600) // 60)
    segs = int(segundos % 60)
    ms = int(round((segundos - int(segundos)) * 1000))
    return f"{horas:02}:{minutos:02}:{segs:02},{ms:03}"


def _fim_do_ultimo_bloco_srt(caminho_srt: Path) -> float | None:
    if not caminho_srt.exists():
        return None
    matches = _PADRAO_TEMPO_SRT.findall(caminho_srt.read_text(encoding="utf-8"))
    if not matches:
        return None
    _, _, _, _, h2, m2, s2, ms2 = matches[-1]
    return _tempo_para_segundos(h2, m2, s2, ms2)


def _extrair_trecho_final_audio(caminho_audio: Path, inicio_s: float, caminho_saida: Path) -> None:
    comando = [
        "ffmpeg", "-y", "-ss", str(max(0.0, inicio_s)), "-i", str(caminho_audio),
        "-acodec", "libmp3lame", "-q:a", "2", str(caminho_saida),
    ]
    resultado = subprocess.run(comando, capture_output=True, text=True)
    if resultado.returncode != 0:
        raise TranscricaoError(
            f"ffmpeg falhou ao extrair trecho final de {caminho_audio}: {resultado.stderr.strip()}"
        )


def _blocos_srt(caminho_srt: Path) -> list[tuple[float, float, str]]:
    """Retorna lista de (inicio_s, fim_s, texto) de um .srt."""
    if not caminho_srt.exists():
        return []
    texto = caminho_srt.read_text(encoding="utf-8")
    blocos = []
    for bloco in re.split(r"\n\s*\n", texto.strip()):
        linhas = bloco.strip().splitlines()
        if len(linhas) < 2:
            continue
        m = _PADRAO_TEMPO_SRT.search(linhas[1])
        if not m:
            continue
        inicio = _tempo_para_segundos(*m.groups()[0:4])
        fim = _tempo_para_segundos(*m.groups()[4:8])
        blocos.append((inicio, fim, " ".join(linhas[2:]).strip()))
    return blocos


def _escrever_srt(caminho_srt: Path, blocos: list[tuple[float, float, str]]) -> None:
    linhas = []
    for i, (inicio, fim, texto) in enumerate(blocos, start=1):
        linhas.append(
            f"{i}\n{_segundos_para_tempo_srt(inicio)} --> {_segundos_para_tempo_srt(fim)}\n{texto}\n"
        )
    caminho_srt.write_text("\n".join(linhas), encoding="utf-8")


def _completar_transcricao_truncada(caminho_audio: Path, caminho_srt: Path) -> None:
    """Detecta se a transcrição parou antes do fim real do áudio e completa o
    trecho final que faltou, retranscrevendo só essa parte e anexando ao .srt.

    Alguns áudios longos fazem o motor de transcrição parar de gerar texto
    antes do fim real (bug observado em transcript-skill/faster-whisper em
    ao menos um vídeo de ~32 minutos), mesmo havendo fala real no trecho
    perdido. Esta função é uma rede de segurança contra isso. Quando o motor
    trava repetidamente perto do mesmo ponto do áudio, a sobreposição usada
    na retranscrição aumenta a cada tentativa, dando mais contexto novo ao
    modelo na esperança de passar do ponto problemático.
    """
    duracao_total = _duracao_audio(caminho_audio)
    sobreposicao = _SOBREPOSICAO_RETRANSCRICAO

    for _ in range(_MAX_TENTATIVAS_COMPLETAR):
        fim_atual = _fim_do_ultimo_bloco_srt(caminho_srt)
        if fim_atual is None:
            return
        gap = duracao_total - fim_atual
        if gap <= _GAP_MINIMO_PARA_COMPLETAR:
            return

        inicio_trecho = max(0.0, fim_atual - sobreposicao)
        trecho_audio = caminho_audio.with_name(caminho_audio.stem + "._trecho_final.mp3")
        trecho_srt = caminho_audio.with_name(caminho_audio.stem + "._trecho_final.srt")
        try:
            _extrair_trecho_final_audio(caminho_audio, inicio_trecho, trecho_audio)
            _invocar_transcript_skill(trecho_audio, trecho_srt)

            # Mantém só os blocos originais que terminam ANTES do início da
            # janela retranscrita. Filtrar por início não basta: um bloco
            # original pode começar antes da janela mas terminar dentro
            # dela (ou além), e nesse caso ele se sobreporia no tempo aos
            # blocos novos, duplicando texto na junção.
            blocos_originais = [
                b for b in _blocos_srt(caminho_srt) if b[1] <= inicio_trecho
            ]
            blocos_novos = _blocos_srt(trecho_srt)
            blocos_ajustados = [
                (inicio + inicio_trecho, fim + inicio_trecho, texto)
                for inicio, fim, texto in blocos_novos
            ]
            if not blocos_ajustados:
                # Nenhum progresso nesta tentativa; aumenta a sobreposição
                # para a próxima tentativa em vez de desistir de imediato.
                sobreposicao *= 2
                continue
            _escrever_srt(caminho_srt, blocos_originais + blocos_ajustados)

            novo_fim = _fim_do_ultimo_bloco_srt(caminho_srt)
            if novo_fim is not None and novo_fim <= fim_atual:
                # A retranscrição não avançou o fim da transcrição; dobra a
                # sobreposição na próxima tentativa para tentar passar do
                # ponto onde o motor está travando.
                sobreposicao *= 2
        finally:
            trecho_audio.unlink(missing_ok=True)
            trecho_srt.unlink(missing_ok=True)


def _invocar_transcript_skill(caminho_audio: Path, caminho_srt: Path) -> None:
    """Roda transcript-skill sobre um áudio, monitorando progresso no .srt.

    Levanta TranscricaoTimeoutError se ficar config.PROGRESS_TIMEOUT_SECONDS
    sem escrever novos trechos, ou TranscricaoError em qualquer outra falha.
    """
    comando = [
        sys.executable, str(config.TRANSCRIPT_SKILL_SCRIPT),
        str(caminho_audio), str(caminho_srt), config.TRANSCRIPT_MODEL_SIZE,
    ]

    # transcript-skill imprime a transcrição no stdout à medida que processa;
    # sem forçar UTF-8, um caractere fora da codepage padrão do Windows (cp1252)
    # faz o processo quebrar com UnicodeEncodeError no meio da transcrição.
    ambiente = os.environ.copy()
    ambiente["PYTHONIOENCODING"] = "utf-8"
    # Baixar um modelo do Hugging Face pela primeira vez tenta criar symlinks
    # no cache local; sem modo desenvolvedor/admin no Windows isso falha com
    # "OSError: [WinError 1314]". Desabilitar symlinks evita o erro, só custa
    # um pouco mais de espaço em disco (arquivos duplicados em vez de links).
    ambiente["HF_HUB_DISABLE_SYMLINKS"] = "1"

    processo = subprocess.Popen(
        comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        encoding="utf-8", errors="replace", env=ambiente,
    )

    ultima_atividade = time.time()
    timeout_atingido = threading.Event()

    def monitorar_progresso():
        nonlocal ultima_atividade
        ultima_mtime_vista = None
        while processo.poll() is None:
            if caminho_srt.exists():
                mtime_atual = caminho_srt.stat().st_mtime
                if mtime_atual != ultima_mtime_vista:
                    ultima_mtime_vista = mtime_atual
                    ultima_atividade = time.time()
            if time.time() - ultima_atividade > config.PROGRESS_TIMEOUT_SECONDS:
                timeout_atingido.set()
                processo.kill()
                return
            time.sleep(5)

    monitor = threading.Thread(target=monitorar_progresso, daemon=True)
    monitor.start()
    _, stderr = processo.communicate()
    monitor.join(timeout=1)

    if timeout_atingido.is_set():
        raise TranscricaoTimeoutError(
            f"Transcrição de {caminho_audio} sem progresso por mais de "
            f"{config.PROGRESS_TIMEOUT_SECONDS // 60} minutos, processo encerrado."
        )

    if processo.returncode != 0:
        raise TranscricaoError(
            f"transcript-skill falhou ao transcrever {caminho_audio}: {stderr.strip()}"
        )


def transcrever_audio(caminho_audio: Path) -> Path:
    """Invoca transcript-skill sobre o áudio, monitorando progresso no .srt gerado.

    Aborta com TranscricaoTimeoutError se o .srt ficar
    config.PROGRESS_TIMEOUT_SECONDS sem receber novos trechos.

    Após a transcrição inicial, verifica se o `.srt` cobre a duração real do
    áudio; se parou antes do fim (bug observado no motor de transcrição em
    áudios longos), retranscreve automaticamente o trecho final que faltou.
    """
    caminho_audio = Path(caminho_audio)
    caminho_srt = caminho_audio.with_suffix(".srt")

    _invocar_transcript_skill(caminho_audio, caminho_srt)
    _completar_transcricao_truncada(caminho_audio, caminho_srt)

    return caminho_srt
