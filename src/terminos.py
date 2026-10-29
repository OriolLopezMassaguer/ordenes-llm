"""Términos, sistemas de reescritura (TRS) y su lectura desde la TPDB (formato XTC)."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------- términos

@dataclass(frozen=True)
class Var:
    nombre: str

    def __str__(self) -> str:
        return self.nombre


@dataclass(frozen=True)
class Fun:
    nombre: str
    args: tuple = ()

    def __str__(self) -> str:
        if not self.args:
            return self.nombre
        return f"{self.nombre}({', '.join(str(a) for a in self.args)})"


Termino = Var | Fun


def variables(t: Termino) -> set[str]:
    if isinstance(t, Var):
        return {t.nombre}
    out: set[str] = set()
    for a in t.args:
        out |= variables(a)
    return out


def simbolos(t: Termino) -> dict[str, int]:
    """Símbolos de función de t con su aridad."""
    if isinstance(t, Var):
        return {}
    out = {t.nombre: len(t.args)}
    for a in t.args:
        out.update(simbolos(a))
    return out


# ------------------------------------------------- lectura desde texto
# Sintaxis: f(x, g(y)) ; las constantes pueden escribirse "c" o "c()".
# Qué identificadores son variables lo dice el conjunto `vars_`.

_TOKEN = re.compile(r"\s*([A-Za-z0-9_'.+\-*<>=!?:#@$%&^~|/\\]+|\(|\)|,)")


def leer_termino(texto: str, vars_: set[str]) -> Termino:
    tokens = [m.group(1) for m in _TOKEN.finditer(texto)]
    pos = 0

    def termino() -> Termino:
        nonlocal pos
        nombre = tokens[pos]
        pos += 1
        if pos < len(tokens) and tokens[pos] == "(":
            pos += 1
            args = []
            if tokens[pos] != ")":
                args.append(termino())
                while tokens[pos] == ",":
                    pos += 1
                    args.append(termino())
            assert tokens[pos] == ")", f"se esperaba ')' en {texto!r}"
            pos += 1
            return Fun(nombre, tuple(args))
        return Var(nombre) if nombre in vars_ else Fun(nombre)

    t = termino()
    assert pos == len(tokens), f"texto sobrante en {texto!r}"
    return t


# ---------------------------------------------------------------- TRS

@dataclass
class TRS:
    nombre: str
    reglas: list[tuple[Termino, Termino]]
    origen: str = ""
    renombrado: dict[str, str] = field(default_factory=dict)  # nuevo -> original

    @property
    def signatura(self) -> dict[str, int]:
        sig: dict[str, int] = {}
        for l, r in self.reglas:
            sig.update(simbolos(l))
            sig.update(simbolos(r))
        return sig

    @property
    def vars_(self) -> set[str]:
        out: set[str] = set()
        for l, r in self.reglas:
            out |= variables(l) | variables(r)
        return out

    def texto(self) -> str:
        return "\n".join(f"{l} -> {r}" for l, r in self.reglas)

    # -- persistencia propia (JSON legible)
    def a_json(self) -> dict:
        return {
            "nombre": self.nombre,
            "origen": self.origen,
            "variables": sorted(self.vars_),
            "reglas": [f"{l} -> {r}" for l, r in self.reglas],
            "renombrado": self.renombrado,
        }

    @staticmethod
    def de_json(d: dict) -> "TRS":
        vs = set(d["variables"])
        reglas = []
        for linea in d["reglas"]:
            l, r = linea.split(" -> ", 1)
            reglas.append((leer_termino(l, vs), leer_termino(r, vs)))
        return TRS(d["nombre"], reglas, d.get("origen", ""), d.get("renombrado", {}))

    @staticmethod
    def cargar(ruta: str | Path) -> "TRS":
        return TRS.de_json(json.loads(Path(ruta).read_text(encoding="utf-8")))

    def guardar(self, ruta: str | Path) -> None:
        Path(ruta).write_text(json.dumps(self.a_json(), indent=2, ensure_ascii=False), encoding="utf-8")


# ------------------------------------------------------ lectura XTC

class NoSoportado(Exception):
    """El problema usa algo fuera del alcance de la fase 1."""


def _xtc_termino(nodo: ET.Element) -> Termino:
    if nodo.tag == "var":
        return Var(nodo.text.strip())
    if nodo.tag == "funapp":
        nombre = nodo.find("name").text.strip()
        args = tuple(_xtc_termino(a[0]) for a in nodo.findall("arg"))
        return Fun(nombre, args)
    raise NoSoportado(f"nodo de término desconocido: {nodo.tag}")


def leer_xtc(ruta: str | Path) -> TRS:
    """Lee un TRS estándar (sin condiciones, teorías ni reglas relativas)."""
    ruta = Path(ruta)
    raiz = ET.parse(ruta).getroot()
    if raiz.get("type") != "termination":
        raise NoSoportado("no es un problema de terminación")
    estrategia = raiz.findtext("strategy", "FULL").strip()
    if estrategia != "FULL":
        raise NoSoportado(f"estrategia {estrategia}")
    trs = raiz.find("trs")
    if trs.find("relrules") is not None:
        raise NoSoportado("reglas relativas")
    if trs.find("signature/funcsym/theory") is not None:
        raise NoSoportado("teoría ecuacional (p. ej. AC)")
    reglas = []
    for regla in trs.findall("rules/rule"):
        if regla.find("conditions") is not None:
            raise NoSoportado("reglas condicionales")
        reglas.append((_xtc_termino(regla.find("lhs")[0]), _xtc_termino(regla.find("rhs")[0])))
    return TRS(ruta.stem, reglas, origen=str(ruta))


# ------------------------------------------------------ renombrado

def _renombrar_t(t: Termino, fs: dict[str, str], xs: dict[str, str]) -> Termino:
    if isinstance(t, Var):
        return Var(xs.setdefault(t.nombre, f"x{len(xs) + 1}"))
    nuevo = fs.setdefault(t.nombre, f"f{len(fs) + 1}")
    return Fun(nuevo, tuple(_renombrar_t(a, fs, xs) for a in t.args))


def renombrar(trs: TRS) -> TRS:
    """Símbolos -> f1, f2, … y variables -> x1, x2, … por orden de aparición.

    Evita que el LLM reconozca el problema (plus, ack, …) y tire de soluciones
    memorizadas: así medimos razonamiento sobre la estructura, no memoria.
    """
    fs: dict[str, str] = {}
    reglas = []
    for l, r in trs.reglas:
        xs: dict[str, str] = {}  # las variables son locales a cada regla
        reglas.append((_renombrar_t(l, fs, xs), _renombrar_t(r, fs, xs)))
    return TRS(trs.nombre, reglas, trs.origen, {v: k for k, v in fs.items()})
