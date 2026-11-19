"""Luz espia (F2.4): acende quando o valor entra numa das zonas (na cor dela), pode piscar.

A luz apagada (e o rótulo) ficam no fundo; a acesa, com um halo, é pré-renderizada por cor.
"""
from __future__ import annotations

from collections.abc import Sequence

import pygame

from painel.widgets.base import Cor, Widget, Zona, restaurar


class LuzEspia(Widget):
    def __init__(self, canal: str, centro: tuple[int, int], raio: int, zonas: Sequence[Zona], *,
                 rotulo: str = "", piscar_hz: float = 0.0, cor_apagada: Cor = (45, 45, 45),
                 cor_rotulo: Cor = (160, 160, 160)) -> None:
        if not zonas:
            raise ValueError(f"{canal}: a luz precisa de pelo menos uma zona")
        lo = min(z.de for z in zonas)
        hi = max(z.ate for z in zonas)
        super().__init__(canal, lo - 1, hi + 1, tau=0, zonas=zonas)
        self.centro, self.raio = centro, raio
        self.rotulo, self.piscar_hz = rotulo, piscar_hz
        self.cor_apagada, self.cor_rotulo = cor_apagada, cor_rotulo
        halo = round(raio * 1.6)
        self.ret = pygame.Rect(0, 0, 2 * halo, 2 * halo)
        self.ret.center = centro
        self._acesas: dict[Cor, pygame.Surface] = {}
        self._t = 0.0

    def atualizar(self, alvo: float | None, dt: float) -> None:
        super().atualizar(alvo, dt)
        self._t += dt

    def acesa(self) -> bool:
        if self.zona() is None:
            return False
        if self.piscar_hz <= 0:
            return True
        return (self._t * self.piscar_hz) % 1.0 < 0.5

    def _imagem(self, cor: Cor) -> pygame.Surface:
        if cor not in self._acesas:
            s = pygame.Surface(self.ret.size, pygame.SRCALPHA)
            c = (self.ret.w // 2, self.ret.h // 2)
            halo = self.ret.w // 2
            for i in range(8, 0, -1):          # halo: círculos concêntricos transparentes
                r = self.raio + (halo - self.raio) * i / 8
                pygame.draw.circle(s, (*cor, 12 + (8 - i) * 12), c, r)   # mais forte no meio
            pygame.draw.circle(s, cor, c, self.raio)
            claro = tuple(min(255, v + 90) for v in cor)
            pygame.draw.circle(s, claro, (c[0] - self.raio // 3, c[1] - self.raio // 3),
                               max(1, self.raio // 3))
            self._acesas[cor] = s
        return self._acesas[cor]

    def pintar_fundo(self, fundo: pygame.Surface) -> None:
        pygame.draw.circle(fundo, self.cor_apagada, self.centro, self.raio)
        if self.rotulo:
            t = pygame.font.Font(None, max(14, self.raio + 4)).render(self.rotulo, True,
                                                                      self.cor_rotulo)
            fundo.blit(t, t.get_rect(midtop=(self.centro[0], self.ret.bottom - 2)))

    def _chave(self) -> object:
        z = self.zona()
        return (z.cor if z else None) if self.acesa() else None

    def _pintar(self, tela: pygame.Surface, fundo: pygame.Surface) -> list[pygame.Rect]:
        restaurar(tela, fundo, self.ret)
        if self.acesa():
            tela.blit(self._imagem(self.zona().cor), self.ret)
        return [self.ret.copy()]
