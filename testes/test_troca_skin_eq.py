"""Testes da F1.8: troca de skin em tempo de execução e equalizador (motor falso; roda no PC)."""
from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pygame
import pytest

from core import skin as sk
from player import janela_eq as jeq
from player import janela_principal as jp
from player import metadados as md
from player.audio_falso import MotorFalso
from player.main import Player, listar_skins

PASTA = Path(__file__).resolve().parent.parent / "player" / "skins_teste"


def test_quadros_e_cursor_do_slider() -> None:
    assert (jeq.quadro_slider(-12), jeq.quadro_slider(0), jeq.quadro_slider(12)) == (0, 14, 27)
    assert jeq.quadro_slider(99) == 27
    assert (jeq.y_cursor(12), jeq.y_cursor(-12)) == (0, 51)
    assert jeq.y_cursor(0) in (25, 26)


@pytest.fixture()
def player(tmp_path: Path):
    skins = listar_skins(str(PASTA))
    if len(skins) < 3:
        pytest.skip("skins de teste não baixadas")
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.display.init()
    pygame.font.init()
    tela = pygame.display.set_mode((800, 480))
    base = sk.carregar(str(PASTA / "base-2.91.wsz"))
    base.converter()
    faixas = [md.Faixa(str(tmp_path / f"{i}.mp3"), f"Faixa {i}", None, 10) for i in range(5)]
    p = Player(SimpleNamespace(tela=tela), base, faixas, escala=2, motor=MotorFalso(),
               skins=skins, padrao=base)
    yield p
    pygame.display.quit()


def _tecla(p: Player, k: int) -> None:
    p.ao_evento(pygame.event.Event(pygame.KEYDOWN, key=k))


def test_troca_de_skin_percorre_a_pasta(player: Player) -> None:
    nomes = []
    for _ in range(3):
        _tecla(player, pygame.K_k)
        assert player.quadro(player.app.tela, 0.033) is None      # redesenha a tela inteira
        nomes.append(player.skin.nome)
    assert nomes == ["winamp5_classified", "zelda_amp_3", "base-2.91"]
    # Janelas refeitas com a skin nova; cache de regiões não acumula.
    assert player.playlists[False].skin is player.skin and player.janela_eq.skin is player.skin
    assert len(jp._cache_mascaras) <= 1


def test_colorkey_acompanha_a_regiao(player: Player) -> None:
    _tecla(player, pygame.K_k)                                    # winamp5_classified: tem região
    assert player.skin.regiao is not None and player.escalado.get_colorkey() is not None
    _tecla(player, pygame.K_k)
    _tecla(player, pygame.K_k)                                    # base: retangular
    assert player.skin.regiao is None and player.escalado.get_colorkey() is None


def test_equalizador_teclado_e_motor(player: Player) -> None:
    _tecla(player, pygame.K_e)
    assert player.inferior == "eq" and player.foco == "principal"
    player.quadro(player.app.tela, 0.033)
    assert player.estado.eq and not player.estado.pl
    _tecla(player, pygame.K_TAB)
    assert player.foco == "eq"
    _tecla(player, pygame.K_RETURN)                               # liga
    for _ in range(3):
        _tecla(player, pygame.K_RIGHT)                            # pré-amp → banda 3
    for _ in range(4):
        _tecla(player, pygame.K_UP)
    assert player.eq_sel == 3 and player.bandas[2] == 4.0
    ligado, preamp, bandas = player.motor.eq
    assert ligado and preamp == 0.0 and bandas[2] == 4.0
    for _ in range(30):
        _tecla(player, pygame.K_DOWN)
    assert player.bandas[2] == -12.0                              # limitado a -12 dB
    assert player.motor.pos == 10.0                               # ←/→ não buscaram na faixa
    _tecla(player, pygame.K_BACKSPACE)
    assert player.motor.eq[2] == [0.0] * 10
    assert player.quadro(player.app.tela, 0.033) is not None
    # O fundo do slider da banda 3 (0 dB) é o quadro 14 do eqmain.bmp.
    eq = player.janela_eq
    x, y = jeq.X_BANDA0 + jeq.PASSO_BANDA * 2, jeq.Y_BANDA
    esperado = player.skin.imagens["eqmain"].get_at((13 + 0 * 15 + 2, 164 + 65 + 2))
    assert eq.trabalho.get_at((x + 2, y + 2)) == esperado
    _tecla(player, pygame.K_e)
    assert player.inferior == "playlist" and player.foco == "playlist"
