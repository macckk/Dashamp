"""Testes do cálculo de consumo (F3.2) com valores conhecidos (contas feitas à mão)."""
from __future__ import annotations

import pytest

from carputer import consumo as cs
from scripts.emulador_obd import codigo_para_hex

GASOLINA = cs.COMBUSTIVEIS["gasolina"]


def test_lh_por_maf_gasolina() -> None:
    # 10 g/s de ar / 14,7 = 0,6803 g/s de gasolina × 3600 / 745 g/L = 3,287 L/h
    assert cs.lh_por_maf(10.0, GASOLINA) == pytest.approx(3.2874, abs=1e-3)
    assert cs.lh_por_maf(0.0, GASOLINA) == 0.0
    # mistura rica (λ 0,8): mais combustível para o mesmo ar
    assert cs.lh_por_maf(10.0, GASOLINA, 0.8) == pytest.approx(3.2874 / 0.8, abs=1e-3)
    assert cs.lh_por_maf(10.0, GASOLINA, 0.0) == cs.lh_por_maf(10.0, GASOLINA)  # λ inválida


def test_combustiveis_brasileiros_gastam_mais_volume() -> None:
    lh = {n: cs.lh_por_maf(10.0, c) for n, c in cs.COMBUSTIVEIS.items()}
    assert lh["gasolina"] < lh["gasolina_br"] < lh["etanol"]
    # etanol: 10 / 8,4 × 3600 / 809 = 5,298 L/h (~61% a mais que a gasolina pura)
    assert lh["etanol"] == pytest.approx(5.2975, abs=1e-3)


def test_maf_por_map_lei_dos_gases() -> None:
    # 100 kPa, 1,6 L, VE 0,85, 3000 rpm, 25 °C:
    # 100 × 1,6 × 0,85 × 25 / (0,28705 × 298,15) = 3400 / 85,584 = 39,73 g/s
    assert cs.maf_por_map(100, 25, 3000, 1.6, 0.85) == pytest.approx(39.727, abs=1e-2)
    # marcha lenta: 30 kPa, 800 rpm → ~3,2 g/s (ordem de grandeza de um 1.6 real)
    assert cs.maf_por_map(30, 25, 800, 1.6, 0.85) == pytest.approx(3.178, abs=1e-2)
    assert cs.maf_por_map(0, 25, 800, 1.6) == 0 and cs.maf_por_map(30, 25, 0, 1.6) == 0


def test_km_por_litro() -> None:
    assert cs.km_por_litro(60, 6) == 10
    assert cs.km_por_litro(2, 6) is None           # parado
    assert cs.km_por_litro(60, 0) is None


def test_media_de_uma_hora_constante() -> None:
    """60 km/h gastando 6 L/h por 1 h (lido a 10 Hz) = 10 km/L de média."""
    c = cs.Consumo("gasolina")
    maf = 6.0 * 745.0 / 3600.0 * 14.7               # o MAF que dá 6 L/h
    for i in range(36001):
        saida = c.atualizar({"maf": maf, "velocidade": 60.0}, i * 0.1)
    assert c.metodo == "maf"
    assert saida["combustivel_lh"] == pytest.approx(6.0)
    assert saida["consumo_kml"] == pytest.approx(10.0)
    assert saida["consumo_medio_kml"] == pytest.approx(10.0)
    assert c.litros == pytest.approx(6.0, rel=1e-4) and c.km == pytest.approx(60.0, rel=1e-4)


def test_media_ignora_lacunas_e_parada() -> None:
    c = cs.Consumo("gasolina")
    maf = 6.0 * 745.0 / 3600.0 * 14.7
    c.atualizar({"maf": maf, "velocidade": 60.0}, 0.0)
    c.atualizar({"maf": maf, "velocidade": 60.0}, 1.0)
    c.atualizar({"maf": maf, "velocidade": 60.0}, 100.0)       # carro sumiu 99 s: não conta
    assert c.km == pytest.approx(60 / 3600) and c.litros == pytest.approx(6 / 3600)
    parado = c.atualizar({"maf": 2.0, "velocidade": 0.0}, 100.5)
    assert parado["consumo_kml"] == 0.0 and parado["combustivel_lh"] > 0


def test_escolha_do_metodo() -> None:
    c = cs.Consumo("gasolina", cilindrada_l=1.6)
    assert c.lh({"combustivel_lh": 4.2, "maf": 10.0}, lh_direto=True) == 4.2 and c.metodo == "pid"
    assert c.lh({"combustivel_lh": 4.2, "maf": 10.0}) == pytest.approx(3.2874, abs=1e-3)
    assert c.metodo == "maf"
    v = {"pressao_coletor": 100, "temp_ar": 25, "rpm": 3000}
    assert c.lh(v) == pytest.approx(cs.lh_por_maf(39.727, GASOLINA), abs=1e-2)
    assert c.metodo == "map"
    assert cs.Consumo("gasolina").lh(v) is None                # sem MAF e sem cilindrada
    assert cs.Consumo().atualizar({"rpm": 900}, 0) == {}
    with pytest.raises(ValueError, match="diesel"):
        cs.Consumo("diesel")


@pytest.mark.parametrize("codigo, hexa", [
    ("P0143", "0143"), ("P0300", "0300"), ("P1234", "1234"), ("C0035", "4035"),
    ("B2AB1", "AAB1"), ("U3000", "F000"),
])
def test_codigo_para_hex(codigo: str, hexa: str) -> None:
    """Lançador de testes do emulador: 2 bits do grupo + 2 do 1.º dígito + 3 hexadecimais."""
    assert codigo_para_hex(codigo) == hexa
    with pytest.raises(ValueError):
        codigo_para_hex("X0143")
