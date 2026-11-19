"""Arco segmentado (F2.6): um anel que se acende do início até o valor, segmento a segmento.

Os segmentos apagados vão para o fundo. Cada segmento aceso (setor de anel na cor da zona do seu
meio) é um sprite pequeno pré-renderizado em 3× com smoothscale; a cada mudança o quadro restaura
o quadrado do arco e cola os n primeiros sprites. Sem rotação nem desenho de polígonos no laço.
"""
from __future__ import annotations

import math
from collections.abc import Sequence

import pygame

from painel.widgets.base import Cor, Widget, Zona, restaurar

SUPER = 3


def setor(centro: tuple[float, float], r_ext: float, r_int: float, a0: float, a1: float,
          cor: Cor | tuple[int, int, int, int]) -> tuple[pygame.Surface, tuple[int, int]]:
    """Setor de anel entre os ângulos a0 e a1 (graus, anti-horário a partir das 3 h), com
    antisserrilhado. Devolve o sprite e a posição do canto na tela."""
    passos = max(2, int(abs(a1 - a0) / 2) + 1)
    angs = [math.radians(a0 + (a1 - a0) * i / passos) for i in range(passos + 1)]
    cx, cy = centro
    pts = [(cx + r_ext * math.cos(a), cy - r_ext * math.sin(a)) for a in angs] + \
          [(cx + r_int * math.cos(a), cy - r_int * math.sin(a)) for a in reversed(angs)]
    x0, y0 = math.floor(min(p[0] for p in pts)) - 1, math.floor(min(p[1] for p in pts)) - 1
    x1, y1 = math.ceil(max(p[0] for p in pts)) + 1, math.ceil(max(p[1] for p in pts)) + 1
    grande = pygame.Surface(((x1 - x0) * SUPER, (y1 - y0) * SUPER), pygame.SRCALPHA)
    pygame.draw.polygon(grande, cor, [((x - x0) * SUPER, (y - y0) * SUPER) for x, y in pts])
    sprite = pygame.transform.smoothscale(grande, (x1 - x0, y1 - y0))
    return sprite, (x0, y0)


class Arco(Widget):
    def __init__(self, canal: str, centro: tuple[int, int], raio: int, minimo: float,
                 maximo: float, *, espessura: int = 24, angulo_zero: float = 225.0,
                 varredura: float = 270.0, segmentos: int = 54, espaco: float = 1.2,
                 zonas: Sequence[Zona] = (), tau: float = 0.12, cor: Cor = (0, 200, 255),
                 cor_apagada: Cor = (35, 40, 48)) -> None:
        super().__init__(canal, minimo, maximo, tau, zonas)
        self.centro, self.raio, self.espessura = centro, raio, espessura
        self.angulo_zero, self.varredura = angulo_zero, varredura
        self.segmentos, self.espaco = segmentos, espaco
        self.cor, self.cor_apagada = cor, cor_apagada
        self.ret = pygame.Rect(0, 0, 2 * raio + 4, 2 * raio + 4)
        self.ret.center = centro
        self._acesos: list[tuple[pygame.Surface, tuple[int, int]]] = []

    def _angulos(self, i: int) -> tuple[float, float]:
        passo = self.varredura / self.segmentos
        a0 = self.angulo_zero - i * passo - self.espaco / 2
        return a0, a0 - passo + self.espaco

    def _cor_segmento(self, i: int) -> Cor:
        meio = self.minimo + (i + 0.5) / self.segmentos * (self.maximo - self.minimo)
        z = self.zona(meio)
        return z.cor if z else self.cor

    def pintar_fundo(self, fundo: pygame.Surface) -> None:
        r_int = self.raio - self.espessura
        convert = pygame.display.get_surface() is not None
        self._acesos = []
        for i in range(self.segmentos):
            a0, a1 = self._angulos(i)
            apagado, pos = setor(self.centro, self.raio, r_int, a0, a1, self.cor_apagada)
            fundo.blit(apagado, pos)
            aceso, pos = setor(self.centro, self.raio, r_int, a0, a1, self._cor_segmento(i))
            self._acesos.append((aceso.convert_alpha() if convert else aceso, pos))

    def acesos(self) -> int:
        return 0 if self.valor is None else int(round(self.fracao() * self.segmentos))

    def _chave(self) -> object:
        return self.acesos()

    def _pintar(self, tela: pygame.Surface, fundo: pygame.Surface) -> list[pygame.Rect]:
        restaurar(tela, fundo, self.ret)
        for sprite, pos in self._acesos[:self.acesos()]:
            tela.blit(sprite, pos)
        return [self.ret.copy()]
