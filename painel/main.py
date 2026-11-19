"""App do painel (F2.5): carrega um tema e o alimenta com uma fonte.

    python -m painel.main [--tema exemplo] [--replay viagem.db --velocidade 2] [--metricas]

Fonte padrão: a simulada. Esc/Q sai. Um tema inválido termina com a lista de erros do arquivo.
"""
from __future__ import annotations

import sys
from collections.abc import Sequence

from core.app import App, opcoes_comuns

import pygame  # noqa: E402

from painel import tema as tm  # noqa: E402
from painel.teste_widgets import criar_fonte  # noqa: E402


def main(argv: Sequence[str] | None = None) -> None:
    p = opcoes_comuns("Dashamp - painel")
    p.add_argument("--tema", default="exemplo", help=f"nome ou pasta (temas: {', '.join(tm.listar())})")
    p.add_argument("--replay", help="viagem .db em vez da simulação")
    p.add_argument("--velocidade", type=float, default=1.0)
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
    fonte = criar_fonte(args.replay, args.velocidade)

    def quadro(tela: pygame.Surface, dt: float) -> list[pygame.Rect] | None:
        tema.painel.atualizar(fonte, dt)
        return tema.painel.desenhar(tela)

    fonte.iniciar()
    try:
        app.rodar(quadro)
    finally:
        fonte.parar()
        if fonte.erro:
            print(f"erro na fonte: {fonte.erro!r}", flush=True)


if __name__ == "__main__":
    main()
