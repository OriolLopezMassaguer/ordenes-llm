import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from lpo import LPO, fuerza_bruta, orienta, reglas_no_orientadas  # noqa: E402
from terminos import TRS, leer_termino, renombrar  # noqa: E402


def trs(nombre, reglas, vars_="x y z"):
    vs = set(vars_.split())
    return TRS(nombre, [tuple(leer_termino(p, vs) for p in r.split(" -> ")) for r in reglas])


SUMA = trs("suma", ["plus(0, y) -> y", "plus(s(x), y) -> s(plus(x, y))"])

ACKERMANN = trs("ack", [
    "ack(0, y) -> s(y)",
    "ack(s(x), 0) -> ack(x, s(0))",
    "ack(s(x), s(y)) -> ack(x, ack(s(x), y))",
])

# Conmutatividad: ningún orden de reducción la orienta.
CONMUT = trs("conmut", ["plus(x, y) -> plus(y, x)"])

# Asociatividad: LPO la orienta (lexicográfico sobre el primer argumento).
ASOC = trs("asoc", ["times(times(x, y), z) -> times(x, times(y, z))"])


def test_suma_necesita_plus_mayor_que_s():
    assert orienta(SUMA, ["plus", "s", "0"])
    assert not orienta(SUMA, ["s", "plus", "0"])
    assert reglas_no_orientadas(SUMA, ["s", "plus", "0"]) == [1]


def test_ackermann_es_lpo():
    assert orienta(ACKERMANN, ["ack", "s", "0"])


def test_conmutatividad_imposible():
    sol, _, _ = fuerza_bruta(CONMUT)
    assert sol is None


def test_asociatividad_por_lexicografico():
    assert orienta(ASOC, ["times"])


def test_variable_y_subtermino():
    lpo = LPO([])
    x = leer_termino("x", {"x"})
    assert lpo.gt(leer_termino("f(x)", {"x"}), x)
    assert not lpo.gt(x, leer_termino("f(x)", {"x"}))


def test_precedencia_parcial():
    # sin 's' en la lista, plus y s son incomparables
    assert not orienta(SUMA, ["plus"])


def test_fuerza_bruta_cuenta():
    sol, buenas, probadas = fuerza_bruta(SUMA, contar=True)
    assert sol is not None and probadas == 6
    # orientan exactamente las permutaciones con plus > s: 3 de 6
    assert buenas == 3


def test_renombrado_preserva_orientabilidad():
    r = renombrar(SUMA)
    assert set(r.renombrado.values()) == {"plus", "0", "s"}
    inv = {v: k for k, v in r.renombrado.items()}
    assert orienta(r, [inv["plus"], inv["s"], inv["0"]])
