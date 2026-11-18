"""Leitor de skins clássicas (.wsz: um zip de BMPs e arquivos de texto).

- Nomes de arquivo sem diferenciar maiúsculas (`MAIN.BMP`, `main.bmp`, `Main.Bmp`); arquivos em
  subpastas do zip também valem, com preferência para a raiz.
- BMPs viram superfícies pygame (sem `convert()`: chame `Skin.converter()` depois de abrir a janela).
- `viscolor.txt`: 24 cores do analisador; `pledit.txt`: cores da playlist (seção `[Text]`).
- Faltou arquivo? Usa o da skin padrão (`padrao`); sem ela, valores internos para os textos.

Uso:
    padrao = carregar("player/skins_teste/base-2.91.wsz")
    skin = carregar("outra.wsz", padrao=padrao)
"""
from __future__ import annotations

import io
import os
import re
import zipfile
from dataclasses import dataclass, field

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame  # noqa: E402

Cor = tuple[int, int, int]

# BMPs da janela principal, equalizador e playlist (nome sem extensão, minúsculo).
BMPS = (
    "main", "titlebar", "cbuttons", "shufrep", "text", "numbers", "nums_ex", "volume",
    "balance", "monoster", "playpaus", "posbar", "eqmain", "eq_ex", "pledit",
    "gen", "genex", "mb", "video",
)

# Grupos em que basta um dos arquivos: nums_ex (dígitos com sinal de menos) substitui numbers.
EQUIVALENTES: dict[str, tuple[str, ...]] = {"numbers": ("nums_ex", "numbers")}

# Cores do Winamp 2.91 (as mesmas do viscolor.txt da skin padrão), usadas quando nada mais existe.
VISCOLOR_PADRAO: tuple[Cor, ...] = (
    (0, 0, 0), (24, 33, 41), (239, 49, 16), (206, 41, 16), (214, 90, 0), (214, 102, 0),
    (214, 115, 0), (198, 123, 8), (222, 165, 24), (214, 181, 33), (189, 222, 41),
    (148, 222, 33), (41, 206, 16), (50, 190, 16), (57, 181, 16), (49, 156, 8), (41, 148, 0),
    (24, 132, 8), (255, 255, 255), (214, 214, 222), (181, 189, 189), (160, 170, 175),
    (148, 156, 165), (150, 150, 150),
)

PLEDIT_PADRAO: dict[str, str] = {
    "normal": "#00FF00", "current": "#FFFFFF", "normalbg": "#000000",
    "selectedbg": "#0000C6", "font": "Arial", "mbbg": "#000000", "mbfg": "#00FF00",
}


@dataclass
class Skin:
    nome: str
    imagens: dict[str, pygame.Surface] = field(default_factory=dict)
    viscolor: tuple[Cor, ...] = VISCOLOR_PADRAO
    pledit: dict[str, str] = field(default_factory=lambda: dict(PLEDIT_PADRAO))
    # Arquivos que não estavam na skin e vieram do fallback (ou faltam de vez).
    emprestados: list[str] = field(default_factory=list)
    ausentes: list[str] = field(default_factory=list)

    def imagem(self, nome: str) -> pygame.Surface | None:
        """BMP pelo nome (sem extensão, qualquer caixa). Para 'numbers', prefere nums_ex."""
        nome = nome.lower()
        for alternativa in EQUIVALENTES.get(nome, (nome,)):
            if alternativa in self.imagens:
                return self.imagens[alternativa]
        return None

    def cor_pledit(self, chave: str) -> Cor:
        return hex_para_cor(self.pledit.get(chave.lower(), PLEDIT_PADRAO.get(chave.lower(), "#000000")))

    def converter(self) -> None:
        """Converte as superfícies para o formato da tela (blit mais rápido). Exige janela aberta."""
        for nome, img in self.imagens.items():
            self.imagens[nome] = img.convert()


# ---------------------------------------------------------------------------
# Textos


def ler_viscolor(texto: str) -> tuple[Cor, ...]:
    """24 cores 'r,g,b' (uma por linha, com comentários '//'); o que faltar vem do padrão."""
    cores: list[Cor] = []
    for linha in texto.splitlines():
        numeros = re.findall(r"\d+", linha.split("//", 1)[0])
        if len(numeros) >= 3:
            r, g, b = (min(int(n), 255) for n in numeros[:3])
            cores.append((r, g, b))
        if len(cores) == 24:
            break
    return tuple(cores) + VISCOLOR_PADRAO[len(cores):]


def ler_pledit(texto: str) -> dict[str, str]:
    """Chaves da seção [Text] em minúsculas; o que faltar vem do padrão."""
    valores = dict(PLEDIT_PADRAO)
    secao = None
    for linha in texto.splitlines():
        linha = linha.strip()
        if linha.startswith("["):
            secao = linha.strip("[]").strip().lower()
        elif secao == "text" and "=" in linha:
            chave, valor = linha.split("=", 1)
            valores[chave.strip().lower()] = valor.strip()
    return valores


def hex_para_cor(valor: str) -> Cor:
    """'#RRGGBB' (com ou sem '#', ignorando lixo depois) para (r, g, b); inválido vira preto."""
    m = re.search(r"[0-9a-fA-F]{6}", valor)
    if not m:
        return (0, 0, 0)
    h = m.group(0)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


# ---------------------------------------------------------------------------
# Zip


def _indice(zf: zipfile.ZipFile) -> dict[str, str]:
    """nome-base minúsculo -> nome no zip; arquivos da raiz têm preferência sobre subpastas."""
    indice: dict[str, str] = {}
    for info in sorted(zf.infolist(), key=lambda i: i.filename.count("/")):
        if info.is_dir():
            continue
        base = info.filename.rsplit("/", 1)[-1].lower()
        indice.setdefault(base, info.filename)
    return indice


def _carregar_bmp(dados: bytes, nome: str) -> pygame.Surface | None:
    # Algumas skins trazem PNG/GIF com extensão .bmp: se o carregador de BMP recusar,
    # deixa o pygame detectar o formato pelo conteúdo.
    try:
        return pygame.image.load(io.BytesIO(dados), nome)
    except (pygame.error, ValueError):
        pass
    try:
        return pygame.image.load(io.BytesIO(dados))
    except (pygame.error, ValueError):
        return None


def carregar(caminho: str, padrao: Skin | None = None) -> Skin:
    nome = os.path.splitext(os.path.basename(caminho))[0]
    skin = Skin(nome=nome)
    with zipfile.ZipFile(caminho) as zf:
        indice = _indice(zf)
        for bmp in BMPS:
            arquivo = indice.get(bmp + ".bmp")
            if arquivo is not None:
                img = _carregar_bmp(zf.read(arquivo), bmp + ".bmp")
                if img is not None:
                    skin.imagens[bmp] = img
        if "viscolor.txt" in indice:
            skin.viscolor = ler_viscolor(zf.read(indice["viscolor.txt"]).decode("latin-1"))
        elif padrao is not None:
            skin.viscolor = padrao.viscolor
        if "pledit.txt" in indice:
            skin.pledit = ler_pledit(zf.read(indice["pledit.txt"]).decode("latin-1"))
        elif padrao is not None:
            skin.pledit = dict(padrao.pledit)
    _completar(skin, padrao)
    return skin


def _completar(skin: Skin, padrao: Skin | None) -> None:
    """Preenche BMPs ausentes com os da skin padrão (respeitando os equivalentes)."""
    for bmp in BMPS:
        grupo = next((g for g in EQUIVALENTES.values() if bmp in g), (bmp,))
        if any(alt in skin.imagens for alt in grupo):
            continue
        emprestado = padrao.imagens.get(bmp) if padrao is not None else None
        if emprestado is not None:
            skin.imagens[bmp] = emprestado
            skin.emprestados.append(bmp)
        elif bmp == grupo[-1]:  # registra o grupo uma vez só
            skin.ausentes.append(bmp)
