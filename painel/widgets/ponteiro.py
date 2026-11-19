"""Ponteiro analógico com escala (F2.4).

A escala (traços, números, faixa das zonas) é desenhada no fundo em 2× e reduzida com
smoothscale (antisserrilhado barato, só na carga). O ponteiro usa o cache de ângulos da F0.8,
mas preenchido **sob demanda**: cada ângulo (passo de 1°, só dentro da varredura) é girado com
rotozoom na primeira vez que aparece e guardado recortado ao conteúdo. Assim a carga é
instantânea (a F2.5 pede tema em < 1 s) e o custo de girar aparece no máximo uma vez por ângulo.
"""
from __future__ import annotations

import math
from collections.abc import Sequence

import pygame

from painel.widgets.base import Cor, Widget, Zona, restaurar


def ponto(cx: float, cy: float, graus: float, r: float) -> tuple[float, float]:
    rad = math.radians(graus)
    return cx + r * math.cos(rad), cy - r * math.sin(rad)


class CacheAngulos:
    def __init__(self, sprite: pygame.Surface, passo: float = 1.0) -> None:
        self.sprite = sprite
        self.passo = passo
        self.quadros: dict[int, tuple[pygame.Surface, int, int]] = {}

    def obter(self, graus: float) -> tuple[pygame.Surface, int, int]:
        i = int(round(graus / self.passo))
        q = self.quadros.get(i)
        if q is None:
            girado = pygame.transform.rotozoom(self.sprite, i * self.passo, 1.0)
            caixa = girado.get_bounding_rect()
            recorte = girado.subsurface(caixa).copy()
            if pygame.display.get_surface() is not None:
                recorte = recorte.convert_alpha()      # blit mais rápido no formato da tela
            q = (recorte, caixa.x - girado.get_width() // 2, caixa.y - girado.get_height() // 2)
            self.quadros[i] = q
        return q


class Ponteiro(Widget):
    def __init__(self, canal: str, centro: tuple[int, int], raio: int, minimo: float,
                 maximo: float, *, angulo_zero: float = 225.0, varredura: float = 270.0,
                 zonas: Sequence[Zona] = (), tau: float = 0.12,
                 passo_maior: float | None = None, divisor: float = 1.0, menores: int = 4,
                 rotulo: str = "", cor_ponteiro: Cor = (220, 20, 20),
                 cor_face: Cor = (236, 228, 205), cor_traco: Cor = (30, 30, 30),
                 cor_aro: Cor = (90, 90, 90), fonte_numeros: str | None = None,
                 sprite: pygame.Surface | None = None, escala: bool = True,
                 cubo: bool = True) -> None:
        """`sprite`: imagem do ponteiro com o pivô no centro, apontando para a direita (0°);
        sem ela, o ponteiro é desenhado. `escala=False` deixa a face por conta do tema (fundo)."""
        super().__init__(canal, minimo, maximo, tau, zonas)
        self.centro, self.raio = centro, raio
        self.angulo_zero, self.varredura = angulo_zero, varredura
        self.passo_maior = passo_maior or (maximo - minimo) / 8
        self.divisor, self.menores, self.rotulo = divisor, menores, rotulo
        self.cores = {"ponteiro": cor_ponteiro, "face": cor_face, "traco": cor_traco,
                      "aro": cor_aro}
        self.fonte_numeros = fonte_numeros
        self.ret = pygame.Rect(0, 0, 2 * raio, 2 * raio)
        self.ret.center = centro
        comprimento = int(raio * 0.86)
        self.cache = CacheAngulos(sprite if sprite is not None
                                  else self._sprite(comprimento, cor_ponteiro))
        self.cubo = self._cubo(max(8, raio // 12)) if cubo else None
        self.escala = escala
        self._ret_anterior = pygame.Rect(centro, (0, 0))

    def angulo(self, valor: float | None = None) -> float:
        return self.angulo_zero - self.varredura * self.fracao(valor)

    # --- carga ------------------------------------------------------------------------

    @staticmethod
    def _sprite(comprimento: int, cor: Cor) -> pygame.Surface:
        """Pivô no centro; ponteiro na metade direita (0°), com uma cauda curta."""
        larg, alt = 2 * comprimento + 8, max(10, comprimento // 9)
        s = pygame.Surface((larg, alt), pygame.SRCALPHA)
        cx, cy = larg / 2, alt / 2
        cauda, base, ponta = comprimento * 0.15, alt * 0.35, 1.5
        pygame.draw.polygon(s, cor, [(cx - cauda, cy - base), (cx + comprimento, cy - ponta),
                                     (cx + comprimento, cy + ponta), (cx - cauda, cy + base)])
        return s

    @staticmethod
    def _cubo(r: int) -> pygame.Surface:
        s = pygame.Surface((2 * r + 2, 2 * r + 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (40, 40, 40), (r + 1, r + 1), r)
        pygame.draw.circle(s, (120, 120, 120), (r + 1, r + 1), max(2, r // 2))
        return s

    def pintar_fundo(self, fundo: pygame.Surface) -> None:
        if not self.escala:
            return
        e = 2                                  # desenha em 2× e reduz
        lado = 2 * self.raio * e
        c = lado / 2
        r = self.raio * e
        face = pygame.Surface((lado, lado))
        face.blit(pygame.transform.scale(fundo.subsurface(self.ret), (lado, lado)), (0, 0))
        pygame.draw.circle(face, self.cores["aro"], (c, c), r - 1)
        pygame.draw.circle(face, self.cores["face"], (c, c), r * 0.95)
        faixa = self.maximo - self.minimo
        for z in self.zonas:                   # faixa colorida das zonas, junto à borda
            de, ate = max(z.de, self.minimo), min(z.ate, self.maximo)
            passos = max(2, int((ate - de) / faixa * 120))
            angulos = [self.angulo(de + (ate - de) * i / passos) for i in range(passos + 1)]
            pygame.draw.polygon(face, z.cor, [ponto(c, c, a, r * 0.90) for a in angulos]
                                + [ponto(c, c, a, r * 0.80) for a in reversed(angulos)])
        fonte = pygame.font.SysFont(self.fonte_numeros, int(r * 0.2)) if self.fonte_numeros \
            else pygame.font.Font(None, int(r * 0.24))
        n_maiores = int(round(faixa / self.passo_maior))
        for i in range(n_maiores * (self.menores + 1) + 1):
            v = self.minimo + i * self.passo_maior / (self.menores + 1)
            a = self.angulo(v)
            maior = i % (self.menores + 1) == 0
            pygame.draw.line(face, self.cores["traco"], ponto(c, c, a, r * (0.74 if maior else 0.82)),
                             ponto(c, c, a, r * 0.90), int((3 if maior else 1.5) * e))
            if maior:
                n = v / self.divisor
                txt = fonte.render(f"{n:g}", True, self.cores["traco"])
                face.blit(txt, txt.get_rect(center=ponto(c, c, a, r * 0.58)))
        if self.rotulo:
            t = pygame.font.Font(None, int(r * 0.16)).render(self.rotulo, True, self.cores["aro"])
            face.blit(t, t.get_rect(center=(c, c - r * 0.3)))
        fundo.blit(pygame.transform.smoothscale(face, self.ret.size), self.ret)

    # --- quadro -----------------------------------------------------------------------

    def _chave(self) -> object:
        return None if self.valor is None else int(round(self.angulo() / self.cache.passo))

    def _pintar(self, tela: pygame.Surface, fundo: pygame.Surface) -> list[pygame.Rect]:
        sujo = self._ret_anterior.copy()
        restaurar(tela, fundo, self._ret_anterior)
        if self.valor is None:
            return [sujo]
        img, dx, dy = self.cache.obter(self.angulo())
        cx, cy = self.centro
        ret = tela.blit(img, (cx + dx, cy + dy))
        if self.cubo is not None:
            ret.union_ip(tela.blit(self.cubo, self.cubo.get_rect(center=self.centro)))
        self._ret_anterior = ret
        return [sujo.union(ret)]
