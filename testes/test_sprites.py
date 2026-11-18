"""Testes do mapa de sprites (F1.3)."""
from __future__ import annotations

from pathlib import Path

import pytest

from core import skin as sk
from player import sprites as sp

PASTA = Path(__file__).resolve().parent.parent / "player" / "skins_teste"


def _skin(nome: str, padrao: sk.Skin | None = None) -> sk.Skin:
    caminho = PASTA / nome
    if not caminho.exists():
        pytest.skip(f"{nome} não baixada (rode scripts/baixar_skins.sh)")
    return sk.carregar(str(caminho), padrao=padrao)


@pytest.fixture(scope="module")
def base() -> sk.Skin:
    return _skin("base-2.91.wsz")


def test_todo_sprite_cabe_no_bmp_da_skin_padrao(base: sk.Skin) -> None:
    for nome, s in sp.SPRITES.items():
        if s.arquivo == "nums_ex":
            continue  # a base-2.91 não tem nums_ex
        img = base.imagens[s.arquivo]
        assert img.get_rect().contains((s.x, s.y, s.w, s.h)), f"{nome} fora de {s.arquivo}.bmp"
        assert sp.recortar(base, nome).get_size() == (s.w, s.h)


def test_elementos_cabem_na_janela() -> None:
    for nome, (x, y) in sp.POSICOES.items():
        assert 0 <= x < sp.LARGURA_JANELA and 0 <= y < sp.ALTURA_JANELA, nome


def test_quadros_de_volume_e_balanco(base: sk.Skin) -> None:
    assert sp.volume_fundo(base, 0).get_size() == (68, 13)
    assert sp.balanco_fundo(base, 27).get_size() == (38, 13)
    assert sp.volume_fundo(base, 99).get_offset() == sp.volume_fundo(base, 27).get_offset()


def test_fonte_texto() -> None:
    assert sp.posicao_caractere("a") == (0, 0)
    assert sp.posicao_caractere("Z") == (125, 0)          # sem diferenciar caixa
    assert sp.posicao_caractere("0") == (0, 6)
    assert sp.posicao_caractere("#") == (150, 6)
    assert sp.posicao_caractere("?") == (15, 12)
    assert sp.posicao_caractere("<") == sp.posicao_caractere("(")
    assert sp.posicao_caractere("☺") == sp.posicao_caractere(" ")  # desconhecido -> espaço


def test_zelda_bmps_menores_e_nums_ex(base: sk.Skin) -> None:
    zelda = _skin("zelda_amp_3.wsz", padrao=base)
    # volume.bmp da Zelda tem 420 px de altura: o cursor (y=422) não existe.
    assert sp.recortar(zelda, "volume_cursor") is None
    assert sp.volume_fundo(zelda, 27).get_size() == (68, 13)
    # Sem numbers.bmp: os dígitos vêm do nums_ex.
    assert sp.digito(zelda, 7).get_parent() is zelda.imagens["nums_ex"]
    # text.bmp de 18 px (3 linhas de 6) já tem a fonte inteira.
    for c in "q?*#":
        assert sp.caractere(zelda, c).get_size() == (5, 6)
