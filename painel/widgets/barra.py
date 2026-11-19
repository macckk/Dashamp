"""Bargraph segmentado (F2.4).

Os segmentos apagados vão para o fundo; os acesos (cada um na cor da zona em que está o seu
meio) são pré-renderizados numa superfície do tamanho da barra, por cima de uma cópia do fundo.
A cada mudança, o quadro restaura a barra (tudo apagado) e copia o trecho aceso: dois blits.
"""
from __future__ import annotations

from collections.abc import Sequence

import pygame

from painel.widgets.base import Cor, Widget, Zona, restaurar


class Barra(Widget):
    def __init__(self, canal: str, ret: tuple[int, int, int, int], minimo: float, maximo: float,
                 *, segmentos: int = 20, vertical: bool = False, espaco: int = 2,
                 zonas: Sequence[Zona] = (), tau: float = 0.15,
                 cor: Cor = (40, 220, 60), cor_apagada: Cor = (30, 40, 30)) -> None:
        super().__init__(canal, minimo, maximo, tau, zonas)
        self.ret = pygame.Rect(ret)
        self.segmentos, self.vertical, self.espaco = segmentos, vertical, espaco
        self.cor, self.cor_apagada = cor, cor_apagada
        self.acesa: pygame.Surface | None = None

    def _ret_segmento(self, i: int) -> pygame.Rect:
        """Segmento i (0 = o do mínimo), em coordenadas locais da barra."""
        w, h = self.ret.size
        if self.vertical:
            passo = (h + self.espaco) / self.segmentos
            y1 = h - round(i * passo)
            y0 = h - round((i + 1) * passo) + self.espaco
            return pygame.Rect(0, y0, w, y1 - y0)
        passo = (w + self.espaco) / self.segmentos
        x0 = round(i * passo)
        return pygame.Rect(x0, 0, round((i + 1) * passo) - self.espaco - x0, h)

    def _cor_segmento(self, i: int) -> Cor:
        meio = self.minimo + (i + 0.5) / self.segmentos * (self.maximo - self.minimo)
        z = self.zona(meio)
        return z.cor if z else self.cor

    def pintar_fundo(self, fundo: pygame.Surface) -> None:
        local = fundo.subsurface(self.ret)
        for i in range(self.segmentos):
            local.fill(self.cor_apagada, self._ret_segmento(i))
        self.acesa = local.copy()
        for i in range(self.segmentos):
            self.acesa.fill(self._cor_segmento(i), self._ret_segmento(i))

    def acesos(self) -> int:
        return 0 if self.valor is None else int(round(self.fracao() * self.segmentos))

    def _chave(self) -> object:
        return self.acesos()

    def _pintar(self, tela: pygame.Surface, fundo: pygame.Surface) -> list[pygame.Rect]:
        restaurar(tela, fundo, self.ret)
        n = self.acesos()
        if n and self.acesa is not None:
            w, h = self.ret.size
            if self.vertical:
                topo = self._ret_segmento(n - 1).top
                trecho = pygame.Rect(0, topo, w, h - topo)
            else:
                trecho = pygame.Rect(0, 0, self._ret_segmento(n - 1).right, h)
            tela.blit(self.acesa, self.ret.move(trecho.topleft).topleft, trecho)
        return [self.ret.copy()]
