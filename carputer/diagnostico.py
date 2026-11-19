"""Diagnóstico do carro pelo OBD-II (preparação da F3.3): relatório para `docs/carro.md`.

Liga no ELM327, descobre o protocolo e os PIDs que o carro tem, lê cada um uma vez (com o tempo
de resposta), mede a taxa de leitura do rpm sozinho e a do painel (agenda completa da FonteOBD)
e lista os códigos de erro. O relatório vai para `~/dashamp/.dados/diagnosticos/` (o deploy não
apaga essa pasta) e aparece na tela.

Privacidade: do VIN (chassi) ficam só o fabricante (3 primeiros caracteres) e o código do ano
(10.º); o número inteiro identificaria o carro e nunca é gravado.

    python -m carputer.diagnostico [--porta /dev/ttyUSB0] [--baud 38400]   # tela (Eee PC, F5)
    python -m painel.fontes.obd --diagnostico [--porta ...]                # só texto
"""
from __future__ import annotations

import os
import statistics
import threading
import time
from collections.abc import Callable
from datetime import datetime

from painel.fontes.obd import TIPOS_ERRO, ConexaoPythonOBD, FabricaConexao, FonteOBD

PASTA = os.path.expanduser("~/dashamp/.dados/diagnosticos")
ESPERA_ADAPTADOR_S = 120.0       # tempo procurando o adaptador antes de desistir
SEGUNDOS_RPM = 10.0
SEGUNDOS_PAINEL = 20.0

Avisar = Callable[[str], None]

# Ano-modelo pelo 10.º caractere do VIN (ciclo de 30 anos; vale o mais recente até o ano atual).
_ANOS = "ABCDEFGHJKLMNPRSTVWXY123456789"


def ano_do_vin(vin: str, ano_atual: int | None = None) -> int | None:
    if len(vin) < 10 or vin[9] not in _ANOS:
        return None
    base = 2010 + _ANOS.index(vin[9])                  # 'A' = 1980 ou 2010
    limite = (ano_atual or datetime.now().year) + 1
    return base if base <= limite else base - 30


def vin_resumido(vin: str | None) -> str:
    if not vin or len(vin.strip()) < 10:
        return "não informado"
    v = vin.strip()
    ano = ano_do_vin(v)
    return f"fabricante {v[:3]}, ano-modelo {ano or '?'} (número completo omitido)"


def _medir(func: Callable[[], object]) -> tuple[object, float]:
    t = time.perf_counter()
    r = func()
    return r, (time.perf_counter() - t) * 1000


def diagnosticar(porta: str | None, baud: int | None, avisar: Avisar = print,
                 conectar: FabricaConexao = ConexaoPythonOBD,
                 segundos_rpm: float = SEGUNDOS_RPM, segundos_painel: float = SEGUNDOS_PAINEL,
                 espera_adaptador_s: float = ESPERA_ADAPTADOR_S,
                 parar: threading.Event | None = None) -> str:
    """Roda o diagnóstico e devolve o relatório em Markdown."""
    parar = parar or threading.Event()
    agora = datetime.now()
    linhas = [f"# Diagnóstico OBD-II — {agora:%Y-%m-%d %H:%M}", "",
              "Preencha: **modelo** ____  **ano** ____  **motor** ____  **combustível** ____", "",
              f"- Porta: `{porta or 'procurada automaticamente'}`"
              f"{f' a {baud} baud' if baud else ''}"]

    avisar("Procurando o adaptador OBD...")
    conexao = None
    fim = time.monotonic() + espera_adaptador_s
    situacao = "sem_adaptador"
    while not parar.is_set():
        try:
            conexao = conectar(porta, baud)
            situacao = conexao.situacao()
        except Exception as e:  # noqa: BLE001 — porta ausente, permissão
            situacao = f"sem_adaptador ({e})"
        if situacao == "conectado":
            break
        if conexao is not None:
            conexao.fechar()
            conexao = None
        if time.monotonic() > fim:
            break
        avisar("  ainda não: " + ("o adaptador responde, mas o carro não (ligue a ignição)"
                                  if situacao == "sem_carro" else "adaptador não encontrado"))
        parar.wait(3.0)
    if conexao is None:
        linhas += [f"- **Falhou**: {situacao}.", ""]
        avisar("Sem conexão com o carro.")
        return "\n".join(linhas) + "\n"

    try:
        avisar(f"Conectado: {getattr(conexao, 'protocolo', '?')}")
        texto = getattr(conexao, "consultar_texto", lambda c: None)
        vin = texto("VIN")
        linhas += [
            f"- Protocolo: {getattr(conexao, 'protocolo', '?')}",
            f"- Adaptador: {texto('ELM_VERSION') or '?'} "
            f"(tensão no conector: {texto('ELM_VOLTAGE') or '?'})",
            f"- VIN: {vin_resumido(vin)}",
            f"- Combustível informado: {texto('FUEL_TYPE') or 'não informado'}",
            f"- Norma OBD: {texto('OBD_COMPLIANCE') or 'não informada'}",
            f"- Situação: {texto('STATUS') or 'não informada'}",
            "",
        ]

        suportados = getattr(conexao, "suportados", lambda: [])()
        avisar(f"{len(suportados)} PIDs suportados; lendo cada um...")
        linhas += [f"## PIDs suportados ({len(suportados)})", "",
                   "| PID | Descrição | Valor | Resposta (ms) |", "| --- | --- | --- | --- |"]
        latencias = []
        for nome, desc in suportados:
            if parar.is_set():
                break
            valor, ms = _medir(lambda n=nome: texto(n))
            latencias.append(ms)
            linhas.append(f"| `{nome}` | {desc} | {valor if valor is not None else '—'} "
                          f"| {ms:.0f} |")
        if latencias:
            linhas += ["", f"Resposta média: {statistics.mean(latencias):.0f} ms "
                           f"(mín. {min(latencias):.0f}, máx. {max(latencias):.0f})."]
        linhas.append("")

        avisar(f"Medindo o rpm sozinho por {segundos_rpm:.0f} s...")
        n, t0 = 0, time.monotonic()
        while time.monotonic() - t0 < segundos_rpm and not parar.is_set():
            if conexao.ler("RPM") is not None:
                n += 1
        dt = time.monotonic() - t0
        linhas += ["## Taxa de leitura", "",
                   f"- Só o rpm: **{n / dt:.1f} leituras/s** ({n} em {dt:.0f} s)."]
        avisar(f"  rpm sozinho: {n / dt:.1f}/s")

        codigos = {t: conexao.erros(t) for t in TIPOS_ERRO}
    finally:
        conexao.fechar()

    avisar(f"Medindo o painel (agenda completa) por {segundos_painel:.0f} s...")
    fonte = FonteOBD(porta, baud, conectar=conectar)
    fonte.iniciar()
    t0 = time.monotonic()
    while time.monotonic() - t0 < segundos_painel and not parar.is_set():
        time.sleep(0.2)
    fonte.parar()
    linhas += [f"- Painel: **{fonte.taxa_rpm:.1f} rpm/s** (um ciclo da agenda por leitura); "
               f"canais: {', '.join(fonte.canais) or 'nenhum'}.",
               f"- Consumo calculado por: {fonte.consumo.metodo or 'nenhum método'}.", ""]
    avisar(f"  painel: {fonte.taxa_rpm:.1f} rpm/s")

    linhas += ["## Códigos de erro", ""]
    for tipo in TIPOS_ERRO:
        lista = codigos[tipo]
        linhas.append(f"- {tipo.capitalize()}: " + (", ".join(
            f"`{c}` {d}".strip() for c, d in lista) if lista else "nenhum"))
    avisar("Pronto.")
    return "\n".join(linhas) + "\n"


def salvar(relatorio: str, pasta: str = PASTA) -> str:
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, f"obd-{datetime.now():%Y%m%d-%H%M%S}.md")
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(relatorio)
    return caminho


# --- tela (Eee PC) --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    import pygame  # noqa: PLC0415

    from core.app import App, opcoes_comuns  # noqa: PLC0415

    p = opcoes_comuns("Dashamp - diagnóstico OBD-II")
    p.add_argument("--porta", help="padrão: procurar (USB ou Bluetooth)")
    p.add_argument("--baud", type=int)
    args = p.parse_args(argv)
    app = App(args, "Dashamp - diagnóstico")
    log: list[str] = []
    estado = {"versao": 0, "desenhada": -1, "rodando": False}
    parar = threading.Event()

    def avisar(s: str) -> None:
        log.append(s)
        estado["versao"] += 1

    def rodar() -> None:
        estado["rodando"] = True
        try:
            rel = diagnosticar(args.porta, args.baud, avisar, parar=parar)
            avisar(f"Relatório salvo em {salvar(rel)}")
        except Exception as e:  # noqa: BLE001 — aparece na tela
            avisar(f"Erro: {e!r}")
        estado["rodando"] = False
        avisar("R = repetir   F4 = painel do carro   F1 = música")

    def iniciar() -> None:
        log.clear()
        threading.Thread(target=rodar, daemon=True).start()

    titulo = pygame.font.Font(None, 40)
    fonte = pygame.font.Font(None, 26)

    def quadro(tela: pygame.Surface, _dt: float) -> list[pygame.Rect] | None:
        if estado["versao"] == estado["desenhada"]:
            return []
        estado["desenhada"] = estado["versao"]
        tela.fill((12, 14, 18))
        tela.blit(titulo.render("Diagnóstico do carro (OBD-II)", True, (255, 170, 30)), (24, 18))
        for i, linha in enumerate(log[-15:]):
            tela.blit(fonte.render(linha[:90], True, (235, 235, 235)), (24, 70 + i * 26))
        return None

    def ao_evento(ev: pygame.event.Event) -> None:
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_r and not estado["rodando"]:
            iniciar()

    iniciar()
    try:
        app.rodar(quadro, ao_evento)
    finally:
        parar.set()


if __name__ == "__main__":
    main()
