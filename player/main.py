"""Player funcional (F1.6): janela principal da skin ligada ao motor de áudio.

    python -m player.main [arquivos ou pastas ...] [--skin X.wsz] [--escala 1|2]

Atalhos (os do Winamp): Z anterior, X tocar, C pausar, V parar, B próxima; setas ↑/↓ volume,
←/→ voltar/avançar 5 s; S aleatório, R repetir. Esc/Q sai. Sem argumentos, toca ~/musica.
"""
from __future__ import annotations

import os
import random
from collections.abc import Sequence

from core.app import ALTURA, LARGURA, App, opcoes_comuns

import pygame  # noqa: E402

from core.skin import Skin, carregar  # noqa: E402
from player import sprites as sp  # noqa: E402
from player.analisador import Analisador  # noqa: E402
from player.janela_principal import (  # noqa: E402
    COR_TRANSPARENTE, PASTA_SKINS, EstadoJanela, desenhar,
)

EXTENSOES = (".mp3", ".ogg", ".flac", ".wav", ".m4a", ".opus")
PASSO_LETREIRO_PX = 5        # o letreiro anda um caractere por vez
INTERVALO_LETREIRO_S = 0.2
SEPARADOR_LETREIRO = "  ***  "


def listar_faixas(entradas: Sequence[str]) -> list[str]:
    faixas: list[str] = []
    for entrada in entradas:
        entrada = os.path.expanduser(entrada)
        if os.path.isdir(entrada):
            for raiz, _, arquivos in sorted(os.walk(entrada)):
                faixas += [os.path.join(raiz, a) for a in sorted(arquivos)
                           if a.lower().endswith(EXTENSOES)]
        elif entrada.lower().endswith(EXTENSOES) and os.path.exists(entrada):
            faixas.append(entrada)
    return faixas


def formatar_tempo(segundos: float | None) -> str:
    if segundos is None:
        return ""
    m, s = divmod(int(segundos), 60)
    return f"{m}:{s:02d}"


class Player:
    def __init__(self, app: App, skin: Skin, faixas: list[str], escala: int,
                 motor: object | None = None) -> None:
        self.app = app
        self.skin = skin
        self.faixas = faixas
        self.indice = 0
        if motor is None:  # importado aqui: os testes no PC (sem GStreamer) injetam um falso
            from player.audio import MotorAudio

            motor = MotorAudio()
        self.motor = motor
        self.estado = EstadoJanela(volume=self.motor.volume(), eq=False, pl=False)
        self.analisador = Analisador(skin.viscolor)
        self.trabalho = pygame.Surface((sp.LARGURA_JANELA, sp.ALTURA_JANELA)).convert()
        self.escala = escala
        tamanho = (sp.LARGURA_JANELA * escala, sp.ALTURA_JANELA * escala)
        self.escalado = pygame.Surface(tamanho).convert()
        if skin.regiao is not None:
            self.escalado.set_colorkey(COR_TRANSPARENTE)
        self.ret_tela = self.escalado.get_rect(center=(LARGURA // 2, ALTURA // 2))
        self._letreiro_texto = ""
        self._letreiro_t = 0.0
        self._pos_vis = sp.POSICOES["visualizacao"]
        app.tela.fill((0, 0, 0))
        if faixas:
            self.abrir(0, tocar=True)

    # --- faixas -----------------------------------------------------------------

    def abrir(self, indice: int, tocar: bool) -> None:
        self.indice = indice % len(self.faixas)
        self.motor.abrir(self.faixas[self.indice])
        self.estado.deslocamento_titulo = 0
        self._letreiro_texto = ""
        self.analisador.zerar()
        if tocar:
            self.motor.tocar()

    def proxima(self, passo: int = 1) -> None:
        if not self.faixas:
            return
        if self.estado.aleatorio and len(self.faixas) > 1:
            novo = random.choice([i for i in range(len(self.faixas)) if i != self.indice])
        else:
            novo = self.indice + passo
        estava_tocando = self.motor.estado() == "tocando"
        self.abrir(novo, tocar=estava_tocando)

    def _fim_da_faixa(self) -> None:
        """Como o Winamp: segue a lista; no fim, volta ao começo se 'repetir' estiver ligado."""
        n = len(self.faixas)
        if self.estado.aleatorio and n > 1:
            novo = random.choice([i for i in range(n) if i != self.indice])
        elif self.indice + 1 < n:
            novo = self.indice + 1
        elif self.estado.repetir:
            novo = 0
        else:
            self.abrir(0, tocar=False)
            return
        self.abrir(novo, tocar=True)

    # --- teclado ------------------------------------------------------------------

    def ao_evento(self, ev: pygame.event.Event) -> None:
        if ev.type != pygame.KEYDOWN or not self.faixas:
            return
        k, m = ev.key, self.motor
        if k == pygame.K_z:
            self.proxima(-1)
        elif k == pygame.K_x:
            if m.estado() == "tocando":
                m.buscar(0)
            m.tocar()
        elif k == pygame.K_c:
            m.tocar() if m.estado() == "pausado" else m.pausar()
        elif k == pygame.K_v:
            m.parar()
            self.analisador.zerar()
        elif k == pygame.K_b:
            self.proxima(1)
        elif k in (pygame.K_UP, pygame.K_DOWN):
            self.estado.volume = m.volume(m.volume() + (5 if k == pygame.K_UP else -5))
        elif k in (pygame.K_LEFT, pygame.K_RIGHT):
            pos = m.posicao()
            if pos is not None:
                m.buscar(pos + (5 if k == pygame.K_RIGHT else -5))
        elif k == pygame.K_s:
            self.estado.aleatorio = not self.estado.aleatorio
        elif k == pygame.K_r:
            self.estado.repetir = not self.estado.repetir

    # --- quadro --------------------------------------------------------------------

    def _atualizar_estado(self, dt: float) -> None:
        m, e = self.motor, self.estado
        while not m.eventos.empty():
            ev = m.eventos.get()
            if ev.tipo == "fim":
                self._fim_da_faixa()
            elif ev.tipo == "erro":
                print(f"erro de áudio: {ev.texto}", flush=True)
                self.proxima()
        e.reproducao = m.estado()
        tocando = e.reproducao != "parado"
        pos, dur = (m.posicao(), m.duracao()) if tocando else (None, None)
        e.tempo_s = int(pos) if pos is not None else None
        e.posicao = (pos / dur) if pos is not None and dur else None
        t = m.tags
        e.kbps = str(t.kbps) if tocando and t.kbps else ""
        e.khz = str(t.khz) if tocando and t.khz else ""
        e.estereo = (t.canais >= 2) if tocando and t.canais else None
        self._atualizar_letreiro(dur or m.duracao(), dt)
        self.analisador.atualizar(m.espectro() if e.reproducao == "tocando" else None, dt)

    def _atualizar_letreiro(self, duracao: float | None, dt: float) -> None:
        t = self.motor.tags
        nome = os.path.splitext(os.path.basename(self.faixas[self.indice]))[0] if self.faixas else ""
        titulo = f"{t.artista} - {t.titulo}" if t.titulo and t.artista else (t.titulo or nome)
        tempo = formatar_tempo(duracao)
        texto = f"{self.indice + 1}. {titulo}" + (f" ({tempo})" if tempo else "")
        if texto != self._letreiro_texto:
            self._letreiro_texto = texto
            self.estado.deslocamento_titulo = 0
            self._letreiro_t = 0.0
        largura = len(texto) * sp.LARGURA_CARACTERE
        if largura <= sp.LARGURA_LETREIRO:
            self.estado.titulo = texto
            return
        # Rola em círculo: o texto é repetido depois do separador.
        volta = largura + len(SEPARADOR_LETREIRO) * sp.LARGURA_CARACTERE
        self.estado.titulo = texto + SEPARADOR_LETREIRO + texto
        self._letreiro_t += dt
        while self._letreiro_t >= INTERVALO_LETREIRO_S:
            self._letreiro_t -= INTERVALO_LETREIRO_S
            self.estado.deslocamento_titulo = (self.estado.deslocamento_titulo
                                               + PASSO_LETREIRO_PX) % volta

    def quadro(self, tela: pygame.Surface, dt: float) -> list[pygame.Rect]:
        self._atualizar_estado(dt)
        desenhar(self.skin, self.estado, self.trabalho)
        self.analisador.desenhar(self.trabalho, self._pos_vis)
        if self.escala == 1:
            tela.blit(self.trabalho, self.ret_tela)
        else:
            pygame.transform.scale(self.trabalho, self.escalado.get_size(), self.escalado)
            tela.blit(self.escalado, self.ret_tela)
        return [self.ret_tela]

    def fechar(self) -> None:
        self.motor.fechar()


def main(argv: Sequence[str] | None = None) -> None:
    p = opcoes_comuns("Dashamp - player")
    p.add_argument("entradas", nargs="*", default=["~/musica"], help="arquivos ou pastas")
    p.add_argument("--skin", default=os.path.join(PASTA_SKINS, "base-2.91.wsz"))
    p.add_argument("--escala", type=int, choices=(1, 2), default=2)
    args = p.parse_args(argv)
    app = App(args, "Dashamp")
    base = os.path.join(PASTA_SKINS, "base-2.91.wsz")
    padrao = carregar(base) if os.path.exists(base) and \
        os.path.abspath(base) != os.path.abspath(args.skin) else None
    skin = carregar(args.skin, padrao=padrao)
    skin.converter()
    faixas = listar_faixas(args.entradas)
    print(f"{len(faixas)} faixa(s); skin {skin.nome}", flush=True)
    player = Player(app, skin, faixas, args.escala)
    try:
        app.rodar(player.quadro, player.ao_evento)
    finally:
        player.fechar()


if __name__ == "__main__":
    main()
