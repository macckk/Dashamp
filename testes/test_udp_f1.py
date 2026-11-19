"""Testes da FonteUDPF1 (F2.7): decodificação do F1 24, gravação de pacotes e recepção."""
from __future__ import annotations

import socket
import time
from pathlib import Path

import pytest

from painel.fontes import udp_f1 as u


def test_tamanhos_do_f1_24() -> None:
    assert u.CABECALHO.size == 29 and u.TELEMETRIA.size == 60
    assert u.TAMANHOS == {6: 1352, 7: 1239}
    assert len(u.montar_telemetria(0, 0, 0, 0, 0)) == 1352
    assert len(u.montar_status(10, 100)) == 1239


def test_decodifica_o_carro_do_jogador() -> None:
    tipo, v = u.decodificar(u.montar_telemetria(287, 0.75, 7, 11250, 104, jogador=5))
    assert tipo == "telemetria"
    assert v == {"velocidade": 287.0, "acelerador": 75.0, "marcha": 7.0, "rpm": 11250.0,
                 "temp_motor": 104.0}
    assert u.decodificar(u.montar_telemetria(0, 0, -1, 4000, 90))[1]["marcha"] == -1  # ré
    tipo, v = u.decodificar(u.montar_status(27.5, 110.0, jogador=19))
    assert tipo == "status" and v["combustivel_nivel"] == pytest.approx(25.0)


@pytest.mark.parametrize("dados, motivo", [
    (b"\x00" * 10, "curto"),
    (u.montar_telemetria(1, 0, 1, 1, 1, formato=2023), "formato_2023"),
    (u.montar_telemetria(1, 0, 1, 1, 1)[:-1], "tamanho_6_1351"),
    (u.montar_cabecalho(0) + b"\x00" * 1320, "id_0"),            # movimento: não usado
    (u.montar_status(1, 0), "status"),                            # capacidade 0: sem valor
])
def test_ignora_o_que_nao_e_do_f1_24(dados: bytes, motivo: str) -> None:
    tipo, valores = u.decodificar(dados)
    assert tipo == motivo and valores == {}


def _gravar_corrida(caminho: Path) -> list[tuple[int, float, int, int, int]]:
    voltas = [(80 + i, i / 40, 3 + i // 15, 9000 + 50 * i, 95 + i // 10) for i in range(40)]
    with u.GravadorPacotes(str(caminho)) as g:
        for i, (vel, acel, marcha, rpm, temp) in enumerate(voltas):
            g.gravar(u.montar_telemetria(vel, acel, marcha, rpm, temp, jogador=3), t=i / 60)
            if i % 10 == 0:
                g.gravar(u.montar_status(100 - i, 110, jogador=3), t=i / 60)
            g.gravar(u.montar_cabecalho(0, 3) + b"\x00" * 1320, t=i / 60)   # ruído
    return voltas


def test_pacotes_gravados_dao_os_valores_certos(tmp_path: Path) -> None:
    arq = tmp_path / "corrida.udp"
    voltas = _gravar_corrida(arq)
    pacotes = list(u.ler_pacotes(str(arq)))
    assert len(pacotes) == 40 + 4 + 40 and pacotes[1][0] == 0.0
    leituras = [v for t, d in pacotes for tipo, v in [u.decodificar(d)] if tipo == "telemetria"]
    assert len(leituras) == 40
    for (vel, acel, marcha, rpm, temp), v in zip(voltas, leituras):
        assert v["velocidade"] == vel and v["marcha"] == marcha and v["rpm"] == rpm
        assert v["temp_motor"] == temp and v["acelerador"] == pytest.approx(acel * 100, abs=1e-4)
    # Gravação cortada no meio de um pacote: lê até o último inteiro.
    dados = arq.read_bytes()
    (tmp_path / "cortada.udp").write_bytes(dados[:-100])
    assert len(list(u.ler_pacotes(str(tmp_path / "cortada.udp")))) == 83
    (tmp_path / "outro.bin").write_bytes(b"qualquer")
    with pytest.raises(ValueError):
        list(u.ler_pacotes(str(tmp_path / "outro.bin")))


def test_fonte_recebe_pela_rede_e_grava(tmp_path: Path) -> None:
    arq = tmp_path / "rede.udp"
    fonte = u.FonteUDPF1(porta=0, endereco="127.0.0.1", gravar_em=str(arq))
    with fonte:
        envio = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        envio.sendto(u.montar_status(55, 110), ("127.0.0.1", fonte.porta))
        envio.sendto(u.montar_telemetria(312, 1.0, 8, 11800, 108), ("127.0.0.1", fonte.porta))
        envio.sendto(b"lixo", ("127.0.0.1", fonte.porta))
        fim = time.monotonic() + 3
        while fonte.leituras < 1 and time.monotonic() < fim:
            time.sleep(0.01)
        time.sleep(0.1)
        envio.close()
    assert fonte.erro is None and not fonte.ativa
    v = fonte.ultima().valores
    assert v["velocidade"] == 312 and v["marcha"] == 8 and v["combustivel_nivel"] == 50.0
    assert fonte.contagem == {"status": 1, "telemetria": 1, "curto": 1}
    assert len(list(u.ler_pacotes(str(arq)))) == 3       # grava também o que ignora


def test_fim_da_sessao_zera_os_mostradores() -> None:
    fonte = u.FonteUDPF1(porta=0, endereco="127.0.0.1")
    with fonte:
        envio = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        envio.sendto(u.montar_status(55, 110), ("127.0.0.1", fonte.porta))
        envio.sendto(u.montar_telemetria(250, 0.9, 6, 10500, 101), ("127.0.0.1", fonte.porta))
        envio.close()
        fim = time.monotonic() + 4
        while fonte.contagem["repouso"] < 1 and time.monotonic() < fim:
            time.sleep(0.02)
    v = fonte.ultima().valores
    assert fonte.contagem["repouso"] == 1 and fonte.leituras == 2
    assert (v["rpm"], v["velocidade"], v["marcha"], v["acelerador"]) == (0, 0, 0, 0)
    assert v["temp_motor"] == 101 and v["combustivel_nivel"] == 50.0
