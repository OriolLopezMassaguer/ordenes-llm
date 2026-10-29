# Plan: LLMs y órdenes de términos

Proyecto de afición, a ritmo de fines de semana, con puntos claros donde parar.

## Objetivo

Montar un pequeño banco de pruebas donde un LLM propone órdenes o interpretaciones
para sistemas de reescritura (TRS) y un comprobador formal decide si son válidos.
Medir si el LLM aporta algo frente a la búsqueda clásica.

Idea central: **generar y comprobar**. El LLM puede equivocarse; el comprobador no.
Una alucinación cuesta tiempo, nunca corrección.

## Fase 0 — Preparación (una tarde)

- [ ] Entorno Python con `z3-solver` y acceso a un LLM (API, o a mano al principio).
- [ ] Descargar la TPDB (Termination Problems Database, en GitHub). Comprobar qué
      formato usa ahora (históricamente `.trs` / XTC).
- [ ] Elegir ~50 TRS pequeños, sin AC ni reglas condicionales, que se sabe que terminan.
- [ ] **Renombrar símbolos** (`plus` → `f3`, `s` → `g1`, …) para que el LLM no use
      soluciones memorizadas de la TPDB: medimos razonamiento, no memoria.

## Fase 1 — LPO (1–2 fines de semana)

1. [ ] Parser del formato elegido a una representación de términos.
2. [ ] Comprobador de LPO.
3. [ ] **Línea base:** fuerza bruta sobre todas las precedencias (factible con
       signaturas pequeñas).
4. [ ] **Bucle con el LLM:** se le dan las reglas, devuelve una precedencia en JSON;
       si falla, se le dice qué regla no se orienta y repite (máx. 3–5 intentos).
5. [ ] **Métricas:** problemas resueltos, intentos necesarios, casos en que la fuerza
       bruta encuentra y el LLM no.

**Hito:** tabla de resultados. ¿«Entiende» el LLM LPO?

## Fase 2 — Interpretaciones polinómicas con Z3 (2 fines de semana)

1. [ ] Limitarse a polinomios **lineales** con coeficientes naturales pequeños.
2. [ ] El LLM propone la interpretación de cada símbolo.
3. [ ] Z3 comprueba decrecimiento estricto de cada regla sobre ℕ y monotonía,
       buscando un contraejemplo (si no lo hay, vale).
4. [ ] Si falla, se devuelve al LLM el contraejemplo concreto
       («con x=0, y=2 la regla 3 no decrece»).

**Hito:** comparar LPO frente a polinomios y ver si el feedback con contraejemplos
mejora el acierto. Es la parte más nueva: no consta publicada para reescritura.

## Fase 3 — Contra una herramienta real (un fin de semana)

- [ ] Ejecutar NaTT o TTT2 sobre los mismos problemas.
- [ ] Anotar casos curiosos: el LLM encuentra una prueba más simple, o la herramienta
      tarda y el LLM no.

**Punto de decisión:** si no aparece nada interesante, se cierra aquí. Si aparece,
seguir.

## Fase 4 — Opcional: AC-RPO (largo)

- [ ] Implementar AC-RPO (aplanamiento y comparación de multiconjuntos).
- [ ] Repetir la fase 1 con los problemas AC de la TPDB.

## Detalles prácticos

- **Registro:** cada experimento en `experimentos/` (qué se preguntó, qué devolvió,
  si pasó la comprobación).
- **Coste:** con problemas pequeños, unos pocos euros de API.
- **Riesgo principal:** el tiempo que le quite al libro. Las fases cortas con hitos
  permiten parar en cualquiera.

## Referencias

- Medley y Manolios, *Feedback & Synthesis in LLM-Assisted Termination Proofs*, ITP 2026.
  https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ITP.2026.22
- Sultan et al., *LLMs versus the Halting Problem*, 2026. https://arxiv.org/abs/2601.18987
- Kamath et al., *Leveraging LLMs for Program Verification* (LOOPY), FMCAD 2024.
- Bártek y Suda, *Neural Precedence Recommender*, CADE-28, 2021.
  https://link.springer.com/chapter/10.1007/978-3-030-79876-5_30
- IsaFoR/CeTA: https://isafor-ceta.uibk.ac.at/
- Rubio, *A fully syntactic AC-RPO*, Information and Computation 178, 2002.
