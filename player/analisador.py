"""Analisador de barras clássico (76×16) com as cores do viscolor.txt.

Cores (índices do viscolor): 0 = fundo, 1 = pontos da grade, 2..17 = barras do topo para a base,
23 = marcador de pico. 19 barras de 3 px com 1 px de espaço. Fundo e coluna de cores são
pré-renderizados; cada quadro só faz 19 blits de barra + até 19 de pico (sem alocar superfícies).
"""
from __future__ import annotations

import pygame

from player.espectro import BARRAS

LARGURA, ALTURA = 76, 16
LARGURA_BARRA, PASSO = 3, 4
QUEDA_POR_S = 2.2        # fração da altura que a barra desce por segundo
PICO_PARADO_S = 0.4      # o pico fica parado antes de cair
QUEDA_PICO_POR_S = 0.9


class Analisador:
    def __init__(self, viscolor: tuple[tuple[int, int, int], ...]) -> None:
        self.fundo = pygame.Surface((LARGURA, ALTURA))
        self.fundo.fill(viscolor[0])
        for y in range(1, ALTURA, 2):          # grade de pontos em linhas e colunas alternadas
            for x in range(1, LARGURA, 2):
                self.fundo.set_at((x, y), viscolor[1])
        self.coluna = pygame.Surface((LARGURA_BARRA, ALTURA))
        for y in range(ALTURA):                # linha 0 (topo) = cor 2 ... linha 15 = cor 17
            self.coluna.fill(viscolor[2 + y], (0, y, LARGURA_BARRA, 1))
        self.cor_pico = viscolor[23]
        self.alturas = [0.0] * BARRAS
        self.picos = [0.0] * BARRAS
        self._pico_parado = [0.0] * BARRAS
        self._ret = pygame.Rect(0, 0, LARGURA_BARRA, 0)

    def atualizar(self, barras: list[float] | None, dt: float) -> None:
        """Sobe na hora até o valor novo; desce aos poucos (como o Winamp)."""
        for i in range(BARRAS):
            alvo = barras[i] if barras is not None else 0.0
            h = max(alvo, self.alturas[i] - QUEDA_POR_S * dt)
            self.alturas[i] = h
            if h >= self.picos[i]:
                self.picos[i] = h
                self._pico_parado[i] = PICO_PARADO_S
            elif self._pico_parado[i] > 0:
                self._pico_parado[i] -= dt
            else:
                self.picos[i] = max(h, self.picos[i] - QUEDA_PICO_POR_S * dt)

    def zerar(self) -> None:
        for i in range(BARRAS):
            self.alturas[i] = self.picos[i] = 0.0

    def desenhar(self, dest: pygame.Surface, pos: tuple[int, int]) -> None:
        x0, y0 = pos
        dest.blit(self.fundo, pos)
        ret = self._ret
        for i in range(BARRAS):
            px = round(self.alturas[i] * ALTURA)
            x = x0 + i * PASSO
            if px > 0:
                # A barra mostra a parte de baixo da coluna de cores (base sempre na cor 17).
                ret.update(0, ALTURA - px, LARGURA_BARRA, px)
                dest.blit(self.coluna, (x, y0 + ALTURA - px), ret)
            pico = round(self.picos[i] * ALTURA)
            if pico > 0:
                dest.fill(self.cor_pico, (x, y0 + ALTURA - pico, LARGURA_BARRA, 1))
