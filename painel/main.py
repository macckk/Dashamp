"""App do painel (F2.5, F2.6): carrega um tema e o alimenta com uma fonte.

    python -m painel.main [--tema vintage] [--replay viagem.db --velocidade 2] [--metricas]
                          [--ciclo-temas S] [--udp [--porta 20777] [--gravar-udp ARQ]]

Fonte padrão: a simulada; `--udp` escuta a telemetria do F1 24 (e `--gravar-udp` guarda os
pacotes brutos para testes). **T** passa para o próximo tema (sem reiniciar); Esc/Q sai.
Um tema inválido na abertura termina com a lista de erros; na troca, os erros são impressos e o
tema atual continua.
"""
from __future__ import annotations

import os
import sys
from collections.abc import Sequence

from core.app import App, opcoes_comuns

import pygame  # noqa: E402

from painel import tema as tm  # noqa: E402
from painel.teste_widgets import criar_fonte  # noqa: E402


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
    p.add_argument("--gravar-udp", metavar="ARQ", help="com --udp: grava os pacotes brutos")
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
    if args.udp:
        from painel.fontes.udp_f1 import FonteUDPF1

        fonte = FonteUDPF1(args.porta, gravar_em=args.gravar_udp)
        print(f"escutando a telemetria do F1 24 na porta UDP {args.porta}", flush=True)
    else:
        fonte = criar_fonte(args.replay, args.velocidade)
    estado = {"tema": tema, "ciclo": 0.0}

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
        print(f"tema '{novo.nome}' em {novo.segundos_carga * 1000:.0f} ms", flush=True)

    def ao_evento(ev: pygame.event.Event) -> None:
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_t:
            trocar()

    def quadro(tela: pygame.Surface, dt: float) -> list[pygame.Rect] | None:
        if args.ciclo_temas > 0:
            estado["ciclo"] += dt
            if estado["ciclo"] >= args.ciclo_temas:
                estado["ciclo"] = 0.0
                trocar()
        painel = estado["tema"].painel
        painel.atualizar(fonte, dt)
        return painel.desenhar(tela)

    fonte.iniciar()
    try:
        app.rodar(quadro, ao_evento)
    finally:
        fonte.parar()
        if fonte.erro:
            print(f"erro na fonte: {fonte.erro!r}", flush=True)
        if hasattr(fonte, "contagem"):
            print(f"pacotes UDP: {dict(fonte.contagem)}", flush=True)


if __name__ == "__main__":
    main()
