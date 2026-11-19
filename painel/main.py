"""App do painel (F2.5, F2.6): carrega um tema e o alimenta com uma fonte.

    python -m painel.main [--tema vintage] [--replay viagem.db --velocidade 2] [--metricas]
                          [--ciclo-temas S] [--udp [--porta 20777]] [--gt7 [--ps5 IP]]
                          [--gravar-udp ARQ] [--obd [PORTA] [--obd-baud 38400]]

No Eee PC: F1 = player, F2 = painel recebendo o GT7, F3 = painel com a simulação (core.app).
Enquanto não chega telemetria, uma caixa na tela diz o que falta (com o IP deste aparelho).

Fonte padrão: a simulada; `--udp` escuta a telemetria do F1 24; `--gt7` pede a do Gran Turismo 7
ao PS5 (procura o console na rede, ou `--ps5 IP`); `--obd` lê o carro por um ELM327 (sem porta:
procura; ou /dev/ttyUSB0, /dev/rfcomm0, socket://host:porta do emulador). `--gravar-udp` guarda os pacotes brutos. **T** passa para o próximo tema (sem reiniciar); Esc/Q sai.
Um tema inválido na abertura termina com a lista de erros; na troca, os erros são impressos e o
tema atual continua.
"""
from __future__ import annotations

import os
import socket
import sys
import time
from collections.abc import Callable, Sequence

from core.app import App, lembrar_opcao, opcoes_comuns

import pygame  # noqa: E402

from painel import tema as tm  # noqa: E402
from painel.teste_widgets import criar_fonte  # noqa: E402


def ip_local() -> str | None:
    """IP da interface com rota para a rede (nenhum pacote é enviado)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        return None if ip.startswith("127.") or ip == "0.0.0.0" else ip
    except OSError:
        return None
    finally:
        s.close()


class AvisoEspera:
    """Caixa no meio da tela enquanto o jogo não manda nada: o que falta e o IP deste aparelho."""

    def __init__(self, linhas: Callable[[str | None], tuple[str, str, str]]) -> None:
        self.linhas = linhas
        self.fonte_grande = pygame.font.Font(None, 40)
        self.fonte = pygame.font.Font(None, 28)
        self._texto: tuple[str, ...] | None = None
        self._consulta = 0.0

    def desenhar(self, tela: pygame.Surface, forcar: bool) -> bool:
        """Desenha se o texto mudou (ou `forcar`); devolve True se desenhou."""
        agora = time.monotonic()
        if self._texto is None or agora - self._consulta > 2:   # a rede pode subir depois
            self._consulta = agora
            linhas = self.linhas(ip_local())
            if linhas != self._texto:
                self._texto, forcar = linhas, True
        if not forcar:
            return False
        caixa = pygame.Rect(0, 0, 620, 150)
        caixa.center = (400, 240)
        pygame.draw.rect(tela, (12, 14, 18), caixa, border_radius=10)
        pygame.draw.rect(tela, (255, 170, 30), caixa, 2, border_radius=10)
        for i, linha in enumerate(self._texto):
            f = self.fonte_grande if i == 0 else self.fonte
            img = f.render(linha, True, (255, 170, 30) if i == 0 else (235, 235, 235))
            tela.blit(img, img.get_rect(center=(400, caixa.y + 34 + i * 42)))
        return True


def main(argv: Sequence[str] | None = None) -> None:
    p = opcoes_comuns("Dashamp - painel")
    p.add_argument("--tema", default="vintage",
                   help=f"nome ou pasta (temas: {', '.join(tm.listar())})")
    p.add_argument("--ciclo-temas", type=float, default=0.0, metavar="S",
                   help="troca de tema sozinho a cada S segundos (para medir)")
    p.add_argument("--replay", help="viagem .db em vez da simulação")
    p.add_argument("--velocidade", type=float, default=1.0)
    p.add_argument("--udp", action="store_true", help="telemetria do F1 24 pela rede")
    p.add_argument("--porta", type=int, default=20777)
    p.add_argument("--gt7", action="store_true", help="telemetria do Gran Turismo 7 (PS5)")
    p.add_argument("--ps5", help="com --gt7: IP do PS5 (sem isto, procura na rede)")
    p.add_argument("--gravar-udp", metavar="ARQ", help="com --udp/--gt7: grava os pacotes brutos")
    p.add_argument("--obd", nargs="?", const="auto", metavar="PORTA",
                   help="carro pelo adaptador ELM327 (sem PORTA: procura)")
    p.add_argument("--obd-baud", type=int, help="com --obd: velocidade da serial (padrão: detectar)")
    args = p.parse_args(argv)
    app = App(args, "Dashamp - painel")
    try:
        tema = tm.carregar(args.tema)
    except tm.ErroTema as e:
        pygame.quit()
        print(e, file=sys.stderr, flush=True)
        raise SystemExit(2) from None
    print(f"tema '{tema.nome}' carregado em {tema.segundos_carga * 1000:.0f} ms "
          f"({len(tema.painel.widgets)} widgets)", flush=True)
    aviso: AvisoEspera | None = None
    if args.gt7:
        from painel.fontes.gt7 import FonteGT7

        fonte = FonteGT7(args.ps5, gravar_em=args.gravar_udp)
        print(f"Gran Turismo 7: {'PS5 em ' + args.ps5 if args.ps5 else 'procurando o PS5'}",
              flush=True)

        def linhas_gt7(ip: str | None) -> tuple[str, str, str]:
            if ip is None:
                return ("Sem rede", "Ligue o cabo de rede no roteador",
                        "(o Wi-Fi deste aparelho não funciona)")
            if fonte.procurando:
                return ("Procurando o PS5 (Gran Turismo 7)", f"IP deste aparelho: {ip}",
                        "Ligue o GT7 no PS5, na mesma rede")
            return (f"PS5 encontrado: {fonte.ps5}", "Entre na pista para ver os dados",
                    f"IP deste aparelho: {ip}")

        aviso = AvisoEspera(linhas_gt7)
    elif args.obd:
        from painel.fontes.obd import FonteOBD

        porta = None if args.obd == "auto" else args.obd
        fonte = FonteOBD(porta, args.obd_baud)
        print(f"OBD: {porta or 'procurando o adaptador'}", flush=True)
        textos_obd = {
            "sem_carro": ("Adaptador OBD encontrado", "Ligue a ignição do carro",
                          "(o adaptador responde, o carro ainda não)"),
            "sem_adaptador": ("Adaptador OBD não encontrado", f"Porta: {porta or 'procurando'}",
                              "Confira o ELM327 na tomada OBD e no USB"),
        }
        aviso = AvisoEspera(lambda _ip: textos_obd.get(fonte.situacao, (
            "Conectando ao carro (OBD-II)", f"Porta: {porta or 'procurando'}",
            "Pode levar alguns segundos")))
    elif args.udp:
        from painel.fontes.udp_f1 import FonteUDPF1

        fonte = FonteUDPF1(args.porta, gravar_em=args.gravar_udp)
        print(f"escutando a telemetria do F1 24 na porta UDP {args.porta}", flush=True)
        aviso = AvisoEspera(lambda ip: (
            "Aguardando a telemetria do F1 24",
            f"IP deste aparelho: {ip}" if ip else "Sem rede: ligue o cabo de rede",
            f"Porta UDP: {args.porta}  -  Formato UDP: 2024"))
    else:
        fonte = criar_fonte(args.replay, args.velocidade)
    estado = {"tema": tema, "ciclo": 0.0, "aviso": aviso}

    def trocar() -> None:
        nomes = tm.listar()
        atual = os.path.basename(os.path.normpath(estado["tema"].pasta))
        proximo = nomes[(nomes.index(atual) + 1) % len(nomes)] if atual in nomes else nomes[0]
        try:
            novo = tm.carregar(proximo)
        except tm.ErroTema as e:
            print(e, file=sys.stderr, flush=True)
            return
        estado["tema"] = novo
        lembrar_opcao("--tema", proximo)          # no Eee PC: o próximo boot abre neste tema
        print(f"tema '{novo.nome}' em {novo.segundos_carga * 1000:.0f} ms", flush=True)

    def ao_evento(ev: pygame.event.Event) -> None:
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_t:
            trocar()

    def quadro(tela: pygame.Surface, dt: float) -> list[pygame.Rect] | None:
        aviso = estado["aviso"]
        if args.ciclo_temas > 0:
            estado["ciclo"] += dt
            if estado["ciclo"] >= args.ciclo_temas:
                estado["ciclo"] = 0.0
                trocar()
        painel = estado["tema"].painel
        painel.atualizar(fonte, dt)
        if aviso is not None:
            if fonte.ultima() is None:
                sujos = painel.desenhar(tela)
                if aviso.desenhar(tela, forcar=sujos is None):
                    return None
                return sujos
            aviso = None                              # chegou dado: some a caixa
            painel.redesenhar_tudo()
            estado["aviso"] = None
        return painel.desenhar(tela)

    fonte.iniciar()
    try:
        app.rodar(quadro, ao_evento)
    finally:
        fonte.parar()
        if fonte.erro:
            print(f"erro na fonte: {fonte.erro!r}", flush=True)
        if hasattr(fonte, "contagem"):
            print(f"contagem: {dict(fonte.contagem)}", flush=True)
        if hasattr(fonte, "taxa_rpm"):
            print(f"rpm lidos por segundo: {fonte.taxa_rpm:.1f}", flush=True)


if __name__ == "__main__":
    main()
