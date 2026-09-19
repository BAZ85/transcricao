"""Correção de termos técnicos de um .srt via API da OpenAI, com fallback para texto bruto."""

import re
from dataclasses import dataclass
from pathlib import Path

from ferramenta_transcricao import config

try:
    from openai import OpenAI
except ImportError:  # biblioteca ainda não instalada no ambiente
    OpenAI = None

_PADRAO_TEMPO = re.compile(r"(\d{2}:\d{2}:\d{2}),\d{3}\s*-->\s*(\d{2}:\d{2}:\d{2}),\d{3}")
_TAMANHO_LOTE = 20


@dataclass
class Trecho:
    inicio: str
    fim: str
    texto: str


def _parse_srt(conteudo: str) -> list[Trecho]:
    blocos = re.split(r"\n\s*\n", conteudo.strip())
    trechos = []
    for bloco in blocos:
        linhas = bloco.strip().splitlines()
        if len(linhas) < 2:
            continue
        m = _PADRAO_TEMPO.search(linhas[1])
        if not m:
            continue
        texto = " ".join(linhas[2:]).strip()
        trechos.append(Trecho(inicio=m.group(1), fim=m.group(2), texto=texto))
    return trechos


def _montar_markdown(trechos: list[Trecho]) -> str:
    return "\n\n".join(f"**({t.inicio} -> {t.fim})** {t.texto}" for t in trechos)


def _corrigir_com_api(trechos: list[Trecho]) -> list[Trecho]:
    if not config.OPENAI_API_KEY or OpenAI is None:
        raise RuntimeError("Chave de API da OpenAI ausente ou biblioteca openai não instalada")

    cliente = OpenAI(api_key=config.OPENAI_API_KEY)
    corrigidos: list[Trecho] = []

    for inicio in range(0, len(trechos), _TAMANHO_LOTE):
        lote = trechos[inicio:inicio + _TAMANHO_LOTE]
        texto_numerado = "\n".join(f"[{j}] {t.texto}" for j, t in enumerate(lote))

        resposta = cliente.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Estes trechos são de uma transcrição de aula. Primeiro identifique, "
                        "pelo próprio conteúdo, qual é a disciplina ou área técnica tratada "
                        "(ex.: direito tributário, direito ambiental, medicina, engenharia "
                        "etc.). Em seguida, corrija apenas os termos técnicos, siglas, nomes "
                        "próprios de normas/instituições e jargão dessa área que o motor de "
                        "transcrição de voz possa ter errado. Não altere o restante do texto, "
                        "não resuma, não reescreva estilo. Responda cada trecho na mesma "
                        "numeração [n] recebida, um por linha, sem comentários adicionais."
                    ),
                },
                {"role": "user", "content": texto_numerado},
            ],
        )

        conteudo = resposta.choices[0].message.content or ""
        corrigidos_por_indice: dict[int, str] = {}
        for linha in conteudo.splitlines():
            m = re.match(r"\[(\d+)\]\s?(.*)", linha)
            if m:
                corrigidos_por_indice[int(m.group(1))] = m.group(2)

        for j, trecho in enumerate(lote):
            texto_corrigido = corrigidos_por_indice.get(j, trecho.texto)
            corrigidos.append(Trecho(trecho.inicio, trecho.fim, texto_corrigido))

    return corrigidos


def corrigir_transcricao(caminho_srt: Path) -> tuple[str, bool]:
    """Lê o .srt, corrige termos técnicos via API, e retorna (markdown, correcao_aplicada).

    Em qualquer falha da API (chave ausente, erro de rede, rate limit, resposta
    inesperada), cai em fallback: retorna o texto bruto do .srt, com os mesmos
    timestamps, e correcao_aplicada=False.
    """
    caminho_srt = Path(caminho_srt)
    conteudo = caminho_srt.read_text(encoding="utf-8")
    trechos = _parse_srt(conteudo)

    if not trechos:
        return "", False

    try:
        trechos_corrigidos = _corrigir_com_api(trechos)
        return _montar_markdown(trechos_corrigidos), True
    except Exception:
        return _montar_markdown(trechos), False
