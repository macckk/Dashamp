"""Fonte do Gran Turismo 7 (F2.7b): telemetria do PS5 pela rede.

O GT7 não tem especificação oficial; o protocolo abaixo é o descoberto pela comunidade (usado
por vários painéis abertos) e é o que a corrida da F2.8 vai confirmar:

- O PS5 só manda dados a quem pede: o Eee PC envia um "heartbeat" (o byte b"A") para a porta
  UDP **33739** do PS5, e o PS5 responde para a porta **33740** de quem pediu, ~60 pacotes/s.
  O heartbeat precisa ser repetido (fazemos a cada 1 s) senão o PS5 para depois de ~100 pacotes.
- Cada pacote tem 296 bytes (0x128) cifrados com **Salsa20**: chave = os 32 primeiros bytes de
  "Simulator Interface Packet GT7 ver 0.0"; o IV vem dos bytes 0x40..0x43 do pacote (uint32
  little-endian, `iv1`) e o nonce de 8 bytes é `iv1 ^ 0xDEADBEAF` seguido de `iv1`. Decifrado,
  o pacote começa com a assinatura 0x47375330 ("0S7G" em little-endian).
- Campos usados (little-endian): 0x3C rpm (float), 0x44 combustível (float, litros),
  0x48 capacidade do tanque (float), 0x4C velocidade (float, m/s), 0x58 temperatura da água
  (float, °C), 0x8E flags (uint16; bit 0 = carro na pista, bit 1 = pausado), 0x90 marcha
  (uint8; nibble baixo = marcha atual, alto = sugerida), 0x91 acelerador (uint8, 0..255).

**Descoberta do PS5** (para não precisar digitar IP no Eee PC): enquanto não chega nada, o
heartbeat vai para o broadcast da rede e para cada endereço da sub-rede (/24, 254 pacotes de
1 byte a cada 3 s); o primeiro que responder é o PS5, e daí em diante o heartbeat vai só para ele.
Com `ps5="192.168.x.y"` a descoberta é pulada.

O gravador de pacotes é o mesmo da fonte do F1 (`udp_f1.GravadorPacotes`, pacotes cifrados como
chegaram).

    python -m painel.fontes.gt7 [--ps5 IP] [--gravar ARQ]     # escuta e imprime
    python -m painel.fontes.gt7 --simular-ps5                  # finge ser um PS5 (testes)
"""
from __future__ import annotations

import argparse
import ipaddress
import math
import socket
import struct
import time
from collections import Counter

try:  # Debian (python3-pycryptodome) usa o nome Cryptodome; o pip, Crypto
    from Cryptodome.Cipher import Salsa20
except ImportError:  # pragma: no cover - depende da instalação
    from Crypto.Cipher import Salsa20

from painel.fontes.base import Fonte
from painel.fontes.udp_f1 import GravadorPacotes

PORTA_PS5, PORTA_LOCAL = 33739, 33740
CHAVE = b"Simulator Interface Packet GT7 ver 0.0"[:32]
XOR_IV = 0xDEADBEAF
TAMANHO = 0x128
ASSINATURA = 0x47375330
HEARTBEAT = b"A"
INTERVALO_HEARTBEAT_S = 1.0
INTERVALO_DESCOBERTA_S = 3.0

FLAG_NA_PISTA, FLAG_PAUSADO = 0x1, 0x2


def _nonce(iv1: int) -> bytes:
    return struct.pack("<II", iv1 ^ XOR_IV, iv1)


def decifrar(dados: bytes) -> bytes | None:
    """Pacote decifrado, ou None se não for um pacote do GT7."""
    if len(dados) != TAMANHO:
        return None
    iv1 = struct.unpack_from("<I", dados, 0x40)[0]
    claro = Salsa20.new(key=CHAVE, nonce=_nonce(iv1)).decrypt(dados)
    if struct.unpack_from("<I", claro, 0)[0] != ASSINATURA:
        return None
    return claro


def decodificar(dados: bytes) -> tuple[str, dict[str, float]]:
    """('gt7', valores) ou (motivo, {}) para o que não serve."""
    claro = decifrar(dados)
    if claro is None:
        return ("tamanho" if len(dados) != TAMANHO else "assinatura"), {}
    flags = struct.unpack_from("<H", claro, 0x8E)[0]
    if flags & FLAG_PAUSADO:
        return "pausado", {}
    rpm, = struct.unpack_from("<f", claro, 0x3C)
    tanque, capacidade, vel = struct.unpack_from("<fff", claro, 0x44)
    agua, = struct.unpack_from("<f", claro, 0x58)
    marcha_byte, acel = claro[0x90], claro[0x91]
    valores = {"rpm": float(rpm), "velocidade": float(vel) * 3.6,
               "marcha": float(marcha_byte & 0x0F), "acelerador": acel * 100.0 / 255.0,
               "temp_motor": float(agua)}
    if capacidade > 0:
        valores["combustivel_nivel"] = 100.0 * tanque / capacidade
    if not all(math.isfinite(v) for v in valores.values()):
        return "invalido", {}
    return "gt7", valores


def montar_pacote(rpm: float, velocidade_kmh: float, marcha: int, acelerador: int,
                  temp_agua: float, combustivel: float = 40.0, capacidade: float = 80.0,
                  flags: int = FLAG_NA_PISTA, iv1: int = 0x1234567, sugerida: int = 0) -> bytes:
    """Pacote cifrado como o PS5 manda (para testes e para o simulador de PS5)."""
    claro = bytearray(TAMANHO)
    struct.pack_into("<I", claro, 0, ASSINATURA)
    struct.pack_into("<f", claro, 0x3C, rpm)
    struct.pack_into("<fff", claro, 0x44, combustivel, capacidade, velocidade_kmh / 3.6)
    struct.pack_into("<f", claro, 0x58, temp_agua)
    struct.pack_into("<f", claro, 0x5C, temp_agua + 10)            # óleo: não usado
    struct.pack_into("<H", claro, 0x8E, flags)
    claro[0x90] = (sugerida << 4) | (marcha & 0x0F)
    claro[0x91] = acelerador
    cifrado = bytearray(Salsa20.new(key=CHAVE, nonce=_nonce(iv1)).encrypt(bytes(claro)))
    struct.pack_into("<I", cifrado, 0x40, iv1)                     # o IV vai em claro
    return bytes(cifrado)


# --- a fonte ---------------------------------------------------------------------------


def _ip_local() -> str | None:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        return None if ip.startswith("127.") else ip
    except OSError:
        return None
    finally:
        s.close()


def alvos_descoberta(ip_local: str | None) -> list[str]:
    """Broadcast geral, broadcast da /24 e cada endereço da /24 (menos o próprio)."""
    alvos = ["255.255.255.255"]
    if ip_local:
        rede = ipaddress.ip_network(f"{ip_local}/24", strict=False)
        alvos.append(str(rede.broadcast_address))
        alvos += [str(h) for h in rede.hosts() if str(h) != ip_local]
    return alvos


class FonteGT7(Fonte):
    """`ps5`: IP do console (None = descobrir). `porta_ps5`/`porta_local` mudam só em testes."""

    def __init__(self, ps5: str | None = None, gravar_em: str | None = None,
                 porta_ps5: int = PORTA_PS5, porta_local: int = PORTA_LOCAL,
                 endereco: str = "0.0.0.0") -> None:
        super().__init__()
        self.ps5 = ps5
        self.gravar_em = gravar_em
        self.porta_ps5, self.porta_local, self.endereco = porta_ps5, porta_local, endereco
        self.contagem: Counter[str] = Counter()
        self._sock: socket.socket | None = None

    @property
    def procurando(self) -> bool:
        return self.ps5 is None

    def iniciar(self) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1 << 20)
        self._sock.bind((self.endereco, self.porta_local))
        self._sock.settimeout(0.1)
        self.porta_local = self._sock.getsockname()[1]
        super().iniciar()

    def _heartbeat(self, agora: float, prox: dict[str, float]) -> None:
        assert self._sock is not None
        if self.ps5 is not None:
            if agora >= prox["hb"]:
                prox["hb"] = agora + INTERVALO_HEARTBEAT_S
                self._enviar(self.ps5)
        elif agora >= prox["desc"]:
            prox["desc"] = agora + INTERVALO_DESCOBERTA_S
            for alvo in alvos_descoberta(_ip_local()):
                self._enviar(alvo)

    def _enviar(self, alvo: str) -> None:
        try:
            self._sock.sendto(HEARTBEAT, (alvo, self.porta_ps5))  # type: ignore[union-attr]
        except OSError:
            self.contagem["erro_envio"] += 1                     # sem rede: tenta de novo depois

    def _rodar(self) -> None:
        assert self._sock is not None
        gravador = GravadorPacotes(self.gravar_em) if self.gravar_em else None
        prox = {"hb": 0.0, "desc": 0.0}
        estado: dict[str, float] = {}
        ultimo_dado = 0.0
        try:
            while not self._parar.is_set():
                agora = time.monotonic()
                if self.ps5 is not None and ultimo_dado and agora - ultimo_dado > 10:
                    self.contagem["perdido"] += 1                 # console sumiu: procura de novo
                    self.ps5, ultimo_dado = None, 0.0
                self._heartbeat(agora, prox)
                try:
                    dados, (origem, _porta) = self._sock.recvfrom(2048)
                except socket.timeout:
                    continue
                except OSError:
                    continue
                if gravador is not None:
                    gravador.gravar(dados)
                tipo, valores = decodificar(dados)
                self.contagem[tipo] += 1
                if tipo in ("gt7", "pausado"):
                    if self.ps5 is None:                          # achou o console
                        self.ps5 = origem
                        prox["hb"] = 0.0
                    ultimo_dado = agora
                if valores:
                    estado.update(valores)
                    self._publicar(estado)
        finally:
            if gravador is not None:
                gravador.fechar()
            self._sock.close()


# --- simulador de PS5 (testes sem o console) ------------------------------------------------


def simular_ps5(porta: int = PORTA_PS5, segundos: float = 0.0, hz: float = 60.0) -> int:
    """Responde a heartbeats como o PS5: manda pacotes cifrados da FonteSimulada a quem pediu,
    enquanto os heartbeats continuarem chegando. Devolve quantos pacotes mandou."""
    from painel.fontes.simulada import Carro

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", porta))
    s.settimeout(1.0 / hz)
    carro = Carro(semente=3, temp_inicial=70)
    clientes: dict[tuple[str, int], float] = {}
    enviados, iv, t0 = 0, 1, time.monotonic()
    proximo = t0
    try:
        while not segundos or time.monotonic() - t0 < segundos:
            try:
                dados, (ip, _p) = s.recvfrom(64)
                if dados == HEARTBEAT and (ip, PORTA_LOCAL) not in clientes:
                    print(f"heartbeat de {ip}: mandando telemetria para {ip}:{PORTA_LOCAL}",
                          flush=True)
                if dados == HEARTBEAT:
                    clientes[(ip, PORTA_LOCAL)] = time.monotonic()
            except socket.timeout:
                pass
            agora = time.monotonic()
            if agora < proximo:
                continue
            proximo += 1.0 / hz
            carro.passo(1.0 / hz)
            v = carro.valores()
            pacote = montar_pacote(v["rpm"], v["velocidade"], int(v["marcha"]),
                                   round(v["acelerador"] * 2.55), v["temp_motor"],
                                   combustivel=v["combustivel_nivel"] * 0.8, capacidade=80.0,
                                   iv1=iv)
            iv = (iv * 1103515245 + 12345) & 0xFFFFFFFF
            for destino, visto in list(clientes.items()):
                if agora - visto > 5:                         # sem heartbeat: para (como o PS5)
                    del clientes[destino]
                    continue
                s.sendto(pacote, destino)
                enviados += 1
    except KeyboardInterrupt:
        pass
    s.close()
    return enviados


def main() -> None:
    p = argparse.ArgumentParser(description="Telemetria do GT7 (PS5).")
    p.add_argument("--ps5", help="IP do PS5 (sem isto, procura na rede)")
    p.add_argument("--gravar", metavar="ARQ", help="grava os pacotes brutos")
    p.add_argument("--segundos", type=float, default=0)
    p.add_argument("--simular-ps5", action="store_true", help="finge ser um PS5 com o GT7")
    a = p.parse_args()
    if a.simular_ps5:
        print("simulando um PS5: esperando heartbeat na porta UDP 33739", flush=True)
        print(f"{simular_ps5(segundos=a.segundos)} pacotes enviados")
        return
    fonte = FonteGT7(a.ps5, gravar_em=a.gravar)
    fonte.iniciar()
    t0 = time.monotonic()
    try:
        while not a.segundos or time.monotonic() - t0 < a.segundos:
            time.sleep(1)
            u = fonte.ultima()
            print(f"PS5 {fonte.ps5 or '(procurando)'}", dict(fonte.contagem),
                  {k: round(v, 1) for k, v in u.valores.items()} if u else "", flush=True)
    except KeyboardInterrupt:
        pass
    fonte.parar()


if __name__ == "__main__":
    main()
