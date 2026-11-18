"""Lista de faixas com metadados lidos rápido, sem GStreamer (F1.7).

- MP3: título/artista da etiqueta ID3v2 (2.3/2.4; TIT2/TPE1) e duração pelo cabeçalho Xing/Info
  (VBR) ou pelo bitrate do primeiro quadro (CBR). Lê só o começo do arquivo.
- .m3u/.m3u8: caminhos relativos à pasta da lista; `#EXTINF:segundos,Artista - Título` é usado.
- Outros formatos: nome do arquivo, sem duração.
"""
from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass

EXTENSOES = (".mp3", ".ogg", ".flac", ".wav", ".m4a", ".opus")
LISTAS = (".m3u", ".m3u8")
LEITURA_INICIAL = 64 * 1024

# Layer III: bitrates (kbps) por índice, para MPEG-1 e MPEG-2/2.5.
_BITRATES = {
    1: (0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320),
    2: (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160),
}
_TAXAS = {1: (44100, 48000, 32000), 2: (22050, 24000, 16000), 25: (11025, 12000, 8000)}


@dataclass
class Faixa:
    caminho: str
    titulo: str = ""
    artista: str = ""
    duracao: float | None = None

    @property
    def nome(self) -> str:
        """Como o Winamp mostra: 'Artista - Título', ou o nome do arquivo."""
        if self.titulo:
            return f"{self.artista} - {self.titulo}" if self.artista else self.titulo
        return os.path.splitext(os.path.basename(self.caminho))[0]


# ---------------------------------------------------------------------------
# MP3


def _syncsafe(b: bytes) -> int:
    return (b[0] << 21) | (b[1] << 14) | (b[2] << 7) | b[3]


def _texto_id3(dados: bytes) -> str:
    if not dados:
        return ""
    cod, corpo = dados[0], dados[1:]
    codec = {0: "latin-1", 1: "utf-16", 2: "utf-16-be", 3: "utf-8"}.get(cod, "latin-1")
    return corpo.decode(codec, errors="replace").split("\x00")[0].strip()


def _ler_id3v2(cab: bytes) -> tuple[dict[str, str], int]:
    """(quadros de texto, tamanho total da etiqueta). Etiqueta ausente: ({}, 0)."""
    if len(cab) < 10 or cab[:3] != b"ID3":
        return {}, 0
    versao, flags = cab[3], cab[5]
    tamanho = 10 + _syncsafe(cab[6:10]) + (10 if flags & 0x10 else 0)
    quadros: dict[str, str] = {}
    i, fim = 10, min(len(cab), 10 + _syncsafe(cab[6:10]))
    while i + 10 <= fim and cab[i:i + 4].isalnum():
        ident = cab[i:i + 4].decode("latin-1")
        n = _syncsafe(cab[i + 4:i + 8]) if versao >= 4 else int.from_bytes(cab[i + 4:i + 8], "big")
        if n <= 0 or i + 10 + n > len(cab):
            break
        if ident in ("TIT2", "TPE1"):
            quadros[ident] = _texto_id3(cab[i + 10:i + 10 + n])
        i += 10 + n
    return quadros, tamanho


def _duracao_mp3(cab: bytes, inicio: int, tamanho_arquivo: int, tem_id3v1: bool) -> float | None:
    """Acha o primeiro quadro a partir de `inicio` e calcula a duração."""
    for i in range(inicio, min(len(cab) - 4, inicio + 8192)):
        if cab[i] != 0xFF or (cab[i + 1] & 0xE0) != 0xE0:
            continue
        h = int.from_bytes(cab[i:i + 4], "big")
        versao_bits, camada = (h >> 19) & 3, (h >> 17) & 3
        idx_br, idx_taxa, canal = (h >> 12) & 15, (h >> 10) & 3, (h >> 6) & 3
        if camada != 1 or versao_bits == 1 or idx_br in (0, 15) or idx_taxa == 3:
            continue  # só Layer III; cabeçalho inválido: continua procurando
        versao = {3: 1, 2: 2, 0: 25}[versao_bits]
        taxa = _TAXAS[versao][idx_taxa]
        amostras = 1152 if versao == 1 else 576
        mono = canal == 3
        lado = (17 if mono else 32) if versao == 1 else (9 if mono else 17)
        xing = i + 4 + lado
        if cab[xing:xing + 4] in (b"Xing", b"Info") and cab[xing + 7] & 1:
            quadros = int.from_bytes(cab[xing + 8:xing + 12], "big")
            return quadros * amostras / taxa
        kbps = _BITRATES[1 if versao == 1 else 2][idx_br]
        audio = tamanho_arquivo - i - (128 if tem_id3v1 else 0)
        return audio * 8 / (kbps * 1000)
    return None


def ler_mp3(caminho: str) -> Faixa:
    faixa = Faixa(caminho)
    try:
        with open(caminho, "rb") as f:
            cab = f.read(LEITURA_INICIAL)
            tamanho = os.fstat(f.fileno()).st_size
            quadros, tam_id3 = _ler_id3v2(cab)
            if tam_id3 + 4096 > len(cab):  # etiqueta grande (capa): lê o trecho depois dela
                f.seek(tam_id3)
                cab = b"\x00" * tam_id3 + f.read(8192 + 64)
            f.seek(max(0, tamanho - 128))
            tem_id3v1 = f.read(3) == b"TAG"
    except OSError:
        return faixa
    faixa.titulo = quadros.get("TIT2", "")
    faixa.artista = quadros.get("TPE1", "")
    faixa.duracao = _duracao_mp3(cab, tam_id3, tamanho, tem_id3v1)
    return faixa


# ---------------------------------------------------------------------------
# Listas


def ler_m3u(caminho: str) -> list[Faixa]:
    pasta = os.path.dirname(os.path.abspath(caminho))
    faixas: list[Faixa] = []
    extinf: tuple[float | None, str] | None = None
    with open(caminho, encoding="utf-8", errors="replace") as f:
        for linha in f:
            linha = linha.strip().lstrip("﻿")
            if linha.upper().startswith("#EXTINF:"):
                dur, _, nome = linha[8:].partition(",")
                try:
                    segundos: float | None = float(dur) if float(dur) >= 0 else None
                except ValueError:
                    segundos = None
                extinf = (segundos, nome.strip())
            elif linha and not linha.startswith("#"):
                arquivo = linha if os.path.isabs(linha) else os.path.join(pasta, linha)
                faixa = carregar_arquivo(os.path.normpath(arquivo))
                if extinf is not None:
                    if faixa.duracao is None:
                        faixa.duracao = extinf[0]
                    if not faixa.titulo and extinf[1]:
                        artista, _, titulo = extinf[1].partition(" - ")
                        faixa.artista, faixa.titulo = (artista, titulo) if titulo else ("", artista)
                    extinf = None
                faixas.append(faixa)
    return faixas


def carregar_arquivo(caminho: str) -> Faixa:
    return ler_mp3(caminho) if caminho.lower().endswith(".mp3") else Faixa(caminho)


def carregar_lista(entradas: Sequence[str]) -> list[Faixa]:
    """Arquivos, pastas (recursivas, em ordem alfabética) e listas .m3u, na ordem dada."""
    faixas: list[Faixa] = []
    for entrada in entradas:
        entrada = os.path.expanduser(entrada)
        if os.path.isdir(entrada):
            for raiz, pastas, arquivos in os.walk(entrada):
                pastas.sort()
                faixas += [carregar_arquivo(os.path.join(raiz, a)) for a in sorted(arquivos)
                           if a.lower().endswith(EXTENSOES)]
        elif entrada.lower().endswith(LISTAS) and os.path.exists(entrada):
            faixas += ler_m3u(entrada)
        elif entrada.lower().endswith(EXTENSOES) and os.path.exists(entrada):
            faixas.append(carregar_arquivo(entrada))
    return faixas
