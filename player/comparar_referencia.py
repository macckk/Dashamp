"""Compara a janela principal desenhada pelo Dashamp com o screenshot do Winamp Skin Museum (F1.4).

    python -m player.comparar_referencia [skin.wsz ...]

Para cada skin: desenha `ESTADO_REFERENCIA`, compara com os 275×116 de cima do screenshot
(player/skins_teste/<nome>.png, baixado por scripts/baixar_skins.sh) e informa os pixels diferentes,
ignorando a área do analisador (animada). Salva /tmp/comparacao_<nome>.png: referência | Dashamp |
diferenças em vermelho, ampliado 2×. Sai com código 1 se alguma skin tiver diferença.
"""
from __future__ import annotations

import os
import sys
import tempfile
from collections.abc import Sequence

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame  # noqa: E402

from core.skin import carregar  # noqa: E402
from player import sprites as sp  # noqa: E402
from player.janela_principal import (  # noqa: E402
    ESTADO_REFERENCIA, PASTA_SKINS, desenhar, mascara_regiao,
)

AREA_IGNORADA = pygame.Rect(sp.POSICOES["visualizacao"], sp.TAMANHO_VISUALIZACAO)
PASTA_SAIDA = "/tmp" if os.path.isdir("/tmp") else tempfile.gettempdir()


def diferencas(a: pygame.Surface, b: pygame.Surface,
               regiao: pygame.mask.Mask | None = None) -> list[tuple[int, int]]:
    """Pixels diferentes, fora da área do analisador e dentro da região da janela (region.txt:
    o que fica fora é transparente no Winamp e no screenshot mostra o que estava atrás)."""
    pontos = []
    for y in range(sp.ALTURA_JANELA):
        for x in range(sp.LARGURA_JANELA):
            if AREA_IGNORADA.collidepoint(x, y):
                continue
            if regiao is not None and not regiao.get_at((x, y)):
                continue
            if a.get_at((x, y))[:3] != b.get_at((x, y))[:3]:
                pontos.append((x, y))
    return pontos


def regioes(pontos: list[tuple[int, int]]) -> list[str]:
    """Agrupa as diferenças pelos elementos da janela, para saber onde olhar."""
    contagem: dict[str, int] = {}
    for x, y in pontos:
        dono = "outro"
        for nome, (ex, ey) in sp.POSICOES.items():
            s = sp.SPRITES.get(nome) or sp.SPRITES.get(nome + "_lig")
            w, h = (s.w, s.h) if s else (10, 10)
            if nome in ("volume", "balanco"):
                w, h = (68 if nome == "volume" else 38), 13
            if nome in ("letreiro",):
                w, h = sp.LARGURA_LETREIRO, 6
            if nome in ("kbps", "khz"):
                w, h = 15, 6
            if nome in ("minuto_dezena", "minuto_unidade", "segundo_dezena", "segundo_unidade"):
                w, h = 9, 13
            if nome == "posicao":
                w, h = 248, 10
            if nome in ("fundo", "titulo"):
                continue
            if ex <= x < ex + w and ey <= y < ey + h:
                dono = nome
                break
        contagem[dono] = contagem.get(dono, 0) + 1
    return [f"{n}={c}" for n, c in sorted(contagem.items(), key=lambda i: -i[1])]


def comparar(caminho_skin: str, padrao_caminho: str) -> int:
    nome = os.path.splitext(os.path.basename(caminho_skin))[0]
    ref_png = os.path.join(os.path.dirname(caminho_skin), nome + ".png")
    if not os.path.exists(ref_png):
        print(f"{nome}: sem referência ({ref_png}); rode scripts/baixar_skins.sh")
        return 1
    padrao = carregar(padrao_caminho) if os.path.abspath(caminho_skin) != \
        os.path.abspath(padrao_caminho) else None
    skin = carregar(caminho_skin, padrao=padrao)
    nossa = desenhar(skin, ESTADO_REFERENCIA)
    ref = pygame.image.load(ref_png).subsurface((0, 0, sp.LARGURA_JANELA, sp.ALTURA_JANELA))
    regiao = mascara_regiao(skin.regiao)
    pontos = diferencas(nossa, ref, regiao)
    fora = sp.LARGURA_JANELA * sp.ALTURA_JANELA - regiao.count()
    total = regiao.count() - AREA_IGNORADA.width * AREA_IGNORADA.height
    print(f"{nome:22s} {len(pontos):5d} pixels diferentes de {total} "
          f"({100 * len(pontos) / total:.2f}%)  fora da região: {fora}  "
          f"{' '.join(regioes(pontos)[:8])}")

    marca = nossa.copy()
    marca.fill((40, 40, 40))
    marca.blit(nossa, (0, 0))
    for x, y in pontos:
        marca.set_at((x, y), (255, 0, 0))
    pygame.draw.rect(marca, (0, 120, 255), AREA_IGNORADA, 1)
    w, h = sp.LARGURA_JANELA * 2, sp.ALTURA_JANELA * 2
    saida = pygame.Surface((3 * w + 20, h))
    saida.fill((80, 80, 80))
    for i, img in enumerate((ref, nossa, marca)):
        saida.blit(pygame.transform.scale(img, (w, h)), (i * (w + 10), 0))
    pygame.image.save(saida, os.path.join(PASTA_SAIDA, f"comparacao_{nome}.png"))
    return 0 if not pontos else 1


def main(argv: Sequence[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    base = os.path.join(PASTA_SKINS, "base-2.91.wsz")
    skins = argv or sorted(os.path.join(PASTA_SKINS, f) for f in os.listdir(PASTA_SKINS)
                           if f.endswith(".wsz"))
    falhas = sum(comparar(s, base) for s in skins)
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
