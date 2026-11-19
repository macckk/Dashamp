"""Widgets do painel (F2.4): Ponteiro, Barra, Digitos, LuzEspia e Historico, mais o `Painel`
que os junta a uma fonte."""
from painel.widgets.barra import Barra
from painel.widgets.base import Widget, Zona
from painel.widgets.digitos import Digitos
from painel.widgets.historico import Historico
from painel.widgets.luz import LuzEspia
from painel.widgets.painel import Painel
from painel.widgets.ponteiro import Ponteiro

__all__ = ["Barra", "Digitos", "Historico", "LuzEspia", "Painel", "Ponteiro", "Widget", "Zona"]
