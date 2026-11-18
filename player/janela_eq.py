"""Janela do equalizador (F1.8): eqmain.bmp, 10 bandas + pré-amplificação, de -12 a +12 dB.

Coordenadas do eqmain.bmp (275×315) conferidas na skin base (mesmas do Webamp, MIT):
fundo (0,0,275,116); botões ON/AUTO em y=119; barra de título ativa em y=134 e inativa em y=149;
28 fundos de slider (14×63, um a cada 15 px, 14 por linha) a partir de (13,164), do verde
(-12 dB) ao vermelho (+12 dB); cursor do slider (11×11) em (0,164) e selecionado em (0,176);
fundo do gráfico (113×19) em (0,294), cores da curva (1×19) em (115,294) e linha da
pré-amplificação (113×1) em (0,314).

A janela é montada em 1× numa superfície reaproveitada e ampliada só quando algo muda.
"""
from __future__ import annotations

import pygame

from core.skin import Skin

LARGURA, ALTURA = 275, 116
N_BANDAS = 10
DB_MAX = 12
QUADROS_SLIDER = 28
SLIDER_W, SLIDER_H = 14, 63
CURSOR = 11
POS_PREAMP = (21, 38)
X_BANDA0, PASSO_BANDA, Y_BANDA = 78, 18, 38
POS_ON, POS_AUTO, POS_PRESETS = (14, 18), (40, 18), (217, 18)
POS_GRAFICO = (86, 17)
GRAFICO_W, GRAFICO_H = 113, 19


def _sub(img: pygame.Surface | None, x: int, y: int, w: int, h: int) -> pygame.Surface | None:
    if img is None:
        return None
    ret = pygame.Rect(x, y, w, h).clip(img.get_rect())
    return img.subsurface(ret) if ret.width and ret.height else None


def quadro_slider(db: float) -> int:
    """0 (verde, -12 dB) .. 27 (vermelho, +12 dB)."""
    v = (max(-DB_MAX, min(DB_MAX, db)) + DB_MAX) / (2 * DB_MAX)
    return round(v * (QUADROS_SLIDER - 1))


def y_cursor(db: float) -> int:
    """Topo do cursor dentro do slider: 0 em +12 dB, 51 em -12 dB (meio = 0 dB)."""
    v = (DB_MAX - max(-DB_MAX, min(DB_MAX, db))) / (2 * DB_MAX)
    return round(v * (SLIDER_H - 1 - CURSOR))


def y_grafico(db: float) -> int:
    v = (DB_MAX - max(-DB_MAX, min(DB_MAX, db))) / (2 * DB_MAX)
    return round(v * (GRAFICO_H - 1))


class JanelaEq:
    def __init__(self, skin: Skin, escala: int) -> None:
        self.skin = skin
        self.img = skin.imagens.get("eqmain")
        self.escala = escala
        self.tamanho = (LARGURA * escala, ALTURA * escala)
        self.trabalho = pygame.Surface((LARGURA, ALTURA)).convert()
        self.sup = pygame.Surface(self.tamanho).convert()
        self._ultimo: tuple | None = None

    def desenhar(self, ligado: bool, preamp: float, bandas: list[float], selecionado: int,
                 foco: bool) -> bool:
        """Redesenha `self.sup` se algo mudou; `selecionado` 0 = pré-amp, 1..10 = bandas."""
        chave = (ligado, preamp, tuple(bandas), selecionado, foco)
        if chave == self._ultimo:
            return False
        self._ultimo = chave
        t, img = self.trabalho, self.img
        t.fill((0, 0, 0))
        if img is None:
            pygame.transform.scale(t, self.tamanho, self.sup)
            return True
        t.blit(img, (0, 0), (0, 0, LARGURA, ALTURA))
        t.blit(img, (0, 0), (0, 134 if foco else 149, LARGURA, 14))
        _blit(t, _sub(img, 69 if ligado else 10, 119, 26, 12), POS_ON)
        _blit(t, _sub(img, 36, 119, 32, 12), POS_AUTO)
        _blit(t, _sub(img, 224, 164, 44, 12), POS_PRESETS)
        self._grafico(preamp, bandas)
        self._slider(POS_PREAMP, preamp, selecionado == 0 and foco)
        for i, db in enumerate(bandas):
            self._slider((X_BANDA0 + PASSO_BANDA * i, Y_BANDA), db, selecionado == i + 1 and foco)
        pygame.transform.scale(t, self.tamanho, self.sup)
        return True

    def _slider(self, pos: tuple[int, int], db: float, selecionado: bool) -> None:
        q = quadro_slider(db)
        x, y = pos
        _blit(self.trabalho, _sub(self.img, 13 + (q % 14) * 15, 164 + (q // 14) * 65,
                                  SLIDER_W, SLIDER_H), pos)
        _blit(self.trabalho, _sub(self.img, 0, 176 if selecionado else 164, CURSOR, CURSOR),
              (x + 1, y + y_cursor(db)))

    def _grafico(self, preamp: float, bandas: list[float]) -> None:
        """Fundo, linha da pré-amp e a curva das bandas (interpolação linear entre elas)."""
        gx, gy = POS_GRAFICO
        t = self.trabalho
        _blit(t, _sub(self.img, 0, 294, GRAFICO_W, GRAFICO_H), (gx, gy))
        _blit(t, _sub(self.img, 0, 314, GRAFICO_W, 1), (gx, gy + y_grafico(preamp)))
        cores = [tuple(self.img.get_at((115, 294 + y)))[:3] for y in range(GRAFICO_H)] \
            if self.img.get_height() >= 294 + GRAFICO_H else None
        anterior = None
        for x in range(GRAFICO_W):
            pos = x * (N_BANDAS - 1) / (GRAFICO_W - 1)
            i = min(int(pos), N_BANDAS - 2)
            db = bandas[i] + (bandas[i + 1] - bandas[i]) * (pos - i)
            y = y_grafico(db)
            de, ate = (y, y) if anterior is None else (min(y, anterior), max(y, anterior))
            for yy in range(de, ate + 1):
                t.set_at((gx + x, gy + yy), cores[yy] if cores else (0, 255, 0))
            anterior = y


def _blit(dest: pygame.Surface, img: pygame.Surface | None, pos: tuple[int, int]) -> None:
    if img is not None:
        dest.blit(img, pos)
