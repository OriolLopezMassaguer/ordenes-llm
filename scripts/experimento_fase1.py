"""Fase 1: el LLM propone precedencias LPO para los problemas de problemas/fase1/.

Ejemplos:
    # sin API: copias el prompt a un chat y pegas la respuesta (empieza con pocos)
    python scripts/experimento_fase1.py --proveedor manual --limite 3

    # modelo local con Ollama
    python scripts/experimento_fase1.py --proveedor openai --modelo qwen3:8b

    # API de Anthropic (ANTHROPIC_API_KEY en el entorno)
    python scripts/experimento_fase1.py --proveedor anthropic

Cada ejecución deja en experimentos/ un .jsonl con todo el historial (prompts y
respuestas) y un resumen .md con la tabla de resultados.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from llm import crear_cliente, resolver  # noqa: E402
from terminos import TRS  # noqa: E402


def cargar_problemas(carpeta: Path, solo: str | None, solo_resolubles: bool):
    for f in sorted(carpeta.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        if solo and solo not in d["nombre"]:
            continue
        if solo_resolubles and not d["lpo"]["resoluble"]:
            continue
        yield d


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--proveedor", choices=["manual", "anthropic", "openai"], default="manual")
    ap.add_argument("--modelo")
    ap.add_argument("--intentos", type=int, default=4, help="máximo de propuestas por problema")
    ap.add_argument("--limite", type=int, help="procesar solo los N primeros problemas")
    ap.add_argument("--problema", help="solo problemas cuyo nombre contenga este texto")
    ap.add_argument("--solo-resolubles", action="store_true", help="omitir los de control (no LPO)")
    ap.add_argument("--problemas", type=Path, default=RAIZ / "problemas" / "fase1")
    args = ap.parse_args()

    problemas = list(cargar_problemas(args.problemas, args.problema, args.solo_resolubles))
    if args.limite:
        problemas = problemas[: args.limite]
    if not problemas:
        raise SystemExit("No hay problemas que procesar.")

    etiqueta = f"{args.proveedor}-{(args.modelo or 'defecto').replace(':', '_').replace('/', '_')}"
    sello = datetime.now().strftime("%Y%m%d-%H%M%S")
    salida = RAIZ / "experimentos"
    salida.mkdir(exist_ok=True)
    ruta_jsonl = salida / f"{sello}_fase1_{etiqueta}.jsonl"

    filas = []
    with ruta_jsonl.open("w", encoding="utf-8") as log:
        for i, d in enumerate(problemas, 1):
            trs = TRS.de_json(d)
            cliente = crear_cliente(args.proveedor, args.modelo)
            print(f"[{i}/{len(problemas)}] {d['nombre']} … ", end="", flush=True)
            try:
                r = resolver(trs, cliente, args.intentos)
                error = None
            except Exception as e:  # red, cuota, etc.: se anota y se sigue
                r, error = None, f"{type(e).__name__}: {e}"
            lpo = d["lpo"]
            fila = {
                "problema": d["nombre"],
                "lpo_resoluble": lpo["resoluble"],
                "facilidad": round(lpo["soluciones"] / lpo["precedencias"], 3) if lpo["resoluble"] else 0.0,
                "llm_resuelve": bool(r and r.resuelto),
                "intentos": r.intentos if r else None,
                "precedencia": r.precedencia if r else None,
                "error": error,
            }
            filas.append(fila)
            log.write(json.dumps(fila | {"historial": r.historial if r else []}, ensure_ascii=False) + "\n")
            log.flush()
            print("✔" if fila["llm_resuelve"] else ("error" if error else "✘"),
                  f"({fila['intentos']} intentos)" if fila["intentos"] else "")

    ruta_md = ruta_jsonl.with_suffix(".md")
    ruta_md.write_text(resumen(filas, etiqueta, args), encoding="utf-8")
    print(f"\nResumen: {ruta_md}\nHistorial: {ruta_jsonl}")
    print(resumen_corto(filas))


def resumen_corto(filas) -> str:
    res = [f for f in filas if f["lpo_resoluble"]]
    ok = [f for f in res if f["llm_resuelve"]]
    falsos = [f for f in filas if f["llm_resuelve"] and not f["lpo_resoluble"]]
    texto = f"LLM resuelve {len(ok)}/{len(res)} problemas resolubles por LPO"
    if ok:
        texto += f"; media de intentos: {sum(f['intentos'] for f in ok) / len(ok):.2f}"
    if falsos:  # imposible si el comprobador es correcto: sería un fallo nuestro
        texto += f"\n¡ATENCIÓN! {len(falsos)} 'resueltos' que la fuerza bruta no resolvía."
    return texto


def resumen(filas, etiqueta, args) -> str:
    lineas = [
        f"# Fase 1 — {etiqueta}",
        "",
        f"Fecha: {datetime.now():%Y-%m-%d %H:%M} · intentos máx.: {args.intentos} · problemas: {len(filas)}",
        "",
        resumen_corto(filas),
        "",
        "Facilidad = fracción de precedencias totales que orientan el TRS (1 = cualquiera vale).",
        "",
        "| Problema | LPO | Facilidad | LLM | Intentos | Precedencia |",
        "|---|---|---|---|---|---|",
    ]
    for f in filas:
        llm = "error" if f["error"] else ("✔" if f["llm_resuelve"] else "✘")
        prec = " > ".join(f["precedencia"]) if f["precedencia"] else ""
        lineas.append(f"| {f['problema']} | {'sí' if f['lpo_resoluble'] else 'no'} | "
                      f"{f['facilidad']} | {llm} | {f['intentos'] or ''} | {prec} |")
    return "\n".join(lineas) + "\n"


if __name__ == "__main__":
    main()
