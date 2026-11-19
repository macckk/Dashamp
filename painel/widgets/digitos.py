"""Mostrador de 7 segmentos (F2.4), desenhado por código (sem fonte de terceiros).

Os "8" apagados ficam no fundo (o fantasma dos segmentos, como num LED de verdade); os glifos
acesos são pré-renderizados por cor (normal e a de cada zona) em 3× e reduzidos com smoothscale.
Caracteres: 0-9, '-', ' ' e o ponto decimal (desenhado entre os dígitos).

Desempenho: no Eee PC um glifo com alfa de 150 px leva ~4 ms para ser desenhado e um opaco
~0,1 ms. Quando o widget está sozinho na sua área (`sozinho`, posto pelo Painel), cada
(posição, caractere, cor) vira uma imagem **opaca** já combinada com o fundo, feita na primeira
vez que aparece: a repintura do velocímetro caiu de ~13 ms para <1 ms (F3.1).
"""
from __future__ import annotations

from collections.abc import Sequence

import pygame

from painel.widgets.base import Cor, Widget, Zona, restaurar

# Segmentos acesos por caractere (a b c d e f g, sentido horário a partir do topo; g = meio).
SEGMENTOS = {
    "0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd",
    "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abcdfg", "-": "g", " ": "",
}
INCLINACAO = 0.10          # itálico leve, como nos displays de LED


def _poligonos(w: float, h: float, t: float) -> dict[str, list[tuple[float, float]]]:
    """Segmentos hexagonais de espessura t numa célula w×h (sem inclinação)."""
    m = t / 2
    def horizontal(y: float) -> list[tuple[float, float]]:
        return [(m, y), (t, y - m), (w - t, y - m), (w - m, y), (w - t, y + m), (t, y + m)]
    def vertical(x: float, y0: float, y1: float) -> list[tuple[float, float]]:
        return [(x, y0 + m), (x + m, y0 + t), (x + m, y1 - t), (x, y1 - m), (x - m, y1 - t),
                (x - m, y0 + t)]
    meio = h / 2
    return {
        "a": horizontal(m), "g": horizontal(meio), "d": horizontal(h - m),
        "f": vertical(m, 0, meio), "b": vertical(w - m, 0, meio),
        "e": vertical(m, meio, h), "c": vertical(w - m, meio, h),
    }


class Digitos(Widget):
    def __init__(self, canal: str, pos: tuple[int, int], digitos: int, altura: int,
                 minimo: float, maximo: float, *, casas: int = 0, zonas: Sequence[Zona] = (),
                 tau: float = 0.3, cor: Cor = (255, 70, 30), cor_apagada: Cor = (45, 20, 15),
                 espaco: float = 0.25) -> None:
        super().__init__(canal, minimo, maximo, tau, zonas)
        self.n, self.casas, self.altura = digitos, casas, altura
        self.cor, self.cor_apagada = cor, cor_apagada
        self.larg_digito = round(altura * 0.55)
        self.passo = round(self.larg_digito * (1 + espaco)) + round(altura * INCLINACAO)
        self.ret = pygame.Rect(pos, (self.passo * digitos, altura))
        self._glifos: dict[tuple[str, Cor], pygame.Surface] = {}
        self._ponto: dict[Cor, pygame.Surface] = {}
        self._compostos: dict[tuple[int, str, Cor], pygame.Surface] = {}

    def _glifo(self, c: str, cor: Cor) -> pygame.Surface:
        chave = (c, cor)
        g = self._glifos.get(chave)
        if g is None:
            e = 3
            w, h = self.larg_digito * e, self.altura * e
            incl = h * INCLINACAO
            s = pygame.Surface((w + incl, h), pygame.SRCALPHA)
            polis = _poligonos(w, h, h * 0.11)
            for seg in SEGMENTOS[c]:
                pygame.draw.polygon(s, cor, [(x + incl * (1 - y / h), y) for x, y in polis[seg]])
            g = pygame.transform.smoothscale(s, (round((w + incl) / e), self.altura))
            if pygame.display.get_surface() is not None:
                g = g.convert_alpha()
            self._glifos[chave] = g
        return g

    def _composto(self, i: int, c: str, cor: Cor, fundo: pygame.Surface) -> pygame.Surface:
        """Célula `i` com o caractere já desenhado sobre o fundo (opaca)."""
        chave = (i, c, cor)
        s = self._compostos.get(chave)
        if s is None:
            g = self._glifo(c, cor)
            celula = pygame.Rect(self.ret.x + i * self.passo, self.ret.y,
                                 g.get_width(), g.get_height()).clip(fundo.get_rect())
            s = fundo.subsurface(celula).copy()
            s.blit(g, (0, 0))
            self._compostos[chave] = s
        return s

    def _ponto_decimal(self, cor: Cor) -> pygame.Surface:
        if cor not in self._ponto:
            r = max(2, round(self.altura * 0.06))
            s = pygame.Surface((2 * r, 2 * r), pygame.SRCALPHA)
            pygame.draw.circle(s, cor, (r, r), r)
            self._ponto[cor] = s
        return self._ponto[cor]

    def texto(self, valor: float | None = None) -> str:
        v = self.valor if valor is None else valor
        if v is None:
            return "-" * self.n
        v = min(self.maximo, max(self.minimo, v))
        s = f"{v:.{self.casas}f}".replace(".", "")
        s = s.rjust(self.n)
        return s if len(s) <= self.n else "-" * self.n

    def pintar_fundo(self, fundo: pygame.Surface) -> None:
        for i in range(self.n):
            fundo.blit(self._glifo("8", self.cor_apagada), (self.ret.x + i * self.passo, self.ret.y))

    def _cor(self) -> Cor:
        z = self.zona()
        return z.cor if z else self.cor

    def _chave(self) -> object:
        return self.texto(), self._cor()

    def _pintar(self, tela: pygame.Surface, fundo: pygame.Surface) -> list[pygame.Rect]:
        restaurar(tela, fundo, self.ret)
        cor = self._cor()
        for i, c in enumerate(self.texto()):
            if c == " ":
                continue
            pos = (self.ret.x + i * self.passo, self.ret.y)
            if self.sozinho:
                tela.blit(self._composto(i, c, cor, fundo), pos)
            else:
                tela.blit(self._glifo(c, cor), pos)
        if self.casas and self.valor is not None:
            p = self._ponto_decimal(cor)
            x = self.ret.x + (self.n - self.casas) * self.passo - p.get_width() - 1
            tela.blit(p, (x, self.ret.bottom - p.get_height()))
        return [self.ret.copy()]
