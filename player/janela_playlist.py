"""Janela de playlist (F1.7): moldura do pledit.bmp e cores do pledit.txt.

A moldura (275 × altura, altura = 116 + 29·k) é montada uma vez em 1× e ampliada; o texto das
faixas é desenhado direto na escala da tela (nítido), com a fonte do pygame, porque o pledit.txt
só sugere uma fonte do sistema (Arial). Linhas renderizadas ficam em cache; a janela só é
redesenhada quando algo nela muda.
"""
from __future__ import annotations

import pygame

from core.skin import Skin
from player import sprites as sp
from player.metadados import Faixa

LARGURA = 275
ALTURA_MIN = 116
PASSO_ALTURA = 29
ALTURA_LINHA = 13          # em 1×
AREA_X, AREA_Y = 12, 20    # canto da lista dentro da moldura (1×)
MARGEM_DIREITA, MARGEM_BASE = 20, 38


def formatar_duracao(segundos: float | None) -> str:
    if segundos is None:
        return ""
    m, s = divmod(int(round(segundos)), 60)
    return f"{m}:{s:02d}"


class JanelaPlaylist:
    def __init__(self, skin: Skin, linhas_extras: int, escala: int) -> None:
        self.skin = skin
        self.escala = escala
        self.altura = ALTURA_MIN + PASSO_ALTURA * linhas_extras
        self.tamanho = (LARGURA * escala, self.altura * escala)
        self.molduras = {foco: self._moldura(foco) for foco in (True, False)}
        e = escala
        self.area = pygame.Rect(AREA_X * e, AREA_Y * e, (LARGURA - AREA_X - MARGEM_DIREITA) * e,
                                (self.altura - AREA_Y - MARGEM_BASE) * e)
        self.linhas_visiveis = (self.altura - AREA_Y - MARGEM_BASE) // ALTURA_LINHA
        self.fonte = pygame.font.Font(None, int(ALTURA_LINHA * e * 0.85))
        self.cores = {k: skin.cor_pledit(k) for k in ("normal", "current", "normalbg", "selectedbg")}
        self.sup = pygame.Surface(self.tamanho).convert()
        self._cache: dict[tuple[int, str, bool], tuple[pygame.Surface, pygame.Surface]] = {}
        self._ultimo: tuple | None = None
        self.topo = 0

    def _moldura(self, foco: bool) -> pygame.Surface:
        s = "" if foco else "_inativo"
        m = pygame.Surface((LARGURA, self.altura))
        m.fill(self.skin.cor_pledit("normalbg"))

        def por(nome: str, x: int, y: int) -> None:
            img = sp.recortar(self.skin, nome)
            if img is not None:
                m.blit(img, (x, y))

        for x in range(25, LARGURA - 25, 25):
            por("pl_topo" + s, x, 0)
        por("pl_titulo" + s, 25 + (LARGURA - 50 - 100) // 2, 0)
        por("pl_canto_se" + s, 0, 0)
        por("pl_canto_sd" + s, LARGURA - 25, 0)
        for y in range(AREA_Y, self.altura - MARGEM_BASE, PASSO_ALTURA):
            por("pl_esquerda", 0, y)
            por("pl_direita", LARGURA - MARGEM_DIREITA, y)
        por("pl_canto_ie", 0, self.altura - MARGEM_BASE)
        por("pl_canto_id", LARGURA - 150, self.altura - MARGEM_BASE)
        return pygame.transform.scale(m, self.tamanho).convert()

    def _linha(self, i: int, faixa: Faixa, atual: bool) -> tuple[pygame.Surface, pygame.Surface]:
        cor = self.cores["current" if atual else "normal"]
        chave = (i, faixa.nome, atual)
        if chave not in self._cache:
            self._cache[chave] = (self.fonte.render(f"{i + 1}. {faixa.nome}", True, cor),
                                  self.fonte.render(formatar_duracao(faixa.duracao), True, cor))
        return self._cache[chave]

    def ajustar_topo(self, cursor: int, total: int) -> None:
        """Rola o mínimo para o cursor ficar visível."""
        if cursor < self.topo:
            self.topo = cursor
        elif cursor >= self.topo + self.linhas_visiveis:
            self.topo = cursor - self.linhas_visiveis + 1
        self.topo = max(0, min(self.topo, max(0, total - self.linhas_visiveis)))

    def desenhar(self, faixas: list[Faixa], atual: int, cursor: int, foco: bool) -> bool:
        """Redesenha `self.sup` se algo mudou. Devolve True quando redesenhou."""
        self.ajustar_topo(cursor, len(faixas))
        chave = (id(faixas), len(faixas), atual, cursor, foco, self.topo)
        if chave == self._ultimo:
            return False
        self._ultimo = chave
        if len(self._cache) > 400:
            self._cache.clear()
        sup, e = self.sup, self.escala
        sup.blit(self.molduras[foco], (0, 0))
        sup.fill(self.cores["normalbg"], self.area)
        altura_linha = ALTURA_LINHA * e
        anterior = sup.get_clip()
        sup.set_clip(self.area)
        for n in range(self.linhas_visiveis):
            i = self.topo + n
            if i >= len(faixas):
                break
            y = self.area.y + n * altura_linha
            if i == cursor:
                sup.fill(self.cores["selectedbg"], (self.area.x, y, self.area.width, altura_linha))
            nome, duracao = self._linha(i, faixas[i], i == atual)
            dy = (altura_linha - nome.get_height()) // 2
            x_dur = self.area.right - duracao.get_width() - 2 * e
            sup.blit(nome, (self.area.x + 2 * e, y + dy),
                     (0, 0, max(0, x_dur - self.area.x - 6 * e), nome.get_height()))
            sup.blit(duracao, (x_dur, y + dy))
        sup.set_clip(anterior)
        self._desenhar_rolagem(len(faixas))
        return True

    def _desenhar_rolagem(self, total: int) -> None:
        img = sp.recortar(self.skin, "pl_rolagem")
        if img is None:
            return
        e = self.escala
        curso = self.altura - AREA_Y - MARGEM_BASE - img.get_height()
        excedente = max(0, total - self.linhas_visiveis)
        y = AREA_Y + (round(curso * self.topo / excedente) if excedente else 0)
        alvo = pygame.transform.scale(img, (img.get_width() * e, img.get_height() * e))
        self.sup.blit(alvo, ((LARGURA - 15) * e, y * e))
