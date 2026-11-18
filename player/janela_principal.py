"""Janela principal (275×116) desenhada a partir da skin, em escala 1× ou 2×.

`desenhar(skin, estado)` monta a janela inteira numa superfície 275×116; `ampliar` dobra os pixels
(vizinho mais próximo, sem borrar). A F1.6 vai redesenhar só as partes que mudam; aqui o objetivo
é a imagem estática idêntica à referência.

    python -m player.janela_principal --skin player/skins_teste/zelda_amp_3.wsz --escala 2
"""
from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass

from core.app import ALTURA, LARGURA, App, opcoes_comuns

import pygame  # noqa: E402

from core.skin import Skin, carregar  # noqa: E402
from player import sprites as sp  # noqa: E402

PASTA_SKINS = os.path.join(os.path.dirname(__file__), "skins_teste")


@dataclass
class EstadoJanela:
    reproducao: str = "parado"          # "tocando", "pausado" ou "parado"
    tempo_s: int | None = None          # None: sem tempo (parado)
    titulo: str = ""
    deslocamento_titulo: int = 0        # em pixels (letreiro rolando)
    kbps: str = ""
    khz: str = ""
    estereo: bool | None = None         # None: nenhum dos dois aceso
    volume: int = 75                    # 0..100
    balanco: int = 0                    # -100..100
    posicao: float | None = None        # 0..1; None esconde o cursor
    aleatorio: bool = False
    repetir: bool = False
    eq: bool = False
    pl: bool = False
    ativa: bool = True                  # barra de título ativa


# ---------------------------------------------------------------------------
# Conversões de valor para quadro/posição (mesmas regras do Webamp)


def quadro_volume(volume: int) -> int:
    # floor(v·28/100), limitado a 27: com 75% dá o quadro 21, igual ao Webamp (conferido).
    return min(sp.QUADROS_VOLUME - 1, max(0, min(100, volume)) * sp.QUADROS_VOLUME // 100)


def quadro_balanco(balanco: int) -> int:
    return round(min(100, abs(balanco)) / 100 * (sp.QUADROS_BALANCO - 1))


def x_cursor_volume(volume: int) -> int:
    return round(max(0, min(100, volume)) / 100 * (68 - 14))


def x_cursor_balanco(balanco: int) -> int:
    return round((max(-100, min(100, balanco)) + 100) / 200 * (38 - 14))


def x_cursor_posicao(posicao: float) -> int:
    return round(max(0.0, min(1.0, posicao)) * (248 - 29))


# ---------------------------------------------------------------------------
# Desenho


def _blit(dest: pygame.Surface, img: pygame.Surface | None, pos: tuple[int, int]) -> None:
    if img is not None:
        dest.blit(img, pos)


def _texto(dest: pygame.Surface, skin: Skin, texto: str, pos: tuple[int, int],
           largura: int, deslocamento: int = 0) -> None:
    """Escreve com a fonte da skin, recortado em `largura` pixels a partir de `pos`."""
    area = pygame.Rect(pos, (largura, sp.ALTURA_CARACTERE))
    anterior = dest.get_clip()
    dest.set_clip(area)
    x = pos[0] - deslocamento
    for c in texto:
        if x >= area.right:
            break
        if x + sp.LARGURA_CARACTERE > area.left:
            _blit(dest, sp.caractere(skin, c), (x, pos[1]))
        x += sp.LARGURA_CARACTERE
    dest.set_clip(anterior)


def _tempo(dest: pygame.Surface, skin: Skin, segundos: int) -> None:
    minutos, seg = divmod(max(0, segundos), 60)
    minutos = min(minutos, 99)
    for nome, valor in (("minuto_dezena", minutos // 10), ("minuto_unidade", minutos % 10),
                        ("segundo_dezena", seg // 10), ("segundo_unidade", seg % 10)):
        _blit(dest, sp.digito(skin, valor), sp.POSICOES[nome])


def desenhar(skin: Skin, estado: EstadoJanela,
             destino: pygame.Surface | None = None) -> pygame.Surface:
    """Desenha a janela inteira. Com `destino` (275×116 reaproveitada), não aloca superfícies."""
    sup = destino if destino is not None else pygame.Surface((sp.LARGURA_JANELA, sp.ALTURA_JANELA))
    p = sp.POSICOES
    _blit(sup, sp.recortar(skin, "fundo"), p["fundo"])
    _blit(sup, sp.recortar(skin, "titulo_ativo" if estado.ativa else "titulo_inativo"), p["titulo"])
    _blit(sup, sp.recortar(skin, "clutter_bar"), p["clutter_bar"])

    if estado.reproducao != "parado" or estado.tempo_s is not None:
        nome = {"tocando": "estado_tocando", "pausado": "estado_pausado"}.get(
            estado.reproducao, "estado_parado")
        _blit(sup, sp.recortar(skin, nome), p["estado"])
        if estado.reproducao == "tocando":
            _blit(sup, sp.recortar(skin, "estado_com_sinal"), p["sinal"])
    if estado.tempo_s is not None:
        _tempo(sup, skin, estado.tempo_s)

    _texto(sup, skin, estado.titulo, p["letreiro"], sp.LARGURA_LETREIRO,
           estado.deslocamento_titulo)
    _texto(sup, skin, estado.kbps.rjust(3)[:3], p["kbps"], 15)
    _texto(sup, skin, estado.khz.rjust(2)[:2], p["khz"], 10)
    _blit(sup, sp.recortar(skin, "mono_lig" if estado.estereo is False else "mono"), p["mono"])
    _blit(sup, sp.recortar(skin, "estereo_lig" if estado.estereo else "estereo"), p["estereo"])

    vx, vy = p["volume"]
    _blit(sup, sp.volume_fundo(skin, quadro_volume(estado.volume)), (vx, vy))
    _blit(sup, sp.recortar(skin, "volume_cursor"), (vx + x_cursor_volume(estado.volume), vy + 1))
    bx, by = p["balanco"]
    _blit(sup, sp.balanco_fundo(skin, quadro_balanco(estado.balanco)), (bx, by))
    _blit(sup, sp.recortar(skin, "balanco_cursor"), (bx + x_cursor_balanco(estado.balanco), by + 1))

    _blit(sup, sp.recortar(skin, "eq_lig" if estado.eq else "eq"), p["eq"])
    _blit(sup, sp.recortar(skin, "pl_lig" if estado.pl else "pl"), p["pl"])

    px, py = p["posicao"]
    _blit(sup, sp.recortar(skin, "posicao_fundo"), (px, py))
    if estado.posicao is not None:
        _blit(sup, sp.recortar(skin, "posicao_cursor"), (px + x_cursor_posicao(estado.posicao), py))

    for nome in ("anterior", "tocar", "pausar", "parar", "proxima", "ejetar"):
        _blit(sup, sp.recortar(skin, nome), p[nome])
    _blit(sup, sp.recortar(skin, "aleatorio_lig" if estado.aleatorio else "aleatorio"),
          p["aleatorio"])
    _blit(sup, sp.recortar(skin, "repetir_lig" if estado.repetir else "repetir"), p["repetir"])
    aplicar_regiao(sup, mascara_regiao(skin.regiao))
    return sup


COR_TRANSPARENTE = (255, 0, 255)


def mascara_regiao(poligonos: list[list[tuple[int, int]]] | None,
                   w: int = sp.LARGURA_JANELA, h: int = sp.ALTURA_JANELA) -> pygame.mask.Mask:
    """Pixels dentro da região (união dos polígonos), na regra do Windows: o pixel (x, y) está
    dentro se o seu centro (x+0,5; y+0,5) está dentro do polígono (par-ímpar). Sem região: tudo."""
    if poligonos is None:
        if (w, h) == _MASCARA_CHEIA.get_size():
            return _MASCARA_CHEIA
        return pygame.mask.Mask((w, h), fill=True)
    chave = tuple(tuple(p) for p in poligonos)
    if chave not in _cache_mascaras:
        _cache_mascaras[chave] = _rasterizar(poligonos, w, h)
    return _cache_mascaras[chave]


_cache_mascaras: dict[tuple, pygame.mask.Mask] = {}
_cache_fora: dict[int, pygame.mask.Mask] = {}
_MASCARA_CHEIA = pygame.mask.Mask((sp.LARGURA_JANELA, sp.ALTURA_JANELA), fill=True)


def _rasterizar(poligonos: list[list[tuple[int, int]]], w: int, h: int) -> pygame.mask.Mask:
    # Preenche faixas horizontais numa superfície (rápido) e converte em máscara.
    sup = pygame.Surface((w, h))
    sup.fill((0, 0, 0))
    for poligono in poligonos:
        n = len(poligono)
        for y in range(h):
            cy = y + 0.5
            cortes = sorted(
                x1 + (cy - y1) * (x2 - x1) / (y2 - y1)
                for (x1, y1), (x2, y2) in ((poligono[i], poligono[(i + 1) % n]) for i in range(n))
                if (y1 <= cy) != (y2 <= cy)
            )
            for a, b in zip(cortes[0::2], cortes[1::2]):
                x0, x1_ = max(0, int(a + 0.5)), min(w, int(b + 0.5))
                if x1_ > x0:
                    sup.fill((255, 255, 255), (x0, y, x1_ - x0, 1))
    return pygame.mask.from_threshold(sup, (255, 255, 255), (1, 1, 1, 255))


def aplicar_regiao(sup: pygame.Surface, mascara: pygame.mask.Mask) -> None:
    """Pinta de magenta e torna transparente o que está fora da região (como no Winamp)."""
    fora = _cache_fora.get(id(mascara))
    if fora is None:
        fora = mascara.copy()
        fora.invert()
        _cache_fora[id(mascara)] = fora  # as máscaras ficam vivas em _cache_mascaras
    if fora.count() == 0:
        return
    fora.to_surface(sup, setcolor=COR_TRANSPARENTE, unsetcolor=None)
    sup.set_colorkey(COR_TRANSPARENTE)


def limpar_caches() -> None:
    """Esquece as máscaras de região (chamado ao trocar de skin, para não acumular)."""
    _cache_mascaras.clear()
    _cache_fora.clear()


def ampliar(sup: pygame.Surface, escala: int) -> pygame.Surface:
    if escala == 1:
        return sup
    return pygame.transform.scale(sup, (sup.get_width() * escala, sup.get_height() * escala))


# Estado dos screenshots do Winamp Skin Museum (gerados pelo Webamp): usado como referência.
ESTADO_REFERENCIA = EstadoJanela(
    reproducao="tocando", tempo_s=3,
    titulo="1. DJ Mike Llama - Llama Whippin' Intro (0:05)  ***  ",
    kbps="128", khz="44", estereo=True, volume=75, balanco=0, posicao=0.6,
    aleatorio=True, repetir=True, eq=True, pl=True,
)


def main(argv: Sequence[str] | None = None) -> None:
    p = opcoes_comuns("Dashamp - janela principal estática (F1.4)")
    p.add_argument("--skin", default=os.path.join(PASTA_SKINS, "base-2.91.wsz"))
    p.add_argument("--escala", type=int, choices=(1, 2), default=2)
    args = p.parse_args(argv)
    app = App(args, "Dashamp")
    base = os.path.join(PASTA_SKINS, "base-2.91.wsz")
    padrao = carregar(base) if os.path.exists(base) else None
    skin = carregar(args.skin, padrao=padrao)
    janela = ampliar(desenhar(skin, ESTADO_REFERENCIA), args.escala).convert()
    pos = janela.get_rect(center=(LARGURA // 2, ALTURA // 2))
    app.tela.fill((0, 0, 0))
    app.tela.blit(janela, pos)

    def quadro(tela: pygame.Surface, dt: float) -> list[pygame.Rect]:
        return []  # estático: o primeiro quadro (flip) já mostra tudo

    app.rodar(quadro)


if __name__ == "__main__":
    main()
