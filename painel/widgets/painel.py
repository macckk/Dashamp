"""Painel: fundo pré-renderizado + widgets + fonte, com redesenho só do que muda (F2.4).

Widgets que se sobrepõem (um mostrador digital dentro de um mostrador analógico, por exemplo)
formam um grupo: se qualquer um do grupo muda, o fundo é restaurado na união das áreas e todos
são redesenhados na ordem da lista. Sem isso, restaurar o fundo de um apagaria o outro.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence

import pygame

from painel.fontes.base import Fonte
from painel.widgets.base import Widget, restaurar


def _grupos(widgets: Sequence[Widget]) -> list[list[Widget]]:
    """Componentes conexos pela interseção dos retângulos, mantendo a ordem original."""
    pai = list(range(len(widgets)))

    def raiz(i: int) -> int:
        while pai[i] != i:
            pai[i] = pai[pai[i]]
            i = pai[i]
        return i

    for i, a in enumerate(widgets):
        for j in range(i + 1, len(widgets)):
            if a.ret.colliderect(widgets[j].ret):
                pai[raiz(j)] = raiz(i)
    grupos: dict[int, list[Widget]] = {}
    for i, w in enumerate(widgets):
        grupos.setdefault(raiz(i), []).append(w)
    return list(grupos.values())


class Painel:
    def __init__(self, tamanho: tuple[int, int], widgets: Sequence[Widget],
                 cor_fundo: tuple[int, int, int] = (10, 10, 14),
                 decorar: Callable[[pygame.Surface], None] | None = None) -> None:
        self.widgets = list(widgets)
        self.fundo = pygame.Surface(tamanho)
        self.fundo.fill(cor_fundo)
        if decorar is not None:              # rótulos e enfeites estáticos do tema
            decorar(self.fundo)
        for w in self.widgets:
            w.pintar_fundo(self.fundo)
        if pygame.display.get_surface() is not None:
            self.fundo = self.fundo.convert()
        self.grupos = _grupos(self.widgets)
        for g in self.grupos:                # widget sozinho pode pintar por cima do fundo
            for w in g:
                w.sozinho = len(g) == 1
        self._uniao = [g[0].ret.unionall([w.ret for w in g[1:]]) for g in self.grupos]
        self._primeiro = True

    def atualizar(self, fonte: Fonte | None, dt: float) -> None:
        leitura = fonte.ultima() if fonte is not None else None
        valores = leitura.valores if leitura is not None else {}
        for w in self.widgets:
            w.atualizar(valores.get(w.canal), dt)

    def desenhar(self, tela: pygame.Surface) -> list[pygame.Rect] | None:
        """Devolve os retângulos sujos, ou None quando redesenhou a tela inteira."""
        if self._primeiro:
            self._primeiro = False
            tela.blit(self.fundo, (0, 0))
            for w in self.widgets:
                w.invalidar()
                w.desenhar(tela, self.fundo)
            return None
        sujos: list[pygame.Rect] = []
        for grupo, uniao in zip(self.grupos, self._uniao):
            if len(grupo) == 1:
                sujos.extend(grupo[0].desenhar(tela, self.fundo))
                continue
            if all(w._chave() == w._ultima_chave for w in grupo):
                continue
            restaurar(tela, self.fundo, uniao)
            for w in grupo:
                w.invalidar()
                w.desenhar(tela, self.fundo)
            sujos.append(uniao)
        return sujos

    def redesenhar_tudo(self) -> None:
        self._primeiro = True
