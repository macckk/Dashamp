"""Testes da FonteGT7 (F2.7b): cifra Salsa20, campos, gravação e heartbeat."""
from __future__ import annotations

import socket
import struct
import threading
import time
from pathlib import Path

import pytest

from painel.fontes import gt7
from painel.fontes.udp_f1 import GravadorPacotes, ler_pacotes


def test_pacote_cifrado_decodifica() -> None:
    p = gt7.montar_pacote(6543.5, 187.2, 4, 255, 92.0, combustivel=30, capacidade=60, sugerida=3)
    assert len(p) == 0x128
    assert struct.unpack_from("<I", p, 0)[0] != gt7.ASSINATURA        # está mesmo cifrado
    tipo, v = gt7.decodificar(p)
    assert tipo == "gt7"
    assert v["rpm"] == pytest.approx(6543.5) and v["velocidade"] == pytest.approx(187.2, abs=1e-3)
    assert v["marcha"] == 4 and v["acelerador"] == pytest.approx(100.0)  # nibble alto ignorado
    assert v["temp_motor"] == 92.0 and v["combustivel_nivel"] == pytest.approx(50.0)


def test_iv_diferente_a_cada_pacote() -> None:
    a = gt7.montar_pacote(1000, 10, 1, 0, 80, iv1=1)
    b = gt7.montar_pacote(1000, 10, 1, 0, 80, iv1=2)
    assert a != b and gt7.decodificar(a)[1] == gt7.decodificar(b)[1]


@pytest.mark.parametrize("dados, motivo", [
    (b"A", "tamanho"),
    (bytes(0x128), "assinatura"),
    (gt7.montar_pacote(1, 1, 1, 1, 1)[:-1], "tamanho"),
    (gt7.montar_pacote(5000, 100, 3, 50, 90, flags=gt7.FLAG_NA_PISTA | gt7.FLAG_PAUSADO),
     "pausado"),
    (gt7.montar_pacote(0, 0, 0, 0, 90, flags=gt7.FLAG_NA_PISTA | gt7.FLAG_CARREGANDO),
     "carregando"),
    (gt7.montar_pacote(5000, 100, 3, 50, 90, flags=0), "fora_da_pista"),
])
def test_ignora_o_que_nao_serve(dados: bytes, motivo: str) -> None:
    assert gt7.decodificar(dados) == (motivo, {})


def test_corrompido_nao_passa() -> None:
    p = bytearray(gt7.montar_pacote(1, 1, 1, 1, 1))
    p[0x41] ^= 0xFF                                                   # IV errado: lixo
    assert gt7.decodificar(bytes(p))[0] == "assinatura"


def test_pacotes_gravados(tmp_path: Path) -> None:
    arq = tmp_path / "gt7.udp"
    esperado = [(800 + 50 * i, i * 2.0, 1 + i // 10, i * 6, 70 + i // 5) for i in range(40)]
    with GravadorPacotes(str(arq)) as g:
        for i, (rpm, vel, marcha, acel, agua) in enumerate(esperado):
            g.gravar(gt7.montar_pacote(rpm, vel, marcha, acel, agua, iv1=1000 + i), t=i / 60)
    lidos = [gt7.decodificar(d)[1] for _, d in ler_pacotes(str(arq))]
    for (rpm, vel, marcha, acel, agua), v in zip(esperado, lidos):
        assert v["rpm"] == rpm and v["marcha"] == marcha and v["temp_motor"] == agua
        assert v["velocidade"] == pytest.approx(vel, abs=1e-3)
        assert v["acelerador"] == pytest.approx(acel / 2.55)


def test_alvos_da_descoberta() -> None:
    alvos = gt7.alvos_descoberta("192.168.7.20")
    assert alvos[:2] == ["255.255.255.255", "192.168.7.255"]
    assert len(alvos) == 2 + 253 and "192.168.7.20" not in alvos and "192.168.7.1" in alvos
    assert gt7.alvos_descoberta(None) == ["255.255.255.255"]


def test_heartbeat_e_recepcao(tmp_path: Path) -> None:
    """PS5 falso em 127.0.0.1: só manda dados depois do heartbeat, para quem o mandou."""
    ps5 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ps5.bind(("127.0.0.1", 0))
    ps5.settimeout(0.05)
    heartbeats: list[tuple[str, int]] = []
    parar = threading.Event()

    def console() -> None:
        while not parar.is_set():
            try:
                dados, origem = ps5.recvfrom(16)
            except socket.timeout:
                continue
            if dados == b"A":
                heartbeats.append(origem)
                for i in range(5):
                    ps5.sendto(gt7.montar_pacote(4000 + i, 120, 3, 128, 88, iv1=i), origem)

    t = threading.Thread(target=console, daemon=True)
    t.start()
    arq = tmp_path / "rx.udp"
    fonte = gt7.FonteGT7(ps5="127.0.0.1", porta_ps5=ps5.getsockname()[1], porta_local=0,
                         endereco="127.0.0.1", gravar_em=str(arq))
    with fonte:
        fim = time.monotonic() + 3
        while fonte.leituras < 5 and time.monotonic() < fim:
            time.sleep(0.01)
    parar.set()
    t.join(1)
    ps5.close()
    assert heartbeats and heartbeats[0][1] == fonte.porta_local
    assert fonte.erro is None and fonte.contagem["gt7"] >= 5
    v = fonte.ultima().valores
    assert v["marcha"] == 3 and v["velocidade"] == pytest.approx(120, abs=1e-3)
    assert len(list(ler_pacotes(str(arq)))) >= 5


def test_fim_da_corrida_zera_os_mostradores() -> None:
    """Carro na pista, depois pausa (repouso na hora), depois volta e para de mandar (silêncio)."""
    ps5 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ps5.bind(("127.0.0.1", 0))
    ps5.settimeout(0.05)
    parar = threading.Event()
    rodando = gt7.montar_pacote(6000, 150, 4, 200, 91, combustivel=20, capacidade=80)
    pausado = gt7.montar_pacote(6000, 150, 4, 200, 91,
                                flags=gt7.FLAG_NA_PISTA | gt7.FLAG_PAUSADO)
    roteiro = [[rodando] * 3, [pausado], [rodando] * 3]          # um item por heartbeat

    def console() -> None:
        while not parar.is_set():
            try:
                dados, origem = ps5.recvfrom(16)
            except socket.timeout:
                continue
            if dados == b"A" and roteiro:
                for pacote in roteiro.pop(0):
                    ps5.sendto(pacote, origem)

    t = threading.Thread(target=console, daemon=True)
    t.start()
    fonte = gt7.FonteGT7(ps5="127.0.0.1", porta_ps5=ps5.getsockname()[1], porta_local=0,
                         endereco="127.0.0.1")

    def esperar(condicao, s: float = 4.0) -> None:
        fim = time.monotonic() + s
        while not condicao() and time.monotonic() < fim:
            time.sleep(0.01)

    with fonte:
        esperar(lambda: fonte.contagem["gt7"] >= 3)
        assert fonte.ultima().valores["rpm"] == 6000
        esperar(lambda: fonte.contagem["repouso"] >= 1)
        v = fonte.ultima().valores
        assert fonte.contagem["pausado"] == 1                    # zerou pela pausa
        assert (v["rpm"], v["velocidade"], v["marcha"], v["acelerador"]) == (0, 0, 0, 0)
        assert v["temp_motor"] == 91 and v["combustivel_nivel"] == 25   # esses ficam
        esperar(lambda: fonte.contagem["gt7"] >= 6)
        assert fonte.ultima().valores["rpm"] == 6000
        esperar(lambda: fonte.contagem["repouso"] >= 2)          # silêncio de 1,5 s
        assert fonte.ultima().valores["velocidade"] == 0
    parar.set()
    t.join(1)
    ps5.close()
    assert fonte.erro is None and fonte.contagem["repouso"] == 2
