"""Testes da janela principal estática (F1.4)."""
from __future__ import annotations

from pathlib import Path

import pygame
import pytest

from core import skin as sk
from player import janela_principal as jp
from player.comparar_referencia import diferencas

PASTA = Path(__file__).resolve().parent.parent / "player" / "skins_teste"
SKINS = ["base-2.91", "winamp5_classified", "zelda_amp_3"]


@pytest.fixture(scope="module")
def base() -> sk.Skin:
    caminho = PASTA / "base-2.91.wsz"
    if not caminho.exists():
        pytest.skip("skins de teste não baixadas (rode scripts/baixar_skins.sh)")
    return sk.carregar(str(caminho))


def test_regras_de_quadro_e_cursor() -> None:
    assert jp.quadro_volume(0) == 0 and jp.quadro_volume(100) == 27
    assert jp.quadro_volume(75) == 21                       # conferido com o Webamp
    assert jp.quadro_balanco(0) == 0 and jp.quadro_balanco(-100) == jp.quadro_balanco(100) == 27
    assert jp.x_cursor_volume(75) == 40 and jp.x_cursor_balanco(0) == 12
    assert jp.x_cursor_posicao(0.6) == 131 and jp.x_cursor_posicao(2.0) == 219


def test_ler_regiao_e_mascara() -> None:
    texto = "[Normal]\nNumPoints=4\nPointList=2,0 6,0 6,4 2,4\n[Equalizer]\nNumPoints=3\n"
    poligonos = sk.ler_regiao(texto)
    assert poligonos == [[(2, 0), (6, 0), (6, 4), (2, 4)]]
    m = jp.mascara_regiao(poligonos, 8, 5)
    assert m.count() == 4 * 4                                # bordas direita/de baixo ficam fora
    assert m.get_at((2, 0)) and not m.get_at((6, 0)) and not m.get_at((2, 4))
    assert jp.mascara_regiao(None, 8, 5).count() == 40
    assert sk.ler_regiao("[Normal]\nNumPoints=4\nPointList=1,1\n") is None  # incompleto


@pytest.mark.parametrize("nome", SKINS)
def test_identica_a_referencia_do_museum(nome: str, base: sk.Skin) -> None:
    ref_png = PASTA / f"{nome}.png"
    if not ref_png.exists():
        pytest.skip(f"{ref_png.name} não baixada")
    skin = sk.carregar(str(PASTA / f"{nome}.wsz"), padrao=None if nome == "base-2.91" else base)
    nossa = jp.desenhar(skin, jp.ESTADO_REFERENCIA)
    assert nossa.get_size() == (275, 116)
    ref = pygame.image.load(str(ref_png)).subsurface((0, 0, 275, 116))
    assert diferencas(nossa, ref, jp.mascara_regiao(skin.regiao)) == []


def test_ampliar_dobra_pixels(base: sk.Skin) -> None:
    j = jp.desenhar(base, jp.ESTADO_REFERENCIA)
    j2 = jp.ampliar(j, 2)
    assert j2.get_size() == (550, 232)
    for x, y in ((0, 0), (100, 50), (274, 115)):
        cor = j.get_at((x, y))
        assert j2.get_at((2 * x, 2 * y)) == j2.get_at((2 * x + 1, 2 * y + 1)) == cor
