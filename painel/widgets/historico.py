"""Histórico (F2.4): linha dos últimos N segundos de um canal.

Guarda uma amostra do valor suavizado a cada 1/taxa s num deque de tamanho fixo e redesenha a
linha só quando entra amostra nova (4 por segundo, por padrão). Grade e linhas das zonas vão
para o fundo.
"""
from __future__ import annotations

from collections import deque
from collections.abc import Sequence

import pygame

from painel.widgets.base import Cor, Widget, Zona, restaurar


class Historico(Widget):
    def __init__(self, canal: str, ret: tuple[int, int, int, int], minimo: float,
                 maximo: float, *, segundos: float = 30.0, taxa: float = 4.0,
                 zonas: Sequence[Zona] = (), tau: float = 0.15, cor: Cor = (60, 200, 255),
                 cor_grade: Cor = (40, 40, 48), espessura: int = 2) -> None:
        super().__init__(canal, minimo, maximo, tau, zonas)
        self.ret = pygame.Rect(ret)
        self.segundos, self.taxa = segundos, taxa
        self.cor, self.cor_grade, self.espessura = cor, cor_grade, espessura
        self.amostras: deque[float] = deque(maxlen=max(2, int(segundos * taxa)))
        self._acumulado = 0.0
        self._contador = 0
        self._pontos: list[tuple[int, int]] = []

    def atualizar(self, alvo: float | None, dt: float) -> None:
        super().atualizar(alvo, dt)
        if self.valor is None:
            return
        self._acumulado += dt
        periodo = 1.0 / self.taxa
        while self._acumulado >= periodo:
            self._acumulado -= periodo
            self.amostras.append(self.valor)
            self._contador += 1

    def _y(self, valor: float) -> int:
        return self.ret.bottom - 1 - round(self.fracao(valor) * (self.ret.h - 1))

    def pintar_fundo(self, fundo: pygame.Surface) -> None:
        r = self.ret
        pygame.draw.rect(fundo, self.cor_grade, r, 1)
        for i in range(1, 4):
            y = r.y + r.h * i // 4
            pygame.draw.line(fundo, self.cor_grade, (r.x, y), (r.right - 1, y))
        for i in range(1, int(self.segundos // 10)):  # uma linha a cada 10 s
            x = r.right - 1 - round(i * 10 / self.segundos * (r.w - 1))
            pygame.draw.line(fundo, self.cor_grade, (x, r.y), (x, r.bottom - 1))
        for z in self.zonas:
            for v in (z.de, z.ate):
                if self.minimo < v < self.maximo:
                    pygame.draw.line(fundo, z.cor, (r.x, self._y(v)), (r.right - 1, self._y(v)))

    def _chave(self) -> object:
        return self._contador

    def _pintar(self, tela: pygame.Surface, fundo: pygame.Surface) -> list[pygame.Rect]:
        restaurar(tela, fundo, self.ret)
        n = len(self.amostras)
        if n >= 2:
            r, total = self.ret, self.amostras.maxlen or n
            x0 = r.right - 1 - round((n - 1) / (total - 1) * (r.w - 1))
            passo = (r.w - 1) / (total - 1)
            pts = self._pontos
            pts.clear()
            for i, v in enumerate(self.amostras):
                pts.append((x0 + round(i * passo), self._y(v)))
            anterior = tela.get_clip()
            tela.set_clip(r)
            pygame.draw.lines(tela, self.cor, False, pts, self.espessura)
            tela.set_clip(anterior)
        return [self.ret.copy()]
