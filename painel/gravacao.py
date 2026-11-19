"""Formato de gravação de viagens (F2.3): um arquivo SQLite por viagem.

O mesmo formato serve ao painel (replay), ao carputer (gravação OBD, F3.4) e ao servidor (F3.6).

    metadados(chave TEXT PRIMARY KEY, valor TEXT)
        versao       "1"
        criado_em    início da gravação, ISO 8601 em UTC
        fonte        classe da fonte (FonteSimulada, FonteOBD...)
        + o que o gravador receber (hz, veiculo, observacao...); no fechamento:
        duracao_s, leituras
    canais(id INTEGER PRIMARY KEY, nome TEXT UNIQUE, unidade TEXT)
    leituras(t REAL, canal INTEGER, valor REAL)
        uma linha por canal por leitura; `t` em segundos desde o início da fonte;
        `canal` aponta para canais.id (inteiro: ~25 bytes por linha em vez de ~35 com o nome).

As linhas ficam na ordem de gravação (rowid crescente = t crescente), então a leitura sequencial
não precisa de índice. Uma leitura da fonte = as linhas com o mesmo `t`, consecutivas.
Tamanho: 11 canais a 8 Hz ≈ 2,2 kB/s ≈ 8 MB por hora.

Para poupar o flash, o `Gravador` acumula em memória e grava em lote numa transação a cada
`intervalo_s` (10 s por padrão): se a energia cair, perde-se no máximo esse intervalo, e o
arquivo continua íntegro (o SQLite desfaz a transação incompleta).
"""
from __future__ import annotations

import datetime as dt
import sqlite3
import threading
import time
from collections.abc import Iterator, Mapping

from painel.fontes.base import CANAIS, Fonte, Leitura

VERSAO = "1"

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS metadados (chave TEXT PRIMARY KEY, valor TEXT);
CREATE TABLE IF NOT EXISTS canais (id INTEGER PRIMARY KEY, nome TEXT UNIQUE NOT NULL, unidade TEXT);
CREATE TABLE IF NOT EXISTS leituras (t REAL NOT NULL, canal INTEGER NOT NULL, valor REAL NOT NULL);
"""


class Gravador:
    """Grava leituras em lote. Pode ser alimentado direto (`gravar`) ou assinando uma fonte."""

    def __init__(self, caminho: str, metadados: Mapping[str, object] | None = None,
                 intervalo_s: float = 10.0) -> None:
        self.caminho = caminho
        self.intervalo_s = intervalo_s
        # A fonte chama `gravar` na thread dela; `fechar` vem da thread principal.
        self._db = sqlite3.connect(caminho, check_same_thread=False, isolation_level=None)
        self._db.execute("PRAGMA synchronous=NORMAL")
        self._db.executescript(_ESQUEMA)
        self._lock = threading.Lock()
        self._pendentes: list[tuple[float, int, float]] = []
        self._ids: dict[str, int] = {}
        self._ultimo_lote = time.monotonic()
        self.leituras = 0
        self.lotes = 0
        self._t_ultimo = 0.0
        meta = {"versao": VERSAO,
                "criado_em": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
        meta.update({k: str(v) for k, v in (metadados or {}).items()})
        self._db.execute("BEGIN")
        self._db.executemany("INSERT OR REPLACE INTO metadados VALUES (?, ?)", meta.items())
        for i, c in enumerate(CANAIS.values(), start=1):
            self._db.execute("INSERT OR IGNORE INTO canais VALUES (?, ?, ?)", (i, c.nome, c.unidade))
        self._db.execute("COMMIT")
        self._ids = {n: i for i, n in self._db.execute("SELECT id, nome FROM canais")}
        self._fechado = False

    def _id(self, nome: str) -> int:
        i = self._ids.get(nome)
        if i is None:  # canal fora do catálogo: registra assim mesmo (sem unidade)
            cur = self._db.execute("INSERT INTO canais (nome, unidade) VALUES (?, '')", (nome,))
            i = self._ids[nome] = int(cur.lastrowid)
        return i

    def gravar(self, leitura: Leitura) -> None:
        with self._lock:
            if self._fechado:
                return
            for nome, valor in leitura.valores.items():
                self._pendentes.append((leitura.t, self._id(nome), float(valor)))
            self.leituras += 1
            self._t_ultimo = leitura.t
            if time.monotonic() - self._ultimo_lote >= self.intervalo_s:
                self._descarregar()

    def _descarregar(self) -> None:
        self._ultimo_lote = time.monotonic()
        if not self._pendentes:
            return
        self._db.execute("BEGIN")
        self._db.executemany("INSERT INTO leituras VALUES (?, ?, ?)", self._pendentes)
        self._db.execute("COMMIT")
        self._pendentes.clear()
        self.lotes += 1

    def descarregar(self) -> None:
        with self._lock:
            self._descarregar()

    def fechar(self) -> None:
        with self._lock:
            if self._fechado:
                return
            self._descarregar()
            self._db.executemany("INSERT OR REPLACE INTO metadados VALUES (?, ?)",
                                 (("duracao_s", f"{self._t_ultimo:.3f}"),
                                  ("leituras", str(self.leituras))))
            self._db.close()
            self._fechado = True

    def acompanhar(self, fonte: Fonte) -> None:
        """Grava tudo o que a fonte publicar (na thread dela)."""
        fonte.assinar(self.gravar)

    def __enter__(self) -> Gravador:
        return self

    def __exit__(self, *_: object) -> None:
        self.fechar()


# --- leitura ---------------------------------------------------------------------------


def ler_metadados(caminho: str) -> dict[str, str]:
    with sqlite3.connect(caminho) as db:
        return dict(db.execute("SELECT chave, valor FROM metadados"))


def ler_viagem(caminho: str) -> Iterator[tuple[float, dict[str, float]]]:
    """(t, valores) de cada leitura, na ordem gravada. Lê aos poucos (não carrega o arquivo)."""
    db = sqlite3.connect(caminho)
    try:
        versao = dict(db.execute("SELECT chave, valor FROM metadados")).get("versao")
        if versao != VERSAO:
            raise ValueError(f"{caminho}: versão de formato {versao!r}, esperada {VERSAO!r}")
        nomes = dict(db.execute("SELECT id, nome FROM canais"))
        atual_t: float | None = None
        atual: dict[str, float] = {}
        for t, canal, valor in db.execute("SELECT t, canal, valor FROM leituras ORDER BY rowid"):
            if t != atual_t:
                if atual_t is not None:
                    yield atual_t, atual
                atual_t, atual = t, {}
            atual[nomes[canal]] = valor
        if atual_t is not None:
            yield atual_t, atual
    finally:
        db.close()
