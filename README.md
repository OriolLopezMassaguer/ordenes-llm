# ordenes-llm

Experimentos con LLMs para encontrar órdenes de reducción (LPO, interpretaciones
polinómicas y, más adelante, AC-RPO) que prueben la terminación de sistemas de
reescritura. El LLM propone; un comprobador formal decide.

El plan de trabajo está en [PLAN.md](PLAN.md).

## Estructura prevista

- `src/` — parser de TRS, comprobadores (LPO, polinomios con Z3), bucle con el LLM
- `problemas/` — subconjunto de la TPDB con símbolos renombrados
- `experimentos/` — registro de cada experimento
