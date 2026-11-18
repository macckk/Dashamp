"""Testes do player (F1.6) com um motor de áudio falso: rodam no PC e no Eee PC."""
from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pygame
import pytest

from core import skin as sk
from player import sprites as sp
from player.analisador import ALTURA, Analisador
from player.audio_falso import MotorFalso
from player.main import Player, formatar_tempo, listar_faixas

PASTA = Path(__file__).resolve().parent.parent / "player" / "skins_teste"


@pytest.fixture(scope="module")
def skin() -> sk.Skin:
    caminho = PASTA / "base-2.91.wsz"
    if not caminho.exists():
        pytest.skip("skins de teste não baixadas")
    return sk.carregar(str(caminho))


@pytest.fixture()
def player(skin: sk.Skin, tmp_path: Path):
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.display.init()
    pygame.font.init()
    tela = pygame.display.set_mode((800, 480))
    app = SimpleNamespace(tela=tela)
    faixas = []
    for nome in ("a.mp3", "b.mp3", "c.mp3"):
        (tmp_path / nome).write_bytes(b"")
        faixas.append(str(tmp_path / nome))
    p = Player(app, skin, faixas, escala=2, motor=MotorFalso())
    yield p
    pygame.display.quit()


def test_listar_faixas(tmp_path: Path) -> None:
    (tmp_path / "sub").mkdir()
    for n in ("b.MP3", "a.ogg", "capa.jpg", "sub/c.flac"):
        (tmp_path / n).write_bytes(b"")
    nomes = [os.path.relpath(f, tmp_path).replace(os.sep, "/") for f in listar_faixas([str(tmp_path)])]
    assert nomes == ["a.ogg", "b.MP3", "sub/c.flac"]


def test_formatar_tempo() -> None:
    assert formatar_tempo(305) == "5:05" and formatar_tempo(None) == ""


def test_analisador_sobe_na_hora_e_desce_aos_poucos(skin: sk.Skin) -> None:
    a = Analisador(skin.viscolor)
    a.atualizar([1.0] * 19, 0.033)
    assert a.alturas[0] == 1.0 and a.picos[0] == 1.0
    a.atualizar([0.0] * 19, 0.1)
    assert 0.7 < a.alturas[0] < 1.0 and a.picos[0] == 1.0     # pico parado
    dest = pygame.Surface((80, 20))
    a.desenhar(dest, (0, 0))
    assert tuple(dest.get_at((0, ALTURA - 1)))[:3] == skin.viscolor[17]  # base da barra
    assert tuple(dest.get_at((0, 0)))[:3] == skin.viscolor[23]           # pico no topo
    assert tuple(dest.get_at((3, ALTURA - 1)))[:3] in (skin.viscolor[0], skin.viscolor[1])


def test_teclas_e_estado(player: Player) -> None:
    m = player.motor
    tecla = lambda k: player.ao_evento(pygame.event.Event(pygame.KEYDOWN, key=k))
    assert m.chamadas[-1] == "tocar" and player.indice == 0
    player.quadro(player.app.tela, 0.033)
    assert player.estado.reproducao == "tocando" and player.estado.kbps == "320"
    tecla(pygame.K_c)
    assert m.estado() == "pausado"
    tecla(pygame.K_c)
    assert m.estado() == "tocando"
    tecla(pygame.K_b)
    assert player.indice == 1
    tecla(pygame.K_z)
    assert player.indice == 0
    tecla(pygame.K_UP)
    assert player.estado.volume == 80
    tecla(pygame.K_RIGHT)
    assert m.pos == pytest.approx(15.0)
    tecla(pygame.K_v)
    player.quadro(player.app.tela, 0.033)
    assert player.estado.reproducao == "parado" and player.estado.tempo_s is None
    tecla(pygame.K_s)
    tecla(pygame.K_r)
    assert player.estado.aleatorio and player.estado.repetir


def test_fim_da_faixa_segue_e_para_no_fim(player: Player) -> None:
    for esperado in (1, 2):
        player.motor.eventos.put(SimpleNamespace(tipo="fim", texto=""))
        player.quadro(player.app.tela, 0.033)
        assert player.indice == esperado
    player.motor.eventos.put(SimpleNamespace(tipo="fim", texto=""))
    player.quadro(player.app.tela, 0.033)
    assert player.indice == 0 and player.motor.estado() == "parado"


def test_letreiro_rola_em_passos_de_um_caractere(player: Player) -> None:
    player.motor.tags.titulo = "Um titulo bem comprido para nao caber no letreiro"
    player.quadro(player.app.tela, 0.033)
    assert player.estado.deslocamento_titulo == 0
    player.quadro(player.app.tela, 0.25)
    assert player.estado.deslocamento_titulo == sp.LARGURA_CARACTERE
    assert ALTURA == 16
