"""Ponto de entrada de linha de comando: python -m ferramenta_transcricao.cli <diretorio_raiz>"""

import sys
from pathlib import Path

from ferramenta_transcricao import orquestrador


def main() -> int:
    if len(sys.argv) != 2:
        print("Uso: python -m ferramenta_transcricao.cli <diretorio_raiz>")
        return 1

    diretorio_raiz = Path(sys.argv[1])

    if not diretorio_raiz.exists() or not diretorio_raiz.is_dir():
        print(f"Erro: diretório '{diretorio_raiz}' não existe ou não é um diretório.")
        return 1

    resultado = orquestrador.processar_diretorio(diretorio_raiz)
    orquestrador.imprimir_resumo(resultado)

    return 1 if resultado.falhas else 0


if __name__ == "__main__":
    sys.exit(main())
