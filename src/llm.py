"""Bucle generar-y-comprobar: el LLM propone una precedencia LPO, el comprobador decide.

Proveedores:
  manual     — muestra el prompt; pegas la respuesta de cualquier chat (sin API ni coste)
  anthropic  — API de Anthropic (pip install anthropic; variable ANTHROPIC_API_KEY)
  openai     — cualquier API compatible con OpenAI; por defecto Ollama en local
               (ORDENES_LLM_URL, ORDENES_LLM_CLAVE)

El modelo se elige con ORDENES_LLM_MODELO o con --modelo en los scripts.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from dataclasses import dataclass, field

from lpo import regla_viable, reglas_no_orientadas
from terminos import TRS

INSTRUCCIONES = """\
Eres un experto en terminación de sistemas de reescritura.

Te doy un sistema de reescritura de términos (TRS). Tu tarea es encontrar una
precedencia (orden estricto total entre los símbolos de función) tal que el
orden lexicográfico de caminos (LPO) orienta TODAS las reglas: l >_lpo r.

Definición de LPO, dada una precedencia >:
s >_lpo t si y solo si s = f(s1,...,sn) y se cumple uno de:
  (1) si >=_lpo t para algún i  (>= significa > o igual);
  (2) t = g(t1,...,tm), f > g y s >_lpo tj para todo j;
  (3) t = f(t1,...,tn) (mismo símbolo), s >_lpo tj para todo j, y
      (s1,...,sn) es mayor que (t1,...,tn) en el orden lexicográfico
      inducido por >_lpo (el primer argumento distinto decide).
Además, s >_lpo x para una variable x si x aparece en s y s != x.

Razona brevemente y termina tu respuesta con un objeto JSON, en una sola línea:
{"precedencia": ["simbolo_mayor", ..., "simbolo_menor"]}
Incluye todos los símbolos de la signatura exactamente una vez.
"""


def prompt_inicial(trs: TRS) -> str:
    sig = ", ".join(f"{f}/{a}" for f, a in sorted(trs.signatura.items()))
    reglas = "\n".join(f"  {i + 1}: {l} -> {r}" for i, (l, r) in enumerate(trs.reglas))
    vs = ", ".join(sorted(trs.vars_))
    return f"Signatura (símbolo/aridad): {sig}\nVariables: {vs}\nReglas:\n{reglas}"


def prompt_feedback(trs: TRS, prec: list[str], fallan: list[int]) -> str:
    lineas = "\n".join(f"  {i + 1}: {trs.reglas[i][0]} -> {trs.reglas[i][1]}" for i in fallan)
    return (
        f"Con la precedencia {' > '.join(prec)} el LPO NO orienta estas reglas:\n"
        f"{lineas}\nRevisa por qué y propón otra precedencia (mismo formato JSON)."
    )


_JSON = re.compile(r"\{[^{}]*\"precedencia\"[^{}]*\}", re.S)


def extraer_precedencia(texto: str) -> list[str] | None:
    """Último objeto JSON con clave "precedencia" que aparezca en la respuesta."""
    for bloque in reversed(_JSON.findall(texto)):
        try:
            prec = json.loads(bloque)["precedencia"]
        except (json.JSONDecodeError, KeyError):
            continue
        if isinstance(prec, list) and all(isinstance(s, str) for s in prec):
            return prec
    return None


# ----------------------------------------------------------- proveedores

class Cliente:
    """Conversación con un LLM. `enviar` añade el mensaje y devuelve la respuesta."""

    def __init__(self):
        self.mensajes: list[dict] = []

    def enviar(self, texto: str) -> str:
        self.mensajes.append({"role": "user", "content": texto})
        respuesta = self._completar()
        self.mensajes.append({"role": "assistant", "content": respuesta})
        return respuesta

    def _completar(self) -> str:
        raise NotImplementedError


class Manual(Cliente):
    nombre = "manual"

    def _completar(self) -> str:
        print("\n" + "=" * 70)
        if len(self.mensajes) == 1:
            print(INSTRUCCIONES)
        print(self.mensajes[-1]["content"])
        print("=" * 70)
        print("Pega la respuesta del LLM y termina con una línea que diga FIN:")
        lineas = []
        for linea in sys.stdin:
            if linea.strip() == "FIN":
                break
            lineas.append(linea)
        return "".join(lineas)


class Anthropic(Cliente):
    nombre = "anthropic"

    def __init__(self, modelo: str):
        super().__init__()
        import anthropic  # dependencia opcional

        self.api = anthropic.Anthropic()
        self.modelo = modelo

    def _completar(self) -> str:
        r = self.api.messages.create(
            model=self.modelo, max_tokens=4000, system=INSTRUCCIONES, messages=self.mensajes
        )
        return "".join(b.text for b in r.content if b.type == "text")


class OpenAICompatible(Cliente):
    """Vale para Ollama (por defecto), LM Studio, OpenAI y similares."""

    nombre = "openai"

    def __init__(self, modelo: str, url: str | None = None, clave: str | None = None):
        super().__init__()
        self.modelo = modelo
        self.url = (url or os.environ.get("ORDENES_LLM_URL", "http://localhost:11434/v1")).rstrip("/")
        self.clave = clave or os.environ.get("ORDENES_LLM_CLAVE", "ollama")

    def _completar(self) -> str:
        cuerpo = {
            "model": self.modelo,
            "messages": [{"role": "system", "content": INSTRUCCIONES}, *self.mensajes],
        }
        req = urllib.request.Request(
            f"{self.url}/chat/completions",
            data=json.dumps(cuerpo).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.clave}"},
        )
        with urllib.request.urlopen(req, timeout=600) as resp:
            return json.loads(resp.read())["choices"][0]["message"]["content"]


def crear_cliente(proveedor: str, modelo: str | None = None) -> Cliente:
    modelo = modelo or os.environ.get("ORDENES_LLM_MODELO")
    if proveedor == "manual":
        return Manual()
    if proveedor == "anthropic":
        return Anthropic(modelo or "claude-sonnet-5-5")
    if proveedor == "openai":
        if not modelo:
            raise SystemExit("Indica el modelo con --modelo o ORDENES_LLM_MODELO (p. ej. qwen3:8b)")
        return OpenAICompatible(modelo)
    raise SystemExit(f"Proveedor desconocido: {proveedor}")


# ------------------------------------------------------------ el bucle

@dataclass
class Resultado:
    resuelto: bool
    intentos: int
    precedencia: list[str] | None
    historial: list[dict] = field(default_factory=list)


def resolver(trs: TRS, cliente: Cliente, max_intentos: int = 4) -> Resultado:
    """Pide precedencias al LLM y las comprueba; devuelve el historial completo."""
    if not all(regla_viable(l, r) for l, r in trs.reglas):
        return Resultado(False, 0, None, [{"nota": "TRS no orientable por ningún orden de reducción"}])

    sig = set(trs.signatura)
    historial: list[dict] = []
    mensaje = prompt_inicial(trs)
    for intento in range(1, max_intentos + 1):
        respuesta = cliente.enviar(mensaje)
        prec = extraer_precedencia(respuesta)
        paso = {"intento": intento, "respuesta": respuesta, "precedencia": prec}
        historial.append(paso)

        if prec is None:
            mensaje = 'No encuentro el JSON. Termina con {"precedencia": [...]} en una sola línea.'
            continue
        desconocidos = [s for s in prec if s not in sig]
        if desconocidos:
            paso["error"] = f"símbolos desconocidos: {desconocidos}"
            mensaje = f"Los símbolos {desconocidos} no están en la signatura. Usa solo: {sorted(sig)}."
            continue

        fallan = reglas_no_orientadas(trs, prec)
        paso["reglas_fallidas"] = [i + 1 for i in fallan]
        if not fallan:
            return Resultado(True, intento, prec, historial)
        mensaje = prompt_feedback(trs, prec, fallan)
        faltan = sorted(sig - set(prec))
        if faltan:
            mensaje += f"\nNota: no has incluido {faltan}; quedan incomparables con el resto."

    return Resultado(False, max_intentos, None, historial)
