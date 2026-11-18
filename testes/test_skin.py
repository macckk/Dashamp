"""Testes do leitor de .wsz (F1.2). Usam as skins de player/skins_teste/ (scripts/baixar_skins.sh);
os testes que dependem delas são pulados se não tiverem sido baixadas."""
from __future__ import annotations

import io
import time
import zipfile
from pathlib import Path

import pytest

from core import skin as sk

PASTA = Path(__file__).resolve().parent.parent / "player" / "skins_teste"
BASE = PASTA / "base-2.91.wsz"
SKINS = ["base-2.91.wsz", "winamp5_classified.wsz", "zelda_amp_3.wsz"]


def _exige(caminho: Path) -> Path:
    if not caminho.exists():
        pytest.skip(f"{caminho.name} não baixada (rode scripts/baixar_skins.sh)")
    return caminho


@pytest.fixture(scope="module")
def padrao() -> sk.Skin:
    return sk.carregar(str(_exige(BASE)))


# --- textos -------------------------------------------------------------------


def test_viscolor_formatos_variados() -> None:
    texto = "0,0,0, // preto\n039,073,135     // zeros à esquerda\n 1 , 2 , 3\nlixo\n300,0,0\n"
    cores = sk.ler_viscolor(texto)
    assert len(cores) == 24
    assert cores[:4] == ((0, 0, 0), (39, 73, 135), (1, 2, 3), (255, 0, 0))
    assert cores[4:] == sk.VISCOLOR_PADRAO[4:]  # o que faltou vem do padrão


def test_pledit_secao_text_e_padroes() -> None:
    texto = "[Text]\r\nNormal=#DECAFF\r\nCURRENT = B7FFFF\r\nmbFG=#FFFFFF0\r\n[Outra]\r\nNormal=#000000\r\n"
    valores = sk.ler_pledit(texto)
    assert valores["normal"] == "#DECAFF"            # a seção [Outra] não sobrescreve
    assert valores["current"] == "B7FFFF"
    assert valores["normalbg"] == sk.PLEDIT_PADRAO["normalbg"]
    assert sk.hex_para_cor(valores["current"]) == (0xB7, 0xFF, 0xFF)
    assert sk.hex_para_cor(valores["mbfg"]) == (255, 255, 255)  # lixo depois é ignorado
    assert sk.hex_para_cor("sem cor") == (0, 0, 0)


# --- skins reais --------------------------------------------------------------


@pytest.mark.parametrize("arquivo", SKINS)
def test_carrega_skin_real(arquivo: str, padrao: sk.Skin) -> None:
    caminho = _exige(PASTA / arquivo)
    inicio = time.perf_counter()
    skin = sk.carregar(str(caminho), padrao=padrao)
    duracao = time.perf_counter() - inicio
    assert duracao < 1.0, f"carga levou {duracao:.2f} s"
    principal = skin.imagem("MAIN")
    assert principal is not None and principal.get_size() == (275, 116)
    for essencial in ("titlebar", "cbuttons", "text", "numbers", "posbar", "volume", "playpaus"):
        assert skin.imagem(essencial) is not None, essencial
    assert len(skin.viscolor) == 24
    assert all(0 <= c <= 255 for cor in skin.viscolor for c in cor)
    assert {"normal", "current", "normalbg", "selectedbg"} <= skin.pledit.keys()


def test_base_bate_com_padroes_internos(padrao: sk.Skin) -> None:
    assert padrao.viscolor == sk.VISCOLOR_PADRAO
    assert padrao.ausentes == [] or set(padrao.ausentes) <= {"genex", "gen", "mb", "video"}


def test_zelda_usa_nums_ex_no_lugar_de_numbers(padrao: sk.Skin) -> None:
    zelda = sk.carregar(str(_exige(PASTA / "zelda_amp_3.wsz")), padrao=padrao)
    assert "numbers" not in zelda.emprestados       # nums_ex basta: nada emprestado
    assert zelda.imagem("numbers") is zelda.imagens["nums_ex"]


# --- fallback com zip sintético ------------------------------------------------


def _wsz_minimo(tmp_path: Path, padrao: sk.Skin) -> Path:
    """Zip só com Main.BMP (caixa mista, numa subpasta) e um viscolor parcial."""
    import pygame

    bmp = io.BytesIO()
    pygame.image.save(padrao.imagens["main"], bmp, "main.bmp")
    caminho = tmp_path / "minima.wsz"
    with zipfile.ZipFile(caminho, "w") as zf:
        zf.writestr("Minima/Main.BMP", bmp.getvalue())
        zf.writestr("VisColor.Txt", "10,20,30\n")
    return caminho


def test_fallback_para_skin_padrao(tmp_path: Path, padrao: sk.Skin) -> None:
    skin = sk.carregar(str(_wsz_minimo(tmp_path, padrao)), padrao=padrao)
    assert skin.imagem("main").get_size() == (275, 116)    # achado na subpasta, outra caixa
    assert "main" not in skin.emprestados
    assert "cbuttons" in skin.emprestados and skin.imagem("cbuttons") is padrao.imagens["cbuttons"]
    assert skin.viscolor[0] == (10, 20, 30) and skin.viscolor[1:] == sk.VISCOLOR_PADRAO[1:]
    assert skin.pledit == padrao.pledit                     # sem pledit.txt: o da padrão


def test_sem_skin_padrao_registra_ausentes(tmp_path: Path, padrao: sk.Skin) -> None:
    skin = sk.carregar(str(_wsz_minimo(tmp_path, padrao)))
    assert "cbuttons" in skin.ausentes and skin.imagem("cbuttons") is None
    assert skin.ausentes.count("numbers") == 1 and "nums_ex" not in skin.ausentes
    assert skin.pledit == sk.PLEDIT_PADRAO
