"""Base dos widgets do painel (F2.4).

Cada widget mostra um canal da fonte. O ciclo é:
1. `pintar_fundo(fundo)` uma vez na carga: a parte estática (escala, segmentos apagados, rótulos)
   vai para o fundo pré-renderizado do painel;
2. `atualizar(alvo, dt)` a cada quadro: aproxima o valor mostrado do valor lido com uma
   exponencial (constante de tempo `tau`; 0 = sem suavização), o que deixa o ponteiro macio
   mesmo com a fonte a 8 Hz;
3. `desenhar(tela, fundo)`: só quando a aparência muda (a `_chave()` quantizada mudou), restaura o
   fundo no retângulo antigo e desenha; devolve os retângulos sujos para o `display.update`.

Zonas de alerta (`Zona(de, ate, cor)`) colorem a escala, os segmentos, os dígitos e acendem luzes.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import pygame

Cor = tuple[int, int, int]


@dataclass(frozen=True)
class Zona:
    de: float
    ate: float
    cor: Cor

    def contem(self, valor: float) -> bool:
        return self.de <= valor <= self.ate


class Widget:
    def __init__(self, canal: str, minimo: float, maximo: float, tau: float = 0.15,
                 zonas: Sequence[Zona] = ()) -> None:
        if maximo <= minimo:
            raise ValueError(f"{canal}: faixa vazia ({minimo}..{maximo})")
        self.canal = canal
        self.minimo, self.maximo = minimo, maximo
        self.tau = tau
        self.zonas = tuple(zonas)
        self.valor: float | None = None      # valor mostrado (suavizado)
        self.ret = pygame.Rect(0, 0, 0, 0)   # área ocupada na tela
        self._ultima_chave: object = object()

    # --- valor ----------------------------------------------------------------------

    def atualizar(self, alvo: float | None, dt: float) -> None:
        if alvo is None:
            return
        if self.valor is None or self.tau <= 0:
            self.valor = alvo
        else:
            self.valor += (alvo - self.valor) * (1.0 - math.exp(-dt / self.tau))

    def fracao(self, valor: float | None = None) -> float:
        v = self.valor if valor is None else valor
        if v is None:
            return 0.0
        return min(1.0, max(0.0, (v - self.minimo) / (self.maximo - self.minimo)))

    def zona(self, valor: float | None = None) -> Zona | None:
        v = self.valor if valor is None else valor
        if v is None:
            return None
        for z in self.zonas:
            if z.contem(v):
                return z
        return None

    # --- desenho --------------------------------------------------------------------

    def pintar_fundo(self, fundo: pygame.Surface) -> None:
        """Parte estática, desenhada uma vez no fundo do painel."""

    def invalidar(self) -> None:
        """Força o próximo `desenhar` (depois de a tela inteira ter sido redesenhada)."""
        self._ultima_chave = object()

    def desenhar(self, tela: pygame.Surface, fundo: pygame.Surface) -> list[pygame.Rect]:
        chave = self._chave()
        if chave == self._ultima_chave:
            return []
        self._ultima_chave = chave
        return self._pintar(tela, fundo)

    def _chave(self) -> object:
        """Estado visual quantizado: se não mudou, não redesenha."""
        raise NotImplementedError

    def _pintar(self, tela: pygame.Surface, fundo: pygame.Surface) -> list[pygame.Rect]:
        raise NotImplementedError


def restaurar(tela: pygame.Surface, fundo: pygame.Surface, ret: pygame.Rect) -> None:
    tela.blit(fundo, ret, ret)


def texto(fonte: pygame.font.Font, s: str, cor: Cor) -> pygame.Surface:
    return fonte.render(s, True, cor)
