"""Testes da FonteSimulada (F2.2). Rodam no PC e no Eee PC (sem pygame)."""
from __future__ import annotations

import time

import pytest

from painel.fontes.base import CANAIS, canais_desconhecidos
from painel.fontes.simulada import KMH_POR_1000, FonteSimulada, simular

# Canais que só o OBD tem (a simulação não os produz).
SO_OBD = {"maf", "trim_curto", "trim_longo", "sonda_o2", "lambda", "consumo_kml",
          "consumo_medio_kml"}


@pytest.fixture(scope="module")
def viagem() -> list[tuple[float, dict[str, float]]]:
    return simular(600)                           # 10 min simulados, 8 Hz


def _serie(viagem, canal: str) -> list[float]:
    return [v[canal] for _, v in viagem]


def test_canais_do_catalogo_e_dentro_da_faixa(viagem) -> None:
    for _, v in viagem:
        assert not canais_desconhecidos(v) and set(v) == set(CANAIS) - SO_OBD
        for n, x in v.items():
            assert CANAIS[n].minimo <= x <= CANAIS[n].maximo, n


def test_deterministica_pela_semente() -> None:
    assert simular(30, semente=7) == simular(30, semente=7)
    assert simular(30, semente=7) != simular(30, semente=8)


def test_ciclos_de_conducao(viagem) -> None:
    vel, marcha = _serie(viagem, "velocidade"), _serie(viagem, "marcha")
    paradas = sum(1 for a, b in zip(vel, vel[1:]) if a > 0 and b == 0)
    assert paradas >= 3 and max(vel) > 60
    assert {1, 2, 3, 4, 5} <= set(marcha)
    trocas = [(a, b) for a, b in zip(marcha, marcha[1:]) if a != b]
    assert all(abs(a - b) == 1 for a, b in trocas)  # sem pular marcha


def test_rpm_coerente_com_marcha_e_velocidade(viagem) -> None:
    rpm = _serie(viagem, "rpm")
    assert 700 < min(rpm) and max(rpm) < 6600
    parado = [v["rpm"] for _, v in viagem if v["velocidade"] == 0]
    assert max(parado) < 1300                       # marcha lenta (fria ~1150)
    # Andando acima de 15 km/h, fora das trocas, rpm ≈ velocidade × razão da marcha.
    for (_, a), (_, b) in zip(viagem, viagem[1:]):
        if a["marcha"] == b["marcha"] > 0 and b["velocidade"] > 15:
            esperado = b["velocidade"] * 1000 / KMH_POR_1000[int(b["marcha"])]
            assert b["rpm"] == pytest.approx(esperado, rel=0.25, abs=150)


def test_aquecimento(viagem) -> None:
    temp = _serie(viagem, "temp_motor")
    assert temp[0] < 30 and 85 < temp[-1] < 95 and max(temp) < 95
    # Sobe quase sempre (só o ruído do termostato desce um pouco).
    assert all(b >= a - 0.05 for a, b in zip(temp, temp[1:]))
    lenta_fria = viagem[8][1]["rpm"]
    lenta_quente = [v["rpm"] for _, v in viagem
                    if v["velocidade"] == 0 and v["marcha"] == 0 and v["temp_motor"] > 80]
    assert lenta_quente and lenta_fria - sum(lenta_quente) / len(lenta_quente) > 200


def test_consumo_e_tanque(viagem) -> None:
    consumo, nivel = _serie(viagem, "combustivel_lh"), _serie(viagem, "combustivel_nivel")
    assert 0.5 < min(consumo) < 2 and 8 < max(consumo) < 25
    assert nivel[-1] < nivel[0] and nivel[0] - nivel[-1] < 3


def test_fonte_em_tempo_real() -> None:
    f = FonteSimulada(hz=20)
    with f:
        time.sleep(1.0)
    assert f.erro is None and 17 <= f.leituras <= 23
    u = f.ultima()
    assert u is not None and 0.8 < u.t < 1.2 and set(u.valores) == set(CANAIS) - SO_OBD
