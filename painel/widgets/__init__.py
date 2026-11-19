"""Widgets do painel: Ponteiro, Barra, Digitos, LuzEspia e Historico (F2.4), Arco e Numero
(F2.6), mais o `Painel` que os junta a uma fonte."""
from painel.widgets.arco import Arco
from painel.widgets.barra import Barra
from painel.widgets.base import Widget, Zona
from painel.widgets.digitos import Digitos
from painel.widgets.historico import Historico
from painel.widgets.luz import LuzEspia
from painel.widgets.numero import Numero
from painel.widgets.painel import Painel
from painel.widgets.ponteiro import Ponteiro

__all__ = ["Arco", "Barra", "Digitos", "Historico", "LuzEspia", "Numero", "Painel", "Ponteiro",
           "Widget", "Zona"]
