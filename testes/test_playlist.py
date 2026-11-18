"""Testes da playlist (F1.7): metadados, .m3u, janela e teclado (motor falso; roda no PC)."""
from __future__ import annotations

import os
import time
from pathlib import Path
from types import SimpleNamespace

import pygame
import pytest

from core import skin as sk
from player import metadados as md
from player.audio_falso import MotorFalso
from player.janela_playlist import JanelaPlaylist, formatar_duracao
from player.main import Player

PASTA = Path(__file__).resolve().parent.parent / "player" / "skins_teste"
LISTA50 = os.path.expanduser("~/musica/lista50")


def _id3(quadros: dict[str, str], versao: int = 4) -> bytes:
    corpo = b""
    for ident, texto in quadros.items():
        dados = b"\x03" + texto.encode("utf-8")
        n = len(dados)
        tam = bytes([(n >> 21) & 127, (n >> 14) & 127, (n >> 7) & 127, n & 127]) if versao == 4 \
            else n.to_bytes(4, "big")
        corpo += ident.encode() + tam + b"\x00\x00" + dados
    n = len(corpo)
    return b"ID3" + bytes([versao, 0, 0]) + bytes([(n >> 21) & 127, (n >> 14) & 127,
                                                   (n >> 7) & 127, n & 127]) + corpo


def _mp3(caminho: Path, segundos: float, kbps_idx: int = 9, tags: dict | None = None,
         xing_quadros: int | None = None) -> None:
    """Quadro MPEG-1 Layer III, 44,1 kHz, estéreo; índice 9 = 128 kbps."""
    cab = bytes([0xFF, 0xFB, kbps_idx << 4, 0x00])
    audio = bytearray(cab + b"\x00" * 600)
    if xing_quadros is not None:
        audio[4 + 32:4 + 32 + 12] = b"Xing" + (1).to_bytes(4, "big") + xing_quadros.to_bytes(4, "big")
    kbps = md._BITRATES[1][kbps_idx]
    total = int(segundos * kbps * 1000 / 8)
    audio += b"\x00" * max(0, total - len(audio))
    caminho.write_bytes(_id3(tags or {}) + bytes(audio))


def test_mp3_cbr_titulo_artista_duracao(tmp_path: Path) -> None:
    arq = tmp_path / "x.mp3"
    _mp3(arq, 12.0, tags={"TIT2": "Canção", "TPE1": "Banda"})
    f = md.ler_mp3(str(arq))
    assert (f.titulo, f.artista) == ("Canção", "Banda")
    assert f.duracao == pytest.approx(12.0, abs=0.05)
    assert f.nome == "Banda - Canção"


def test_mp3_vbr_pelo_cabecalho_xing(tmp_path: Path) -> None:
    arq = tmp_path / "v.mp3"
    _mp3(arq, 1.0, xing_quadros=383)            # 383 × 1152 / 44100 = 10,0 s
    assert md.ler_mp3(str(arq)).duracao == pytest.approx(10.0, abs=0.01)


def test_sem_tags_usa_nome_do_arquivo(tmp_path: Path) -> None:
    arq = tmp_path / "minha musica.mp3"
    _mp3(arq, 3.0)
    f = md.ler_mp3(str(arq))
    assert f.nome == "minha musica" and f.duracao == pytest.approx(3.0, abs=0.05)
    assert md.ler_mp3(str(tmp_path / "nao_existe.mp3")).duracao is None


def test_m3u_com_extinf_e_caminhos_relativos(tmp_path: Path) -> None:
    (tmp_path / "sub").mkdir()
    _mp3(tmp_path / "sub" / "a.mp3", 5.0, tags={"TIT2": "A"})
    (tmp_path / "b.ogg").write_bytes(b"")
    (tmp_path / "lista.m3u").write_text(
        "#EXTM3U\n#EXTINF:5,Ignorado - Porque tem ID3\nsub/a.mp3\n"
        "#EXTINF:183,Fulano - Música B\nb.ogg\n# comentário\n", encoding="utf-8")
    faixas = md.carregar_lista([str(tmp_path / "lista.m3u")])
    assert [f.nome for f in faixas] == ["A", "Fulano - Música B"]
    assert faixas[1].duracao == 183 and formatar_duracao(183) == "3:03"


# --- janela e teclado ------------------------------------------------------------


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
    faixas = [md.Faixa(str(tmp_path / f"{i:02d}.mp3"), f"Faixa {i:02d}", "Dashamp", 10 + i)
              for i in range(1, 21)]
    p = Player(SimpleNamespace(tela=tela), skin, faixas, escala=2, motor=MotorFalso())
    yield p
    pygame.display.quit()


def _tecla(p: Player, k: int) -> None:
    p.ao_evento(pygame.event.Event(pygame.KEYDOWN, key=k))


def test_layout_cabe_na_tela(player: Player) -> None:
    tela = pygame.Rect(0, 0, 800, 480)
    assert tela.contains(player.ret_principal) and tela.contains(player.ret_playlist)
    assert player.ret_playlist.top == player.ret_principal.bottom
    _tecla(player, pygame.K_l)
    assert player.ret_principal is None and tela.contains(player.ret_playlist)
    assert player.playlists[True].linhas_visiveis == 13
    assert player.foco == "playlist"


def test_foco_cursor_e_enter(player: Player) -> None:
    _tecla(player, pygame.K_DOWN)                   # foco na principal: volume
    assert player.cursor == 0 and player.estado.volume == 70
    _tecla(player, pygame.K_TAB)
    assert player.foco == "playlist"
    player.quadro(player.app.tela, 0.033)
    assert player.estado.ativa is False             # título da principal fica inativo
    for _ in range(6):
        _tecla(player, pygame.K_DOWN)
    assert player.cursor == 6
    player.quadro(player.app.tela, 0.033)
    assert player.playlists[False].topo == 3        # 4 linhas visíveis: rolou para mostrar o cursor
    _tecla(player, pygame.K_END)
    assert player.cursor == 19
    _tecla(player, pygame.K_PAGEUP)
    assert player.cursor == 15
    _tecla(player, pygame.K_RETURN)
    assert player.indice == 15 and player.motor.estado() == "tocando"


def test_cursor_acompanha_avanco_automatico(player: Player) -> None:
    player.motor.eventos.put(SimpleNamespace(tipo="fim", texto=""))
    player.quadro(player.app.tela, 0.033)
    assert player.indice == 1 and player.cursor == 1


def test_desenha_so_quando_muda(player: Player, skin: sk.Skin) -> None:
    pl = player.playlists[False]
    assert pl.desenhar(player.faixas, 0, 0, False) in (True, False)
    assert pl.desenhar(player.faixas, 0, 0, False) is False
    assert pl.desenhar(player.faixas, 0, 1, False) is True
    # Linha do cursor com a cor de seleção do pledit.txt; fundo com a normalbg.
    y = pl.area.y + 13 * 2 + 3
    assert tuple(pl.sup.get_at((pl.area.right - 3, y)))[:3] == skin.cor_pledit("selectedbg")
    assert tuple(pl.sup.get_at((pl.area.right - 3, pl.area.y + 13 * 2 * 3 + 3)))[:3] == \
        skin.cor_pledit("normalbg")


def test_lista50_carrega_rapido() -> None:
    if not os.path.isdir(LISTA50):
        pytest.skip("~/musica/lista50 ausente (scripts/gerar_mp3_teste.py --lista 50)")
    t0 = time.perf_counter()
    faixas = md.carregar_lista([LISTA50])
    duracao = time.perf_counter() - t0
    assert duracao < 2.0
    assert len(faixas) == 50 and faixas[0].nome == "Dashamp - Faixa 01"
    assert all(f.duracao and 5.5 < f.duracao < 21 for f in faixas)
