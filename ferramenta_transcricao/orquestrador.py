"""Percorre as pastas do curso e orquestra extração, transcrição e correção por vídeo."""

from pathlib import Path

from ferramenta_transcricao import corretor_termos, extrator_audio, transcritor_local

_EXTENSAO_VIDEO = ".mp4"


class ResultadoLote:
    def __init__(self):
        self.processados: list[Path] = []
        self.com_aviso: list[Path] = []
        self.pulados: list[Path] = []
        self.falhas: list[tuple[Path, str]] = []


def _ja_processado(caminho_video: Path) -> bool:
    caminho_audio = caminho_video.with_suffix(".mp3")
    caminho_md = caminho_video.with_suffix(".md")
    return caminho_audio.exists() and caminho_md.exists()


def _processar_video(caminho_video: Path) -> str:
    print(f"[{caminho_video.name}] extraindo áudio...")
    caminho_audio = extrator_audio.extrair_audio(caminho_video)

    print(f"[{caminho_video.name}] transcrevendo...")
    caminho_srt = transcritor_local.transcrever_audio(caminho_audio)

    print(f"[{caminho_video.name}] corrigindo termos técnicos...")
    conteudo_md, correcao_aplicada = corretor_termos.corrigir_transcricao(caminho_srt)

    caminho_md = caminho_video.with_suffix(".md")
    caminho_md.write_text(conteudo_md, encoding="utf-8")

    return "processado" if correcao_aplicada else "aviso"


def processar_diretorio(diretorio_raiz: Path) -> ResultadoLote:
    """Percorre recursivamente o diretório raiz processando cada vídeo .mp4 pendente.

    Falha em um vídeo específico não interrompe o lote: é registrada e o
    processamento segue para o próximo vídeo.
    """
    resultado = ResultadoLote()
    videos = sorted(Path(diretorio_raiz).rglob(f"*{_EXTENSAO_VIDEO}"))

    for caminho_video in videos:
        if _ja_processado(caminho_video):
            resultado.pulados.append(caminho_video)
            print(f"[{caminho_video.name}] já processado, pulando.")
            continue

        try:
            status = _processar_video(caminho_video)
            if status == "aviso":
                resultado.com_aviso.append(caminho_video)
            else:
                resultado.processados.append(caminho_video)
        except Exception as erro:
            resultado.falhas.append((caminho_video, str(erro)))
            print(f"[{caminho_video.name}] FALHA: {erro}")

    return resultado


def imprimir_resumo(resultado: ResultadoLote) -> None:
    total = (
        len(resultado.processados)
        + len(resultado.com_aviso)
        + len(resultado.pulados)
        + len(resultado.falhas)
    )
    print("\n=== Resumo ===")
    print(f"Total de vídeos encontrados: {total}")
    print(f"Processados com sucesso: {len(resultado.processados)}")
    print(f"Processados com aviso (sem correção de termos): {len(resultado.com_aviso)}")
    print(f"Pulados (já processados): {len(resultado.pulados)}")
    print(f"Falhas: {len(resultado.falhas)}")
    for caminho_video, erro in resultado.falhas:
        print(f"  - {caminho_video}: {erro}")
