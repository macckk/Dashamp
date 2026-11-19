"""Desenha um CSV de canais (t + colunas) num PNG, um painel por canal. Uso no PC:

    python scripts/grafico_csv.py tmp/simulada.csv tmp/simulada.png [canal ...]

Feito com o pygame (já é dependência), para não trazer o matplotlib só para conferir curvas.
"""
from __future__ import annotations

import csv
import os
import sys

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402

PADRAO = ("velocidade", "rpm", "marcha", "acelerador", "temp_motor", "temp_ar", "combustivel_lh")
LARGURA, ALTURA_PAINEL, MARGEM = 1200, 130, 70
CORES = ((40, 120, 220), (220, 70, 50), (60, 160, 70), (200, 140, 20), (150, 60, 190),
         (30, 160, 160), (120, 120, 120))


def ler(caminho: str) -> dict[str, list[float]]:
    with open(caminho, encoding="utf-8") as arq:
        linhas = list(csv.DictReader(arq))
    return {k: [float(l[k]) for l in linhas] for k in linhas[0]}


def desenhar(dados: dict[str, list[float]], canais: list[str], saida: str) -> None:
    pygame.init()
    fonte = pygame.font.Font(None, 20)
    sup = pygame.Surface((LARGURA, ALTURA_PAINEL * len(canais) + 30))
    sup.fill((255, 255, 255))
    t = dados["t"]
    t0, t1 = t[0], t[-1]
    w = LARGURA - MARGEM - 20
    for i, canal in enumerate(canais):
        y0 = 10 + i * ALTURA_PAINEL
        h = ALTURA_PAINEL - 25
        v = dados[canal]
        lo, hi = min(v), max(v)
        if hi - lo < 1e-9:
            lo, hi = lo - 1, hi + 1
        pygame.draw.rect(sup, (225, 225, 225), (MARGEM, y0, w, h), 1)
        for seg in range(0, int(t1) + 1, 10):     # grade a cada 10 s
            x = MARGEM + (seg - t0) / (t1 - t0) * w
            pygame.draw.line(sup, (235, 235, 235), (x, y0), (x, y0 + h))
            if i == len(canais) - 1:
                sup.blit(fonte.render(f"{seg}s", True, (90, 90, 90)), (x - 8, y0 + h + 4))
        pontos = [(MARGEM + (tt - t0) / (t1 - t0) * w, y0 + h - (vv - lo) / (hi - lo) * h)
                  for tt, vv in zip(t, v)]
        pygame.draw.lines(sup, CORES[i % len(CORES)], False, pontos, 2)
        sup.blit(fonte.render(canal, True, (0, 0, 0)), (6, y0 + h // 2 - 8))
        sup.blit(fonte.render(f"{hi:.1f}", True, (90, 90, 90)), (6, y0))
        sup.blit(fonte.render(f"{lo:.1f}", True, (90, 90, 90)), (6, y0 + h - 14))
    pygame.image.save(sup, saida)


def main() -> None:
    entrada, saida, *canais = sys.argv[1:]
    desenhar(ler(entrada), canais or list(PADRAO), saida)
    print(f"gráfico em {saida}")


if __name__ == "__main__":
    main()
