"""Selecciona el subconjunto de la fase 1 a partir de la TPDB y lo guarda en problemas/fase1/.

No hace falta ejecutarlo: el subconjunto ya viene en el repo. Sirve para regenerarlo
o ampliarlo. Uso:

    git clone --depth 1 https://github.com/TermCOMP/TPDB.git ../TPDB
    python scripts/seleccionar_problemas.py ../TPDB --resolubles 40 --no-resolubles 10
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from lpo import fuerza_bruta, regla_viable  # noqa: E402
from terminos import NoSoportado, leer_xtc, renombrar  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tpdb", type=Path, help="carpeta raíz de la TPDB clonada")
    ap.add_argument("--resolubles", type=int, default=40)
    ap.add_argument("--no-resolubles", type=int, default=10)
    ap.add_argument("--max-reglas", type=int, default=10)
    ap.add_argument("--min-simbolos", type=int, default=3)
    ap.add_argument("--max-simbolos", type=int, default=7)
    ap.add_argument("--semilla", type=int, default=1997)
    ap.add_argument("--salida", type=Path, default=RAIZ / "problemas" / "fase1")
    args = ap.parse_args()

    resolubles, no_resolubles, vistos = [], [], set()
    for xml in sorted((args.tpdb / "TRS_Standard").rglob("*.xml")):
        try:
            trs = leer_xtc(xml)
        except (NoSoportado, Exception):
            continue
        n = len(trs.signatura)
        if not trs.reglas or len(trs.reglas) > args.max_reglas:
            continue
        if not (args.min_simbolos <= n <= args.max_simbolos):
            continue
        if not all(regla_viable(l, r) for l, r in trs.reglas):
            continue
        ren = renombrar(trs)
        if ren.texto() in vistos:  # la TPDB tiene duplicados
            continue
        vistos.add(ren.texto())
        ren.nombre = f"{xml.parent.name}__{xml.stem}"
        ren.origen = xml.relative_to(args.tpdb).as_posix()
        sol, buenas, total = fuerza_bruta(ren, contar=True)
        datos = ren.a_json() | {"lpo": {"resoluble": sol is not None, "soluciones": buenas,
                                        "precedencias": total, "ejemplo": sol}}
        (resolubles if sol else no_resolubles).append(datos)

    print(f"candidatos: {len(resolubles)} resolubles por LPO, {len(no_resolubles)} no resolubles")

    rnd = random.Random(args.semilla)
    # resolubles repartidos por dificultad: ordenar por fracción de precedencias
    # válidas y tomar muestras equiespaciadas
    resolubles.sort(key=lambda d: d["lpo"]["soluciones"] / d["lpo"]["precedencias"])
    k = min(args.resolubles, len(resolubles))
    elegidos = [resolubles[round(i * (len(resolubles) - 1) / max(k - 1, 1))] for i in range(k)]
    elegidos += rnd.sample(no_resolubles, min(args.no_resolubles, len(no_resolubles)))

    args.salida.mkdir(parents=True, exist_ok=True)
    for d in elegidos:
        (args.salida / f"{d['nombre']}.json").write_text(
            json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"guardados {len(elegidos)} problemas en {args.salida}")


if __name__ == "__main__":
    main()
