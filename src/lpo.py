"""Orden lexicográfico de caminos (LPO) y búsqueda exhaustiva de precedencias."""

from __future__ import annotations

from itertools import permutations
from typing import Iterable, Sequence

from terminos import TRS, Fun, Termino, Var, variables


class LPO:
    """LPO para una precedencia dada como lista de mayor a menor.

    Los símbolos que no aparecen en la lista son incomparables con el resto
    (precedencia parcial).
    """

    def __init__(self, precedencia: Sequence[str]):
        self.rango = {f: i for i, f in enumerate(precedencia)}
        self._memo: dict[tuple[Termino, Termino], bool] = {}

    def mayor_prec(self, f: str, g: str) -> bool:
        return f in self.rango and g in self.rango and self.rango[f] < self.rango[g]

    def gt(self, s: Termino, t: Termino) -> bool:
        """s >_lpo t"""
        clave = (s, t)
        if clave not in self._memo:
            self._memo[clave] = self._gt(s, t)
        return self._memo[clave]

    def ge(self, s: Termino, t: Termino) -> bool:
        return s == t or self.gt(s, t)

    def _gt(self, s: Termino, t: Termino) -> bool:
        if isinstance(s, Var):
            return False
        if isinstance(t, Var):
            return t.nombre in variables(s)
        # (1) algún argumento de s es >= t
        if any(self.ge(si, t) for si in s.args):
            return True
        # en los casos (2) y (3), s debe dominar a todos los argumentos de t
        if not all(self.gt(s, tj) for tj in t.args):
            return False
        # (2) f > g en la precedencia
        if self.mayor_prec(s.nombre, t.nombre):
            return True
        # (3) mismo símbolo y argumentos lexicográficamente mayores
        if s.nombre == t.nombre:
            for si, ti in zip(s.args, t.args):
                if si != ti:
                    return self.gt(si, ti)
        return False


# ------------------------------------------------------------ utilidades

def regla_viable(l: Termino, r: Termino) -> bool:
    """Ningún orden de reducción orienta l -> r si l es variable o r tiene
    variables que no están en l (el TRS no termina)."""
    return isinstance(l, Fun) and variables(r) <= variables(l)


def reglas_no_orientadas(trs: TRS, precedencia: Sequence[str]) -> list[int]:
    """Índices (desde 0) de las reglas l -> r con NO l >_lpo r."""
    lpo = LPO(precedencia)
    return [i for i, (l, r) in enumerate(trs.reglas) if not lpo.gt(l, r)]


def orienta(trs: TRS, precedencia: Sequence[str]) -> bool:
    lpo = LPO(precedencia)
    return all(lpo.gt(l, r) for l, r in trs.reglas)


def precedencias_totales(trs: TRS) -> Iterable[tuple[str, ...]]:
    return permutations(sorted(trs.signatura))


def fuerza_bruta(trs: TRS, contar: bool = False, max_simbolos: int = 8):
    """Busca precedencias totales que orienten todas las reglas.

    Basta con órdenes totales: si una precedencia parcial orienta el TRS,
    cualquier extensión total también lo hace (LPO es monótono en la
    precedencia).

    Devuelve (primera_solución | None, nº soluciones | None, nº probadas).
    Con contar=True recorre todas para medir lo "fácil" que es el problema.
    """
    n = len(trs.signatura)
    if n > max_simbolos:
        raise ValueError(f"{n} símbolos: demasiados para fuerza bruta (máx. {max_simbolos})")
    if not all(regla_viable(l, r) for l, r in trs.reglas):
        return None, 0, 0
    primera, buenas, probadas = None, 0, 0
    for prec in precedencias_totales(trs):
        probadas += 1
        if orienta(trs, prec):
            buenas += 1
            if primera is None:
                primera = list(prec)
                if not contar:
                    return primera, None, probadas
    return primera, (buenas if contar else None), probadas
