"""Fonte UDP do F1 24 (F2.7): telemetria do jogo pela rede, porta 20777.

Formato do F1 24 (pacotes little-endian, sem preenchimento entre campos). O fórum da EA com a
especificação oficial recusou acesso automático; o layout abaixo foi conferido com um cliente
de terceiros para o F1 24 e bate com os tamanhos de pacote da especificação. Por isso o
decodificador confere `m_packetFormat == 2024` e o tamanho exato de cada pacote, e só conta (não
quebra) o que não bater.

    PacketHeader (29 bytes): uint16 m_packetFormat, uint8 m_gameYear, uint8 m_gameMajorVersion,
        uint8 m_gameMinorVersion, uint8 m_packetVersion, uint8 m_packetId, uint64 m_sessionUID,
        float m_sessionTime, uint32 m_frameIdentifier, uint32 m_overallFrameIdentifier,
        uint8 m_playerCarIndex, uint8 m_secondaryPlayerCarIndex
    Car Telemetry (id 6, 1352 bytes): cabeçalho + 22 × CarTelemetryData (60 bytes) +
        uint8 m_mfdPanelIndex, uint8 m_mfdPanelIndexSecondaryPlayer, int8 m_suggestedGear
      CarTelemetryData: uint16 m_speed (km/h), float m_throttle (0..1), float m_steer,
        float m_brake, uint8 m_clutch, int8 m_gear (-1 = R, 0 = N), uint16 m_engineRPM,
        uint8 m_drs, uint8 m_revLightsPercent, uint16 m_revLightsBitValue,
        uint16 m_brakesTemperature[4], uint8 m_tyresSurfaceTemperature[4],
        uint8 m_tyresInnerTemperature[4], uint16 m_engineTemperature (°C),
        float m_tyresPressure[4], uint8 m_surfaceType[4]
    Car Status (id 7, 1239 bytes): cabeçalho + 22 × CarStatusData (55 bytes); daqui só
        float m_fuelInTank e float m_fuelCapacity (deslocamentos 5 e 9 dentro do carro).

Canais produzidos: rpm, velocidade, marcha, acelerador, temp_motor (telemetria) e
combustivel_nivel (status). Cada pacote de telemetria publica uma leitura.

Gravador de pacotes brutos (para testes offline, sem o jogo): arquivo com a assinatura
`DASHUDP1` e registros `<d t><H tamanho><bytes>`.

    python -m painel.fontes.udp_f1 --gravar /tmp/corrida.udp       # grava o que chegar
    python -m painel.fontes.udp_f1 --enviar /tmp/corrida.udp --destino 192.168.x.y
                                                                   # reproduz pela rede
"""
from __future__ import annotations

import argparse
import socket
import struct
import time
from collections import Counter
from collections.abc import Iterator

from painel.fontes.base import REPOUSO, SILENCIO_REPOUSO_S, Fonte

PORTA = 20777
FORMATO = 2024
CABECALHO = struct.Struct("<HBBBBBQfIIBB")
assert CABECALHO.size == 29
CARROS = 22
TELEMETRIA = struct.Struct("<HfffBbHBBH4H4B4BH4f4B")
assert TELEMETRIA.size == 60
TAM_STATUS_CARRO = 55
COMBUSTIVEL = struct.Struct("<ff")             # m_fuelInTank, m_fuelCapacity
DESLOC_COMBUSTIVEL = 5
ID_TELEMETRIA, ID_STATUS = 6, 7
TAMANHOS = {ID_TELEMETRIA: CABECALHO.size + CARROS * TELEMETRIA.size + 3,     # 1352
            ID_STATUS: CABECALHO.size + CARROS * TAM_STATUS_CARRO}            # 1239
ASSINATURA = b"DASHUDP1"
REGISTRO = struct.Struct("<dH")


def decodificar(dados: bytes) -> tuple[str, dict[str, float]]:
    """('telemetria' | 'status', valores) ou (motivo, {}) para pacotes ignorados."""
    if len(dados) < CABECALHO.size:
        return "curto", {}
    cab = CABECALHO.unpack_from(dados)
    formato, pid, jogador = cab[0], cab[5], cab[10]
    if formato != FORMATO:
        return f"formato_{formato}", {}
    if pid not in TAMANHOS:
        return f"id_{pid}", {}                  # outros pacotes: não usamos
    if len(dados) != TAMANHOS[pid] or jogador >= CARROS:
        return f"tamanho_{pid}_{len(dados)}", {}
    if pid == ID_TELEMETRIA:
        c = TELEMETRIA.unpack_from(dados, CABECALHO.size + jogador * TELEMETRIA.size)
        # c: 0 speed, 1 throttle, 2 steer, 3 brake, 4 clutch, 5 gear, 6 rpm, ...,
        #    22 engineTemperature (depois de 4 + 4 + 4 itens de pneus/freios)
        return "telemetria", {"velocidade": float(c[0]), "acelerador": c[1] * 100.0,
                              "marcha": float(c[5]), "rpm": float(c[6]),
                              "temp_motor": float(c[22])}
    tanque, capacidade = COMBUSTIVEL.unpack_from(
        dados, CABECALHO.size + jogador * TAM_STATUS_CARRO + DESLOC_COMBUSTIVEL)
    if capacidade <= 0:
        return "status", {}
    return "status", {"combustivel_nivel": 100.0 * tanque / capacidade}


# --- pacotes de teste (mesmo layout) ---------------------------------------------------------


def montar_cabecalho(pid: int, jogador: int = 0, formato: int = FORMATO,
                     tempo: float = 0.0, quadro: int = 0) -> bytes:
    return CABECALHO.pack(formato, 24, 1, 0, 1, pid, 0x1234ABCD, tempo, quadro, quadro,
                          jogador, 255)


def montar_telemetria(velocidade: int, acelerador: float, marcha: int, rpm: int,
                      temp_motor: int, jogador: int = 0, **cab) -> bytes:
    carros = []
    for i in range(CARROS):
        if i == jogador:
            carros.append(TELEMETRIA.pack(velocidade, acelerador, 0.0, 0.0, 0, marcha, rpm, 0,
                                          50, 0, 400, 400, 400, 400, 90, 90, 90, 90, 95, 95,
                                          95, 95, temp_motor, 23.0, 23.0, 21.5, 21.5,
                                          0, 0, 0, 0))
        else:  # outros carros com valores diferentes, para pegar deslocamento errado
            carros.append(TELEMETRIA.pack(300, 1.0, 0.0, 0.0, 0, 8, 12000, 0, 0, 0,
                                          *[0] * 4, *[0] * 4, *[0] * 4, 130, *[0.0] * 4,
                                          *[0] * 4))
    return montar_cabecalho(ID_TELEMETRIA, jogador, **cab) + b"".join(carros) + \
        struct.pack("<BBb", 255, 255, 0)


def montar_status(tanque: float, capacidade: float, jogador: int = 0, **cab) -> bytes:
    carros = []
    for i in range(CARROS):
        t, c = (tanque, capacidade) if i == jogador else (1.0, 110.0)
        carros.append(struct.pack("<5B", 0, 1, 1, 56, 0) + COMBUSTIVEL.pack(t, c)
                      + b"\x00" * (TAM_STATUS_CARRO - 5 - COMBUSTIVEL.size))
    return montar_cabecalho(ID_STATUS, jogador, **cab) + b"".join(carros)


# --- gravação de pacotes brutos ---------------------------------------------------------


class GravadorPacotes:
    def __init__(self, caminho: str) -> None:
        self._arq = open(caminho, "wb")  # noqa: SIM115 — fechado em fechar()
        self._arq.write(ASSINATURA)
        self._t0 = time.monotonic()
        self.pacotes = 0

    def gravar(self, dados: bytes, t: float | None = None) -> None:
        self._arq.write(REGISTRO.pack(time.monotonic() - self._t0 if t is None else t,
                                      len(dados)) + dados)
        self.pacotes += 1

    def fechar(self) -> None:
        self._arq.close()

    def __enter__(self) -> GravadorPacotes:
        return self

    def __exit__(self, *_: object) -> None:
        self.fechar()


def ler_pacotes(caminho: str) -> Iterator[tuple[float, bytes]]:
    with open(caminho, "rb") as arq:
        if arq.read(len(ASSINATURA)) != ASSINATURA:
            raise ValueError(f"{caminho}: não é uma gravação de pacotes do Dashamp")
        while True:
            cab = arq.read(REGISTRO.size)
            if len(cab) < REGISTRO.size:
                return
            t, n = REGISTRO.unpack(cab)
            dados = arq.read(n)
            if len(dados) < n:
                return                           # gravação cortada no meio: para aqui
            yield t, dados


# --- a fonte ------------------------------------------------------------------------


class FonteUDPF1(Fonte):
    """Escuta a porta, decodifica e publica uma leitura por pacote de telemetria do jogador.
    `gravar_em`: grava também os pacotes brutos (todos, inclusive os ignorados)."""

    def __init__(self, porta: int = PORTA, endereco: str = "0.0.0.0",
                 gravar_em: str | None = None) -> None:
        super().__init__()
        self.porta, self.endereco, self.gravar_em = porta, endereco, gravar_em
        self.contagem: Counter[str] = Counter()
        self._sock: socket.socket | None = None

    def iniciar(self) -> None:
        # O socket é aberto aqui (e não na thread) para um erro de porta ocupada aparecer já.
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Folga para ~1 s de pacotes se o processo travar (ex.: gravando uma captura); o kernel
        # limita ao net.core.rmem_max (180 kB no Eee PC, ~75 pacotes).
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1 << 20)
        self._sock.bind((self.endereco, self.porta))
        self._sock.settimeout(0.2)              # acorda para ver se é hora de parar
        self.porta = self._sock.getsockname()[1]  # porta 0 = qualquer livre (testes)
        super().iniciar()

    def _rodar(self) -> None:
        assert self._sock is not None
        gravador = GravadorPacotes(self.gravar_em) if self.gravar_em else None
        estado: dict[str, float] = {}
        ultima_telemetria = 0.0
        repouso = True
        try:
            while not self._parar.is_set():
                if not repouso and time.monotonic() - ultima_telemetria > SILENCIO_REPOUSO_S:
                    repouso = True                    # fim da sessão: o jogo para de mandar
                    self.contagem["repouso"] += 1
                    estado.update(REPOUSO)
                    self._publicar(estado)
                try:
                    dados = self._sock.recv(2048)
                except socket.timeout:
                    continue
                if gravador is not None:
                    gravador.gravar(dados)
                tipo, valores = decodificar(dados)
                self.contagem[tipo] += 1
                if valores:
                    estado.update(valores)
                    if tipo == "telemetria":
                        ultima_telemetria, repouso = time.monotonic(), False
                        self._publicar(estado)
        finally:
            if gravador is not None:
                gravador.fechar()
            self._sock.close()


def enviar(caminho: str, destino: str, porta: int = PORTA, velocidade: float = 1.0) -> int:
    """Reproduz uma gravação pela rede, no ritmo original (÷ velocidade)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    t0 = time.monotonic()
    n = 0
    for t, dados in ler_pacotes(caminho):
        espera = t / velocidade - (time.monotonic() - t0)
        if espera > 0:
            time.sleep(espera)
        s.sendto(dados, (destino, porta))
        n += 1
    s.close()
    return n


def main() -> None:
    p = argparse.ArgumentParser(description="Telemetria UDP do F1 24: grava ou reproduz pacotes.")
    p.add_argument("--porta", type=int, default=PORTA)
    p.add_argument("--gravar", metavar="ARQ", help="escuta e grava os pacotes brutos")
    p.add_argument("--segundos", type=float, default=0, help="com --gravar: para depois de S s")
    p.add_argument("--enviar", metavar="ARQ", help="reproduz uma gravação pela rede")
    p.add_argument("--destino", default="127.0.0.1")
    p.add_argument("--velocidade", type=float, default=1.0)
    a = p.parse_args()
    if a.enviar:
        print(f"{enviar(a.enviar, a.destino, a.porta, a.velocidade)} pacotes enviados")
        return
    fonte = FonteUDPF1(a.porta, gravar_em=a.gravar)
    fonte.iniciar()
    print(f"escutando UDP {a.porta}{' e gravando em ' + a.gravar if a.gravar else ''}; Ctrl+C para",
          flush=True)
    t0 = time.monotonic()
    try:
        while not a.segundos or time.monotonic() - t0 < a.segundos:
            time.sleep(1)
            u = fonte.ultima()
            print(dict(fonte.contagem), {k: round(v, 1) for k, v in u.valores.items()} if u else "",
                  flush=True)
    except KeyboardInterrupt:
        pass
    fonte.parar()


if __name__ == "__main__":
    main()
