"""Inspeção do mapa de sprites (F1.3): todos os sprites da skin, ampliados 2×, rotulados, em grade.

    python -m player.inspecionar_sprites --skin player/skins_teste/zelda_amp_3.wsz --pagina 1

Setas/Espaço trocam de página. Sprite ausente aparece como uma caixa vermelha com "ausente".
"""
from __future__ import annotations

import os
from collections.abc import Sequence

from core.app import ALTURA, LARGURA, App, opcoes_comuns

import pygame  # noqa: E402

from core.skin import Skin, carregar  # noqa: E402
from player import sprites as sp  # noqa: E402

ESCALA = 2
MARGEM = 8
COR_FUNDO = (28, 28, 34)
COR_ROTULO = (170, 170, 190)
COR_AUSENTE = (200, 40, 40)
PASTA_SKINS = os.path.join(os.path.dirname(__file__), "skins_teste")


def texto_skin(skin: Skin, texto: str) -> pygame.Surface:
    """Escreve com a fonte de text.bmp (o mesmo que o letreiro vai fazer)."""
    sup = pygame.Surface((len(texto) * sp.LARGURA_CARACTERE, sp.ALTURA_CARACTERE))
    for i, c in enumerate(texto):
        img = sp.caractere(skin, c)
        if img is not None:
            sup.blit(img, (i * sp.LARGURA_CARACTERE, 0))
    return sup


def digitos_skin(skin: Skin) -> pygame.Surface:
    sup = pygame.Surface((10 * 9, 13))
    for n in range(10):
        img = sp.digito(skin, n)
        if img is not None:
            sup.blit(img, (9 * n, 0))
    return sup


def itens(skin: Skin) -> list[tuple[str, pygame.Surface | None]]:
    lista: list[tuple[str, pygame.Surface | None]] = []
    for nome in sp.SPRITES:
        if nome.startswith("digito_") or nome == "fundo":
            continue
        lista.append((nome, sp.recortar(skin, nome)))
    lista.append(("digitos (" + ("nums_ex" if "nums_ex" in skin.imagens else "numbers") + ")",
                  digitos_skin(skin)))
    for q in (0, 14, 27):
        lista.append((f"volume_fundo {q}", sp.volume_fundo(skin, q)))
        lista.append((f"balanco_fundo {q}", sp.balanco_fundo(skin, q)))
    lista.append(("texto a-z", texto_skin(skin, "abcdefghijklmnopqrstuvwxyz\"@")))
    lista.append(("texto simbolos", texto_skin(skin, "0123456789….:()-'!_+\\/[]^&%,=$#")))
    lista.append(("texto exemplo", texto_skin(skin, "DASHAMP 1:23 128kbps 44khz ?*")))
    lista.append(("fundo (main.bmp)", sp.recortar(skin, "fundo")))
    return lista


def paginar(itens_: list[tuple[str, pygame.Surface | None]], fonte: pygame.font.Font
            ) -> list[pygame.Surface]:
    """Distribui as células da esquerda para a direita, quebrando linha e página."""
    paginas: list[pygame.Surface] = []
    pagina = pygame.Surface((LARGURA, ALTURA))
    pagina.fill(COR_FUNDO)
    x = y = MARGEM
    altura_linha = 0
    for nome, img in itens_:
        if img is not None:
            celula = pygame.transform.scale(img, (img.get_width() * ESCALA, img.get_height() * ESCALA))
        else:
            celula = pygame.Surface((54, 20))
            celula.fill(COR_AUSENTE)
            celula.blit(fonte.render("ausente", True, (255, 255, 255)), (2, 3))
        rotulo = fonte.render(nome, True, COR_ROTULO)
        w = max(celula.get_width(), rotulo.get_width())
        h = celula.get_height() + rotulo.get_height() + 2
        if x + w > LARGURA - MARGEM:
            x, y = MARGEM, y + altura_linha + MARGEM
            altura_linha = 0
        if y + h > ALTURA - MARGEM and (x, y) != (MARGEM, MARGEM):
            paginas.append(pagina)
            pagina = pygame.Surface((LARGURA, ALTURA))
            pagina.fill(COR_FUNDO)
            x = y = MARGEM
            altura_linha = 0
        pagina.blit(celula, (x, y))
        pygame.draw.rect(pagina, (70, 70, 90), (x - 1, y - 1, celula.get_width() + 2,
                                                 celula.get_height() + 2), 1)
        pagina.blit(rotulo, (x, y + celula.get_height() + 2))
        x += w + MARGEM
        altura_linha = max(altura_linha, h)
    paginas.append(pagina)
    return paginas


def main(argv: Sequence[str] | None = None) -> None:
    p = opcoes_comuns("Dashamp - inspeção do mapa de sprites (F1.3)")
    p.add_argument("--skin", default=os.path.join(PASTA_SKINS, "base-2.91.wsz"))
    p.add_argument("--pagina", type=int, default=0)
    args = p.parse_args(argv)
    app = App(args, "Dashamp sprites")

    base = os.path.join(PASTA_SKINS, "base-2.91.wsz")
    padrao = carregar(base) if os.path.exists(base) and os.path.abspath(base) != \
        os.path.abspath(args.skin) else None
    skin = carregar(args.skin, padrao=padrao)
    fonte = pygame.font.Font(None, 16)
    paginas = paginar(itens(skin), fonte)
    estado = {"pagina": max(0, min(args.pagina, len(paginas) - 1)), "sujo": True}
    print(f"{skin.nome}: {len(paginas)} página(s); emprestados={skin.emprestados} "
          f"ausentes={skin.ausentes}", flush=True)

    def ao_evento(ev: pygame.event.Event) -> None:
        if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RIGHT, pygame.K_SPACE, pygame.K_LEFT):
            passo = -1 if ev.key == pygame.K_LEFT else 1
            estado["pagina"] = (estado["pagina"] + passo) % len(paginas)
            estado["sujo"] = True

    def quadro(tela: pygame.Surface, dt: float) -> list[pygame.Rect]:
        if not estado["sujo"]:
            return []
        estado["sujo"] = False
        tela.blit(paginas[estado["pagina"]], (0, 0))
        rotulo = fonte.render(f"{skin.nome}  [{estado['pagina'] + 1}/{len(paginas)}]", True,
                              (255, 220, 120))
        tela.blit(rotulo, (LARGURA - rotulo.get_width() - MARGEM, ALTURA - rotulo.get_height() - 4))
        return [tela.get_rect()]

    app.rodar(quadro, ao_evento)


if __name__ == "__main__":
    main()
