import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from llm import Cliente, extraer_precedencia, resolver  # noqa: E402
from test_lpo import CONMUT, SUMA, trs  # noqa: E402


class Guionizado(Cliente):
    """Cliente falso que devuelve respuestas fijadas de antemano."""

    def __init__(self, respuestas):
        super().__init__()
        self.respuestas = list(respuestas)

    def _completar(self):
        return self.respuestas.pop(0)


def test_extraer_ultimo_json():
    texto = 'Pruebo {"precedencia": ["a"]} ... mejor:\n{"precedencia": ["plus", "s", "0"]}'
    assert extraer_precedencia(texto) == ["plus", "s", "0"]
    assert extraer_precedencia("sin json") is None


def test_feedback_y_acierto_al_segundo_intento():
    c = Guionizado([
        '{"precedencia": ["s", "plus", "0"]}',
        'Vale, plus debe ser mayor que s. {"precedencia": ["plus", "s", "0"]}',
    ])
    r = resolver(SUMA, c)
    assert r.resuelto and r.intentos == 2
    assert r.historial[0]["reglas_fallidas"] == [2]
    assert "NO orienta" in c.mensajes[2]["content"]


def test_simbolo_inventado():
    c = Guionizado(['{"precedencia": ["mas", "s"]}', '{"precedencia": ["plus", "s", "0"]}'])
    r = resolver(SUMA, c)
    assert r.resuelto and "desconocidos" in r.historial[0]["error"]


def test_no_viable_no_llama_al_llm():
    # la parte derecha introduce una variable nueva: no termina, ni se pregunta
    r = resolver(trs("nuevavar", ["f(x) -> g(y)"]), Guionizado([]))
    assert not r.resuelto and r.intentos == 0


def test_conmutatividad_agota_intentos():
    c = Guionizado(['{"precedencia": ["plus"]}'] * 3)
    r = resolver(CONMUT, c, max_intentos=3)
    assert not r.resuelto and r.intentos == 3
