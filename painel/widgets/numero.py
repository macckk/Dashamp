"""Número grande com fonte (F2.6), para temas modernos (o `Digitos` é o de 7 segmentos).

Glifos de 0-9, '-' e '.' pré-renderizados por cor; os dígitos ocupam a largura do mais largo
(tabular), então o número não "dança" quando muda. A fonte é a padrão do pygame ou uma do
sistema pelo nome (`fonte`); nenhuma fonte de terceiros vai no repositório.
"""
from __future__ import annotations

from collections.abc import Sequence

import pygame

from painel.widgets.base import Cor, Widget, Zona, restaurar


class Numero(Widget):
    def __init__(self, canal: str, centro: tuple[int, int], tamanho: int, minimo: float,
                 maximo: float, *, digitos: int = 3, casas: int = 0, zonas: Sequence[Zona] = (),
                 tau: float = 0.3, cor: Cor = (240, 240, 240), fonte: str | None = None,
                 alinhar: str = "centro") -> None:
        super().__init__(canal, minimo, maximo, tau, zonas)
        if alinhar not in ("esquerda", "centro", "direita"):
            raise ValueError(f"{canal}: alinhar deve ser esquerda, centro ou direita")
        self.centro, self.digitos, self.casas, self.cor = centro, digitos, casas, cor
        self.alinhar = alinhar
        self.fonte = pygame.font.SysFont(fonte, tamanho, bold=True) if fonte \
            else pygame.font.Font(None, tamanho)
        self._glifos: dict[tuple[str, Cor], pygame.Surface] = {}
        self.larg = max(self.fonte.size(c)[0] for c in "0123456789")
        self.larg_ponto = self.fonte.size(".")[0]
        self.alt = self.fonte.get_height()
        largura = self.larg * digitos + (self.larg_ponto if casas else 0)
        self.ret = pygame.Rect(0, 0, largura, self.alt)
        if alinhar == "centro":
            self.ret.center = centro
        elif alinhar == "esquerda":
            self.ret.midleft = centro
        else:
            self.ret.midright = centro

    def texto(self, valor: float | None = None) -> str:
        v = self.valor if valor is None else valor
        if v is None:
            return "-"
        v = min(self.maximo, max(self.minimo, v))
        s = f"{v:.{self.casas}f}"
        return s if len(s.replace(".", "")) <= self.digitos else "-" * self.digitos

    def _glifo(self, c: str, cor: Cor) -> pygame.Surface:
        g = self._glifos.get((c, cor))
        if g is None:
            g = self.fonte.render(c, True, cor)
            if pygame.display.get_surface() is not None:
                g = g.convert_alpha()
            self._glifos[(c, cor)] = g
        return g

    def _cor(self) -> Cor:
        z = self.zona()
        return z.cor if z else self.cor

    def _chave(self) -> object:
        return self.texto(), self._cor()

    def _pintar(self, tela: pygame.Surface, fundo: pygame.Surface) -> list[pygame.Rect]:
        restaurar(tela, fundo, self.ret)
        s, cor = self.texto(), self._cor()
        larguras = [self.larg_ponto if c == "." else self.larg for c in s]
        total = sum(larguras)
        x = {"centro": self.ret.centerx - total // 2, "esquerda": self.ret.x,
             "direita": self.ret.right - total}[self.alinhar]
        for c, w in zip(s, larguras):
            g = self._glifo(c, cor)
            tela.blit(g, (x + (w - g.get_width()) // 2, self.ret.y))
            x += w
        return [self.ret.copy()]
