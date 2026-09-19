"""Prepara o ambiente para rodar a ferramenta_transcricao: confere ffmpeg e a versão
do Python, instala as dependências e cria o .env a partir do exemplo se não existir.

Uso: python verificar_ambiente.py
"""

import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).parent
REQUIREMENTS = RAIZ / "ferramenta_transcricao" / "requirements.txt"
ENV_EXAMPLE = RAIZ / ".env.example"
ENV = RAIZ / ".env"


def checar_python() -> bool:
    if sys.version_info < (3, 10):
        print(f"[X] Python 3.10+ é necessário (você tem {sys.version.split()[0]}).")
        return False
    print(f"[OK] Python {sys.version.split()[0]}")
    return True


def checar_ffmpeg() -> bool:
    ok = True
    for comando in ("ffmpeg", "ffprobe"):
        if shutil.which(comando) is None:
            print(f"[X] '{comando}' não encontrado no PATH. Veja 'Instalando o ffmpeg' "
                  f"em ferramenta_transcricao/README.md.")
            ok = False
        else:
            print(f"[OK] {comando} encontrado")
    return ok


def instalar_dependencias() -> None:
    print("Instalando dependências Python...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS)])


def preparar_env() -> None:
    if ENV.exists():
        print("[OK] .env já existe")
        return
    ENV.write_text(ENV_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    print("[OK] .env criado a partir de .env.example — preencha OPENAI_API_KEY antes de usar.")


def main() -> int:
    print("=== Verificando ambiente ===")
    python_ok = checar_python()
    ffmpeg_ok = checar_ffmpeg()
    instalar_dependencias()
    preparar_env()

    print()
    if python_ok and ffmpeg_ok:
        print("Tudo pronto. Preencha OPENAI_API_KEY no .env e rode:")
        print('  python -m ferramenta_transcricao.cli "<diretorio_raiz_do_curso>"')
        return 0

    print("Resolva os itens marcados com [X] acima antes de usar a ferramenta.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
