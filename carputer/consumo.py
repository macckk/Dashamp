"""Consumo de combustível a partir do OBD-II (F3.2).

Três caminhos, do mais direto ao mais estimado:

1. **PID 01 5E** (taxa de combustível, L/h): poucos carros têm; quando tem, vale ele.
2. **MAF** (01 10, g/s de ar): combustível (g/s) = MAF / (AFR × λ), onde AFR é a relação
   ar/combustível estequiométrica do combustível e λ a razão de equivalência comandada pela
   injeção (01 44; 1,0 se o carro não informa). Litros = gramas / densidade.
3. **Speed-density** (sem MAF): o ar é estimado pela lei dos gases a partir da pressão do coletor
   (MAP, 01 0B), da temperatura do ar (01 0F) e da rotação, com a cilindrada do motor e uma
   eficiência volumétrica (VE, ~0,85) configuráveis:
       ar (g/s) = MAP[kPa] × cilindrada[L] × VE × (rpm / 120) / (0,28705 × T[K])
   (rpm/120: um motor 4 tempos enche os cilindros uma vez a cada duas voltas; 0,28705 kJ/(kg·K) é
   a constante do ar seco.)

Limitações: no corte de injeção (desacelerando engrenado) o ar continua passando e o MAF/MAP
indicam consumo que não existe; a λ comandada corrige parte disso quando o carro a informa.

Combustíveis (valores aproximados, a 20 °C):
- `gasolina`: gasolina pura (E0), AFR 14,7, 745 g/L;
- `gasolina_br`: gasolina C brasileira com 27% de etanol (E27), AFR ≈ 13,1, 757 g/L
  (média por massa de 14,7 e 9,0 com 28% de etanol em massa);
- `etanol`: etanol hidratado (~7% de água em massa), AFR ≈ 8,4, 809 g/L.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

R_AR_KJ = 0.28705            # constante específica do ar seco, kJ/(kg·K) = kPa·L/(g·K)


@dataclass(frozen=True)
class Combustivel:
    nome: str
    afr: float               # relação ar/combustível estequiométrica, em massa
    densidade_g_l: float


COMBUSTIVEIS: dict[str, Combustivel] = {
    "gasolina": Combustivel("gasolina (E0)", 14.7, 745.0),
    "gasolina_br": Combustivel("gasolina C (E27)", 13.1, 757.0),
    "etanol": Combustivel("etanol hidratado", 8.4, 809.0),
}

# Abaixo disto o carro está parado (ou quase): km/L não faz sentido, o painel mostra L/h.
VELOCIDADE_MIN_KMH = 3.0
LH_MIN = 0.05
LACUNA_MAX_S = 2.0           # buraco maior que isto na leitura não entra na média


def lh_por_maf(maf_g_s: float, combustivel: Combustivel, lambda_: float = 1.0) -> float:
    """Consumo em L/h a partir do fluxo de ar (g/s)."""
    if maf_g_s <= 0:
        return 0.0
    lam = lambda_ if lambda_ > 0 else 1.0
    gramas_s = maf_g_s / (combustivel.afr * lam)
    return gramas_s * 3600.0 / combustivel.densidade_g_l


def maf_por_map(map_kpa: float, temp_ar_c: float, rpm: float, cilindrada_l: float,
                ve: float = 0.85) -> float:
    """Fluxo de ar estimado (g/s) para um motor 4 tempos sem sensor MAF."""
    if map_kpa <= 0 or rpm <= 0:
        return 0.0
    return map_kpa * cilindrada_l * ve * (rpm / 120.0) / (R_AR_KJ * (temp_ar_c + 273.15))


def km_por_litro(velocidade_kmh: float, lh: float) -> float | None:
    if velocidade_kmh < VELOCIDADE_MIN_KMH or lh < LH_MIN:
        return None
    return velocidade_kmh / lh


class Consumo:
    """Acrescenta `combustivel_lh`, `consumo_kml` e `consumo_medio_kml` às leituras do OBD.

    `cilindrada_l` só é usada sem MAF (speed-density); sem ela e sem MAF não há consumo."""

    def __init__(self, combustivel: str = "gasolina_br", cilindrada_l: float | None = None,
                 ve: float = 0.85) -> None:
        if combustivel not in COMBUSTIVEIS:
            raise ValueError(f"combustível desconhecido {combustivel!r} "
                             f"(use {', '.join(COMBUSTIVEIS)})")
        self.combustivel = COMBUSTIVEIS[combustivel]
        self.cilindrada_l, self.ve = cilindrada_l, ve
        self.litros = 0.0
        self.km = 0.0
        self.metodo = ""                     # "pid", "maf", "map" ou "" (sem dados)
        self._t: float | None = None
        self._lh_antes = 0.0
        self._vel_antes = 0.0

    def lh(self, v: Mapping[str, float], lh_direto: bool = False) -> float | None:
        if lh_direto and "combustivel_lh" in v:
            self.metodo = "pid"
            return v["combustivel_lh"]
        lam = v.get("lambda", 1.0)
        if "maf" in v:
            self.metodo = "maf"
            return lh_por_maf(v["maf"], self.combustivel, lam)
        if self.cilindrada_l and {"pressao_coletor", "temp_ar", "rpm"} <= v.keys():
            self.metodo = "map"
            ar = maf_por_map(v["pressao_coletor"], v["temp_ar"], v["rpm"], self.cilindrada_l,
                             self.ve)
            return lh_por_maf(ar, self.combustivel, lam)
        self.metodo = ""
        return None

    def atualizar(self, v: Mapping[str, float], t: float,
                  lh_direto: bool = False) -> dict[str, float]:
        """Canais calculados para a leitura `v` no instante `t` (s)."""
        lh = self.lh(v, lh_direto)
        if lh is None:
            return {}
        vel = v.get("velocidade", 0.0)
        if self._t is not None and 0 < t - self._t <= LACUNA_MAX_S:
            dt_h = (t - self._t) / 3600.0
            self.litros += (lh + self._lh_antes) / 2 * dt_h          # trapézio
            self.km += (vel + self._vel_antes) / 2 * dt_h
        self._t, self._lh_antes, self._vel_antes = t, lh, vel
        saida = {"combustivel_lh": lh}
        kml = km_por_litro(vel, lh)
        saida["consumo_kml"] = 0.0 if kml is None else min(kml, 99.9)     # parado: 0
        if self.litros > 0.005 and self.km > 0.05:
            saida["consumo_medio_kml"] = min(self.km / self.litros, 99.9)
        return saida
