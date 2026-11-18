"""Mapa de sprites da janela principal das skins clássicas (Winamp 2).

Coordenadas conferidas com o código-fonte do Webamp (https://github.com/captbaritone/webamp,
licença MIT, `skinSprites.ts`). São fatos do formato de arquivo; nenhum asset é copiado.

- `SPRITES`: nome -> (arquivo BMP, retângulo de origem).
- `POSICOES`: nome do elemento -> posição (x, y) na janela principal de 275×116.
- `recortar(skin, nome)`: devolve a subsuperfície (sem cópia), recortada aos limites do BMP;
  None se o BMP não existir ou o retângulo cair fora dele (skins com BMP menor que o padrão).
"""
from __future__ import annotations

from typing import NamedTuple

import pygame

from core.skin import Skin

LARGURA_JANELA, ALTURA_JANELA = 275, 116


class Sprite(NamedTuple):
    arquivo: str
    x: int
    y: int
    w: int
    h: int


def _s(arquivo: str, x: int, y: int, w: int, h: int) -> Sprite:
    return Sprite(arquivo, x, y, w, h)


SPRITES: dict[str, Sprite] = {
    "fundo": _s("main", 0, 0, 275, 116),
    # titlebar.bmp
    "titulo_ativo": _s("titlebar", 27, 0, 275, 14),
    "titulo_inativo": _s("titlebar", 27, 15, 275, 14),
    "botao_opcoes": _s("titlebar", 0, 0, 9, 9),
    "botao_opcoes_press": _s("titlebar", 0, 9, 9, 9),
    "botao_minimizar": _s("titlebar", 9, 0, 9, 9),
    "botao_minimizar_press": _s("titlebar", 9, 9, 9, 9),
    "botao_recolher": _s("titlebar", 0, 18, 9, 9),
    "botao_recolher_press": _s("titlebar", 9, 18, 9, 9),
    "botao_fechar": _s("titlebar", 18, 0, 9, 9),
    "botao_fechar_press": _s("titlebar", 18, 9, 9, 9),
    "clutter_bar": _s("titlebar", 304, 0, 8, 43),
    "clutter_bar_inativa": _s("titlebar", 312, 0, 8, 43),
    # cbuttons.bmp — controles de reprodução
    "anterior": _s("cbuttons", 0, 0, 23, 18),
    "anterior_press": _s("cbuttons", 0, 18, 23, 18),
    "tocar": _s("cbuttons", 23, 0, 23, 18),
    "tocar_press": _s("cbuttons", 23, 18, 23, 18),
    "pausar": _s("cbuttons", 46, 0, 23, 18),
    "pausar_press": _s("cbuttons", 46, 18, 23, 18),
    "parar": _s("cbuttons", 69, 0, 23, 18),
    "parar_press": _s("cbuttons", 69, 18, 23, 18),
    "proxima": _s("cbuttons", 92, 0, 22, 18),
    "proxima_press": _s("cbuttons", 92, 18, 22, 18),
    "ejetar": _s("cbuttons", 114, 0, 22, 16),
    "ejetar_press": _s("cbuttons", 114, 16, 22, 16),
    # shufrep.bmp — repetir, aleatório, EQ e PL
    "repetir": _s("shufrep", 0, 0, 28, 15),
    "repetir_press": _s("shufrep", 0, 15, 28, 15),
    "repetir_lig": _s("shufrep", 0, 30, 28, 15),
    "repetir_lig_press": _s("shufrep", 0, 45, 28, 15),
    "aleatorio": _s("shufrep", 28, 0, 47, 15),
    "aleatorio_press": _s("shufrep", 28, 15, 47, 15),
    "aleatorio_lig": _s("shufrep", 28, 30, 47, 15),
    "aleatorio_lig_press": _s("shufrep", 28, 45, 47, 15),
    "eq": _s("shufrep", 0, 61, 23, 12),
    "eq_lig": _s("shufrep", 0, 73, 23, 12),
    "eq_press": _s("shufrep", 46, 61, 23, 12),
    "eq_lig_press": _s("shufrep", 46, 73, 23, 12),
    "pl": _s("shufrep", 23, 61, 23, 12),
    "pl_lig": _s("shufrep", 23, 73, 23, 12),
    "pl_press": _s("shufrep", 69, 61, 23, 12),
    "pl_lig_press": _s("shufrep", 69, 73, 23, 12),
    # playpaus.bmp — indicador de estado
    "estado_tocando": _s("playpaus", 0, 0, 9, 9),
    "estado_pausado": _s("playpaus", 9, 0, 9, 9),
    "estado_parado": _s("playpaus", 18, 0, 9, 9),
    # Indicador de 3 px à esquerda do estado (desenhado por cima dele): verde tocando normalmente,
    # vermelho sem sinal/carregando. Conferido contra os screenshots do Museum.
    "estado_com_sinal": _s("playpaus", 36, 0, 3, 9),
    "estado_sem_sinal": _s("playpaus", 39, 0, 3, 9),
    # monoster.bmp
    "estereo_lig": _s("monoster", 0, 0, 29, 12),
    "estereo": _s("monoster", 0, 12, 29, 12),
    "mono_lig": _s("monoster", 29, 0, 27, 12),
    "mono": _s("monoster", 29, 12, 27, 12),
    # posbar.bmp — barra de posição
    "posicao_fundo": _s("posbar", 0, 0, 248, 10),
    "posicao_cursor": _s("posbar", 248, 0, 29, 10),
    "posicao_cursor_press": _s("posbar", 278, 0, 29, 10),
    # volume.bmp / balance.bmp — cursores (os fundos são 28 quadros, ver volume_fundo())
    "volume_cursor": _s("volume", 15, 422, 14, 11),
    "volume_cursor_press": _s("volume", 0, 422, 14, 11),
    "balanco_cursor": _s("balance", 15, 422, 14, 11),
    "balanco_cursor_press": _s("balance", 0, 422, 14, 11),
}

# pledit.bmp — moldura da janela de playlist (sufixo _inativo: sem foco)
SPRITES.update({
    "pl_canto_se": _s("pledit", 0, 0, 25, 20),
    "pl_canto_se_inativo": _s("pledit", 0, 21, 25, 20),
    "pl_titulo": _s("pledit", 26, 0, 100, 20),
    "pl_titulo_inativo": _s("pledit", 26, 21, 100, 20),
    "pl_topo": _s("pledit", 127, 0, 25, 20),
    "pl_topo_inativo": _s("pledit", 127, 21, 25, 20),
    "pl_canto_sd": _s("pledit", 153, 0, 25, 20),
    "pl_canto_sd_inativo": _s("pledit", 153, 21, 25, 20),
    "pl_esquerda": _s("pledit", 0, 42, 12, 29),
    "pl_direita": _s("pledit", 31, 42, 20, 29),
    "pl_canto_ie": _s("pledit", 0, 72, 125, 38),
    "pl_canto_id": _s("pledit", 126, 72, 150, 38),
    "pl_base": _s("pledit", 179, 0, 25, 38),
    "pl_rolagem": _s("pledit", 52, 53, 8, 18),
    "pl_rolagem_press": _s("pledit", 61, 53, 8, 18),
})

# Dígitos grandes do tempo: numbers.bmp (9×13 cada; o menos é um traço de 5×1)
# ou nums_ex.bmp (9×13 cada, com quadros próprios para o menos).
for _n in range(10):
    SPRITES[f"digito_{_n}"] = _s("numbers", 9 * _n, 0, 9, 13)
    SPRITES[f"digito_ex_{_n}"] = _s("nums_ex", 9 * _n, 0, 9, 13)
SPRITES["digito_vazio"] = _s("numbers", 90, 0, 9, 13)
SPRITES["menos"] = _s("numbers", 20, 6, 5, 1)
SPRITES["sem_menos"] = _s("numbers", 9, 6, 5, 1)
SPRITES["menos_ex"] = _s("nums_ex", 99, 0, 9, 13)
SPRITES["sem_menos_ex"] = _s("nums_ex", 90, 0, 9, 13)

QUADROS_VOLUME = 28
QUADROS_BALANCO = 28

POSICOES: dict[str, tuple[int, int]] = {
    "fundo": (0, 0),
    "titulo": (0, 0),
    "botao_opcoes": (6, 3),
    "botao_minimizar": (244, 3),
    "botao_recolher": (254, 3),
    "botao_fechar": (264, 3),
    "clutter_bar": (10, 22),
    "estado": (26, 28),
    "sinal": (24, 28),
    "menos": (36, 26),           # o traço de numbers.bmp vai em (39, 32)
    "minuto_dezena": (48, 26),
    "minuto_unidade": (60, 26),
    "segundo_dezena": (78, 26),
    "segundo_unidade": (90, 26),
    "visualizacao": (24, 43),    # área de 76×16
    "letreiro": (111, 27),       # 155 px de largura (31 caracteres)
    "kbps": (111, 43),           # 3 caracteres
    "khz": (156, 43),            # 2 caracteres
    "mono": (212, 41),
    "estereo": (239, 41),
    "volume": (107, 57),         # 68×13
    "balanco": (177, 57),        # 38×13
    "eq": (219, 58),
    "pl": (242, 58),
    "posicao": (16, 72),
    "anterior": (16, 88),
    "tocar": (39, 88),
    "pausar": (62, 88),
    "parar": (85, 88),
    "proxima": (108, 88),
    "ejetar": (136, 89),
    "aleatorio": (164, 89),
    "repetir": (210, 89),
}
TAMANHO_VISUALIZACAO = (76, 16)
LARGURA_LETREIRO = 155  # conferido contra os screenshots do Museum (não 154)

# ---------------------------------------------------------------------------
# Fonte de text.bmp: grade de 5×6 (31 colunas). Caractere -> (linha, coluna).

LARGURA_CARACTERE, ALTURA_CARACTERE = 5, 6

FONTE: dict[str, tuple[int, int]] = {}
for _i, _c in enumerate("abcdefghijklmnopqrstuvwxyz\"@"):
    FONTE[_c] = (0, _i)
FONTE[" "] = (0, 30)
for _i, _c in enumerate("0123456789….:()-'!_+\\/[]^&%,=$#"):
    FONTE[_c] = (1, _i)
for _i, _c in enumerate("åöä?*"):
    FONTE[_c] = (2, _i)
# Equivalências: o Winamp desenha esses caracteres com os de cima.
_EQUIVALENTES = {"<": "(", ">": ")", "{": "(", "}": ")", "|": "!", "~": "-", ";": ":",
                 "`": "'", "«": "(", "»": ")"}


def posicao_caractere(c: str) -> tuple[int, int]:
    """(x, y) do caractere em text.bmp; desconhecidos viram espaço. Sem diferenciar caixa."""
    c = c.lower()
    c = _EQUIVALENTES.get(c, c)
    linha, coluna = FONTE.get(c, FONTE[" "])
    return coluna * LARGURA_CARACTERE, linha * ALTURA_CARACTERE


# ---------------------------------------------------------------------------
# Recorte


def _sub(img: pygame.Surface | None, x: int, y: int, w: int, h: int) -> pygame.Surface | None:
    if img is None:
        return None
    ret = pygame.Rect(x, y, w, h).clip(img.get_rect())
    if ret.width == 0 or ret.height == 0:
        return None
    return img.subsurface(ret)


def recortar(skin: Skin, nome: str) -> pygame.Surface | None:
    # imagens.get (e não skin.imagem): "numbers" aqui é o numbers.bmp mesmo; a escolha entre
    # numbers e nums_ex é feita em digito().
    s = SPRITES[nome]
    return _sub(skin.imagens.get(s.arquivo), s.x, s.y, s.w, s.h)


def volume_fundo(skin: Skin, quadro: int) -> pygame.Surface | None:
    """Quadro 0..27 do fundo do volume (68×13, um a cada 15 px)."""
    quadro = max(0, min(QUADROS_VOLUME - 1, quadro))
    return _sub(skin.imagens.get("volume"), 0, 15 * quadro, 68, 13)


def balanco_fundo(skin: Skin, quadro: int) -> pygame.Surface | None:
    """Quadro 0..27 do fundo do balanço (38×13 a partir de x=9, um a cada 15 px)."""
    quadro = max(0, min(QUADROS_BALANCO - 1, quadro))
    return _sub(skin.imagens.get("balance"), 9, 15 * quadro, 38, 13)


def digito(skin: Skin, n: int) -> pygame.Surface | None:
    """Dígito grande 0..9, de nums_ex.bmp se a skin tiver, senão de numbers.bmp."""
    if "nums_ex" in skin.imagens:
        return recortar(skin, f"digito_ex_{n}")
    return recortar(skin, f"digito_{n}")


def caractere(skin: Skin, c: str) -> pygame.Surface | None:
    x, y = posicao_caractere(c)
    return _sub(skin.imagens.get("text"), x, y, LARGURA_CARACTERE, ALTURA_CARACTERE)
