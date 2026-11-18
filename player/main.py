"""Player (F1.6 + F1.7): janela principal da skin + playlist, ligadas ao motor de áudio.

    python -m player.main [arquivos, pastas ou .m3u ...] [--skin X.wsz] [--escala 1|2]

Atalhos (os do Winamp): Z anterior, X tocar, C pausar, V parar, B próxima; S aleatório,
R repetir; Tab troca o foco entre a janela principal e a playlist; L alterna a playlist grande.
Foco na principal: ↑/↓ volume, ←/→ voltar/avançar 5 s.
Foco na playlist: ↑/↓, PgUp/PgDn, Home/End movem o cursor; Enter toca; ←/→ voltar/avançar 5 s.
Esc/Q sai. Sem argumentos, toca ~/musica.
"""
from __future__ import annotations

import os
import random
import time
from collections.abc import Sequence

from core.app import ALTURA, LARGURA, App, opcoes_comuns

import pygame  # noqa: E402

from core.skin import Skin, carregar  # noqa: E402
from player import sprites as sp  # noqa: E402
from player.analisador import Analisador  # noqa: E402
from player.janela_playlist import JanelaPlaylist  # noqa: E402
from player.janela_principal import (  # noqa: E402
    COR_TRANSPARENTE, PASTA_SKINS, EstadoJanela, desenhar,
)
from player.metadados import Faixa, carregar_lista  # noqa: E402

PASSO_LETREIRO_PX = 5        # o letreiro anda um caractere por vez
INTERVALO_LETREIRO_S = 0.2
SEPARADOR_LETREIRO = "  ***  "
LINHAS_EXTRAS_GRANDE = 4     # playlist sozinha: 116 + 4·29 = 232 px (464 em 2×)


def listar_faixas(entradas: Sequence[str]) -> list[str]:
    """Só os caminhos (compatibilidade); a lista com metadados vem de `carregar_lista`."""
    return [f.caminho for f in carregar_lista(entradas)]


def formatar_tempo(segundos: float | None) -> str:
    if segundos is None:
        return ""
    m, s = divmod(int(segundos), 60)
    return f"{m}:{s:02d}"


class Player:
    def __init__(self, app: App, skin: Skin, faixas: Sequence[Faixa | str], escala: int,
                 motor: object | None = None) -> None:
        self.app = app
        self.skin = skin
        self.faixas: list[Faixa] = [f if isinstance(f, Faixa) else Faixa(f) for f in faixas]
        self.indice = 0
        self.cursor = 0
        self.foco = "principal"
        self.lista_grande = False
        if motor is None:  # importado aqui: os testes no PC (sem GStreamer) injetam um falso
            from player.audio import MotorAudio

            motor = MotorAudio()
        self.motor = motor
        self.estado = EstadoJanela(volume=self.motor.volume(), eq=False, pl=True)
        self.analisador = Analisador(skin.viscolor)
        self.escala = escala
        self.trabalho = pygame.Surface((sp.LARGURA_JANELA, sp.ALTURA_JANELA)).convert()
        self.escalado = pygame.Surface((sp.LARGURA_JANELA * escala,
                                        sp.ALTURA_JANELA * escala)).convert()
        if skin.regiao is not None:
            self.escalado.set_colorkey(COR_TRANSPARENTE)
        self.playlists = {False: JanelaPlaylist(skin, 0, escala),
                          True: JanelaPlaylist(skin, LINHAS_EXTRAS_GRANDE, escala)}
        self._letreiro_texto = ""
        self._letreiro_t = 0.0
        self._pos_vis = sp.POSICOES["visualizacao"]
        self._relayout = True
        self._posicionar()
        if self.faixas:
            self.abrir(0, tocar=True)

    # --- layout -------------------------------------------------------------------

    def _posicionar(self) -> None:
        """Principal em cima e playlist embaixo, centralizadas; ou só a playlist grande."""
        largura = sp.LARGURA_JANELA * self.escala
        x = (LARGURA - largura) // 2
        pl = self.playlists[self.lista_grande]
        if self.lista_grande:
            self.ret_principal = None
            self.ret_playlist = pygame.Rect((x, (ALTURA - pl.tamanho[1]) // 2), pl.tamanho)
        else:
            altura = sp.ALTURA_JANELA * self.escala + pl.tamanho[1]
            y = max(0, (ALTURA - altura) // 2)
            self.ret_principal = pygame.Rect(x, y, largura, sp.ALTURA_JANELA * self.escala)
            self.ret_playlist = pygame.Rect((x, self.ret_principal.bottom), pl.tamanho)

    # --- faixas -----------------------------------------------------------------

    def abrir(self, indice: int, tocar: bool) -> None:
        if self.cursor == self.indice:  # o cursor acompanha a faixa atual, se estava nela
            self.cursor = indice % len(self.faixas)
        self.indice = indice % len(self.faixas)
        self.motor.abrir(self.faixas[self.indice].caminho)
        print(f"faixa {self.indice + 1}: {self.faixas[self.indice].nome}", flush=True)
        self.estado.deslocamento_titulo = 0
        self._letreiro_texto = ""
        self.analisador.zerar()
        if tocar:
            self.motor.tocar()

    def _aleatoria(self) -> int:
        return random.choice([i for i in range(len(self.faixas)) if i != self.indice])

    def proxima(self, passo: int = 1) -> None:
        if not self.faixas:
            return
        novo = self._aleatoria() if self.estado.aleatorio and len(self.faixas) > 1 \
            else self.indice + passo
        self.abrir(novo, tocar=self.motor.estado() == "tocando")

    def _fim_da_faixa(self) -> None:
        """Como o Winamp: segue a lista; no fim, volta ao começo se 'repetir' estiver ligado."""
        n = len(self.faixas)
        if self.estado.aleatorio and n > 1:
            novo = self._aleatoria()
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
        elif k == pygame.K_s:
            self.estado.aleatorio = not self.estado.aleatorio
        elif k == pygame.K_r:
            self.estado.repetir = not self.estado.repetir
        elif k == pygame.K_TAB:
            self.foco = "playlist" if self.foco == "principal" or self.lista_grande else "principal"
        elif k == pygame.K_l:
            self.lista_grande = not self.lista_grande
            if self.lista_grande:
                self.foco = "playlist"
            self._posicionar()
            self._relayout = True
        elif k in (pygame.K_LEFT, pygame.K_RIGHT):
            pos = m.posicao()
            if pos is not None:
                m.buscar(pos + (5 if k == pygame.K_RIGHT else -5))
        elif self.foco == "principal" and k in (pygame.K_UP, pygame.K_DOWN):
            self.estado.volume = m.volume(m.volume() + (5 if k == pygame.K_UP else -5))
        elif self.foco == "playlist":
            self._tecla_playlist(k)

    def _tecla_playlist(self, k: int) -> None:
        pagina = self.playlists[self.lista_grande].linhas_visiveis
        passos = {pygame.K_UP: -1, pygame.K_DOWN: 1, pygame.K_PAGEUP: -pagina,
                  pygame.K_PAGEDOWN: pagina, pygame.K_HOME: -len(self.faixas),
                  pygame.K_END: len(self.faixas)}
        if k in passos:
            self.cursor = max(0, min(len(self.faixas) - 1, self.cursor + passos[k]))
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.cursor_tocar()

    def cursor_tocar(self) -> None:
        self.indice = self.cursor  # para o cursor não "pular" junto em abrir()
        self.abrir(self.cursor, tocar=True)

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
        e.ativa = self.foco == "principal"
        tocando = e.reproducao != "parado"
        pos, dur = (m.posicao(), m.duracao()) if tocando else (None, None)
        e.tempo_s = int(pos) if pos is not None else None
        e.posicao = (pos / dur) if pos is not None and dur else None
        t = m.tags
        e.kbps = str(t.kbps) if tocando and t.kbps else ""
        e.khz = str(t.khz) if tocando and t.khz else ""
        e.estereo = (t.canais >= 2) if tocando and t.canais else None
        if self.faixas:
            self._atualizar_letreiro(dur or self.faixas[self.indice].duracao, dt)
        self.analisador.atualizar(m.espectro() if e.reproducao == "tocando" else None, dt)

    def _atualizar_letreiro(self, duracao: float | None, dt: float) -> None:
        t = self.motor.tags
        faixa = self.faixas[self.indice]
        if t.titulo:
            titulo = f"{t.artista} - {t.titulo}" if t.artista else t.titulo
        else:
            titulo = faixa.nome
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

    def quadro(self, tela: pygame.Surface, dt: float) -> list[pygame.Rect] | None:
        self._atualizar_estado(dt)
        sujos: list[pygame.Rect] = []
        relayout, self._relayout = self._relayout, False
        if relayout:
            tela.fill((0, 0, 0))
        if self.ret_principal is not None:
            desenhar(self.skin, self.estado, self.trabalho)
            self.analisador.desenhar(self.trabalho, self._pos_vis)
            if self.escala == 1:
                tela.blit(self.trabalho, self.ret_principal)
            else:
                pygame.transform.scale(self.trabalho, self.escalado.get_size(), self.escalado)
                tela.blit(self.escalado, self.ret_principal)
            sujos.append(self.ret_principal)
        playlist = self.playlists[self.lista_grande]
        if playlist.desenhar(self.faixas, self.indice, self.cursor, self.foco == "playlist") \
                or relayout:
            tela.blit(playlist.sup, self.ret_playlist)
            sujos.append(self.ret_playlist)
        return None if relayout else sujos

    def fechar(self) -> None:
        self.motor.fechar()


def main(argv: Sequence[str] | None = None) -> None:
    p = opcoes_comuns("Dashamp - player")
    p.add_argument("entradas", nargs="*", default=["~/musica"],
                   help="arquivos, pastas ou listas .m3u")
    p.add_argument("--skin", default=os.path.join(PASTA_SKINS, "base-2.91.wsz"))
    p.add_argument("--escala", type=int, choices=(1, 2), default=2)
    args = p.parse_args(argv)
    app = App(args, "Dashamp")
    base = os.path.join(PASTA_SKINS, "base-2.91.wsz")
    padrao = carregar(base) if os.path.exists(base) and \
        os.path.abspath(base) != os.path.abspath(args.skin) else None
    skin = carregar(args.skin, padrao=padrao)
    skin.converter()
    t0 = time.perf_counter()
    faixas = carregar_lista(args.entradas)
    print(f"{len(faixas)} faixa(s) carregada(s) em {time.perf_counter() - t0:.2f} s; "
          f"skin {skin.nome}", flush=True)
    player = Player(app, skin, faixas, args.escala)
    try:
        app.rodar(player.quadro, player.ao_evento)
    finally:
        player.fechar()


if __name__ == "__main__":
    main()
