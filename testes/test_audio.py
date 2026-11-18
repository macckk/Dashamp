"""Testes do áudio (F1.5). O agrupamento do espectro roda em qualquer lugar; o motor precisa do
GStreamer (Eee PC) e do MP3 de teste (python3 scripts/gerar_mp3_teste.py)."""
from __future__ import annotations

import os
import time

import pytest

from player.espectro import BARRAS, Agrupador

MP3 = os.path.expanduser("~/musica/teste_320kbps.mp3")


def test_agrupador_cobre_graves_e_agudos() -> None:
    ag = Agrupador(n_bandas=512, taxa=44100)
    assert len(ag.intervalos) == BARRAS
    assert ag.intervalos[0][0] == 0                       # 40 Hz cai na primeira banda
    assert ag.intervalos[-1][1] <= 512
    assert all(b > a for a, b in ag.intervalos)            # nenhuma barra vazia
    assert all(ag.intervalos[i][0] <= ag.intervalos[i + 1][0] for i in range(BARRAS - 1))


def test_agrupador_normaliza_db() -> None:
    ag = Agrupador(n_bandas=512, taxa=44100)
    silencio = ag([-80.0] * 512)
    assert silencio == [0.0] * BARRAS
    tom = [-80.0] * 512
    tom[23] = -6.0                                          # ~1 kHz
    barras = ag(tom)
    assert max(barras) == pytest.approx(0.9)
    assert sum(1 for b in barras if b > 0) == 1


@pytest.fixture(scope="module")
def motor():
    pytest.importorskip("gi")
    if not os.path.exists(MP3):
        pytest.skip("MP3 de teste ausente (python3 scripts/gerar_mp3_teste.py)")
    from player.audio import MotorAudio

    m = MotorAudio("fakesink sync=true")
    m.abrir(MP3)
    m.tocar()
    yield m
    m.fechar()


def _esperar(condicao, limite: float = 5.0) -> bool:
    fim = time.monotonic() + limite
    while time.monotonic() < fim:
        if condicao():
            return True
        time.sleep(0.05)
    return False


def test_toca_e_le_tags(motor) -> None:
    assert _esperar(lambda: motor.estado() == "tocando")
    assert _esperar(lambda: motor.tags.kbps and motor.tags.khz)
    assert motor.tags.titulo == "Varredura de teste" and motor.tags.artista == "Dashamp"
    assert motor.tags.kbps == 320 and motor.tags.khz == 44 and motor.tags.canais == 2
    assert _esperar(lambda: motor.duracao() is not None)
    assert motor.duracao() == pytest.approx(300, abs=1)


def test_espectro_chega_a_20_hz(motor) -> None:
    time.sleep(1.0)  # o início tem um pequeno acúmulo de mensagens
    antes = motor.contadores.espectros
    time.sleep(4.0)
    taxa = (motor.contadores.espectros - antes) / 4.0
    assert 18 <= taxa <= 22
    barras = motor.espectro()
    assert barras is not None and len(barras) == BARRAS and max(barras) > 0.3


def test_busca_volume_balanco_pausa(motor) -> None:
    assert motor.buscar(120)
    assert _esperar(lambda: (motor.posicao() or 0) >= 120)
    assert motor.volume(40) == 40
    assert motor.balanco(-50) == -50
    motor.pausar()
    assert _esperar(lambda: motor.estado() == "pausado")
    pos = motor.posicao()
    time.sleep(0.5)
    assert motor.posicao() == pytest.approx(pos, abs=0.05)
    motor.tocar()
    assert motor.contadores.avisos == []
