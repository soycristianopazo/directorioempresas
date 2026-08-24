# 03 · Matching Engine y Supplier Score

> Documento H del diseño técnico. Cubre §20, §54, §55, §85 y §31 del brief.

---

## H.1 Principio rector

> **Elegibilidad y puntaje son dos cosas distintas y se calculan en ese orden.**

Un proveedor con score 95 que incumple un MUST HAVE **no aparece como recomendado**. Aparece, si acaso, en una sección aparte ("cumple casi todo, le falta ISO 45001") — nunca mezclado con los elegibles. Confundir ambos conceptos es el error que hace que abastecimiento deje de confiar en la herramienta a la tercera RFQ.

El motor es **determinístico y auditable**. Misma entrada + misma versión del motor + mismos pesos = mismo resultado, siempre. Cada corrida guarda `engine_version` y `weights_snapshot`, de modo que un resultado de hace ocho meses se puede reproducir y explicar ante una auditoría.

La IA (V2) **no reemplaza** este motor: lo alimenta (estructurando texto libre en criterios) y lo complementa (re-ranking semántico dentro del conjunto ya elegible). Nunca decide elegibilidad.

---

## H.2 Arquitectura en cuatro etapas

```
sourcing_event_id
        │
        ▼
┌───────────────────────────────────────────────────────────────────┐
│ ETAPA 1 · RECALL — universo de candidatos                         │
│ Filtro barato sobre supplier_search_index (read model).            │
│ Objetivo: pasar de 40.000 offerings a ~500 en <150 ms.            │
│                                                                    │
│  · taxonomy_node_ids && descendientes(nodo_solicitado)            │
│  · admin_division_ids && (territorio ∪ ancestros ∪ movilizables)  │
│  · offering.status = PUBLISHED AND organization.deleted_at IS NULL │
│  · organización no BLOCKED en buyer_supplier_relationships         │
│  · organización ≠ comprador                                       │
└───────────────────────────────────────────────────────────────────┘
        ▼  ~500 candidatos
┌───────────────────────────────────────────────────────────────────┐
│ ETAPA 2 · ELEGIBILIDAD — knock-out por MUST HAVE                  │
│ Evalúa cada sourcing_event_criteria con requirement_level='MUST'. │
│ Resultado binario + acumulación de blocking_reasons[].            │
│ NO descarta filas: marca is_eligible=false y guarda el porqué.    │
│ (El comprador quiere ver los "casi": es información de mercado.)  │
└───────────────────────────────────────────────────────────────────┘
        ▼  ~120 elegibles + ~380 no elegibles con motivo
┌───────────────────────────────────────────────────────────────────┐
│ ETAPA 3 · SCORING — 8 componentes ponderados, 0..100              │
│ Cada componente devuelve 0..1 y su propia explicación.            │
└───────────────────────────────────────────────────────────────────┘
        ▼
┌───────────────────────────────────────────────────────────────────┐
│ ETAPA 4 · RANKING Y EXPLICACIÓN                                   │
│ · Agrega por organización (mejor offering + bonus por cobertura)  │
│ · Aplica modificadores (diversidad, anti-concentración)           │
│ · Genera score_breakdown legible por humanos                      │
│ · Persiste en match_runs / match_results                          │
└───────────────────────────────────────────────────────────────────┘
```

---

## H.3 Etapa 2 — Elegibilidad (MUST HAVE)

Un criterio bloqueante puede ser de siete tipos. Todos se evalúan con la misma firma: `(criterio, candidato) → {cumple: bool, motivo: text}`.

| `criterion_type` | Evaluación | Ejemplo de `blocking_reason` |
|---|---|---|
| `ACCREDITATION` | Existe `accreditation_enrollments` con `status='ACCREDITED'`, `valid_until >= hoy` y `program_id` = el exigido | `No acreditado en "Programa Base Minería" (estado: EN_REVISION)` |
| `CERTIFICATION` | Existe `organization_certifications` vigente del tipo exigido | `Falta ISO 45001 vigente` |
| `TERRITORY` | `offering_territories` cubre la división o un ancestro, o es movilizable dentro del plazo | `No cubre Comuna de Sierra Gorda` |
| `ATTRIBUTE` | Operador tipado sobre `offering_attribute_values` | `vehicle_year requiere >=2024, declarado 2022` |
| `INDUSTRY_EXPERIENCE` | `organization_industries.years_experience >= N` en la industria exigida | `Sin experiencia declarada en Minería` |
| `EXPERIENCE_YEARS` | Antigüedad de la empresa o del offering | `Requiere 5 años, tiene 2` |
| `CAPACITY` | `monthly_capacity >= cantidad` del requerimiento | `Capacidad 80 pax/mes < 150 requeridos` |

**Reglas de decisión:**

- Todo MUST incumplido ⇒ `is_eligible = false`. No hay compensación por score alto.
- Criterio con `is_blocking = false` pero nivel MUST ⇒ advertencia, no bloqueo (permite MUST "blandos" bajo criterio del comprador).
- **Ausencia de dato ≠ incumplimiento.** Si el proveedor no declaró `vehicle_year`, no se asume que incumple: se marca `UNKNOWN`, se penaliza en el score (factor 0.3 en vez de 0) y se le notifica al proveedor *"completar este dato te habría hecho elegible para 3 oportunidades"*. Este bucle es el mecanismo que enriquece la base de datos con el tiempo.

---

## H.4 Etapa 3 — Fórmula de scoring

### Fórmula general

```
total_score = 100 × ( Σ (wᵢ × sᵢ) / Σ wᵢ ) × Π (modificadores)

donde sᵢ ∈ [0,1] y Σ wᵢ se recalcula excluyendo componentes no aplicables
(si el evento no define criterios de atributo, ese peso se redistribuye).
```

### Componentes y pesos por defecto

| # | Componente | Peso | Qué mide |
|---|---|---|---|
| 1 | `category_fit` | **20** | Precisión de la clasificación respecto al nodo solicitado |
| 2 | `attribute_fit` | **20** | Cumplimiento de los NICE TO HAVE de atributos |
| 3 | `territory_fit` | **15** | Cercanía y tipo de cobertura |
| 4 | `experience_fit` | **12** | Experiencia en industria + casos de éxito clasificados |
| 5 | `accreditation_fit` | **10** | Nivel y vigencia de la acreditación |
| 6 | `performance_fit` | **10** | Evaluaciones de desempeño reales |
| 7 | `responsiveness_fit` | **8** | Histórico de respuesta a invitaciones |
| 8 | `capacity_fit` | **5** | Holgura de capacidad frente a la demanda |

Los pesos son **configurables por evento** (`event_matching_weights`) y por defecto pueden diferir por categoría: en servicios de alto riesgo, `accreditation_fit` sube a 20 y `attribute_fit` baja. Los pesos vigentes se congelan en `match_runs.weights_snapshot`.

### Sub-fórmulas

**1. `category_fit`** — usa la distancia en el árbol `ltree`:
```
nodo solicitado == nodo del offering                → 1.00
offering es descendiente del solicitado             → 0.90
offering es ancestro directo (más genérico)         → 0.70
comparten ancestro a 1 nivel (hermano)              → 0.50
comparten ancestro a 2 niveles                      → 0.30
sin ancestro común relevante                        → 0.00 (no debería llegar aquí)
+ 0.05 si el nodo es el is_primary del offering
```

**2. `attribute_fit`** — proporción ponderada de NICE cumplidos:
```
attribute_fit = Σ (peso_criterio × factor) / Σ peso_criterio

factor = 1.0   cumple el operador
         0.6   cumple parcialmente (numérico dentro del ±10% del umbral)
         0.3   dato no declarado (UNKNOWN)
         0.0   no cumple
```

**3. `territory_fit`**:
```
base operacional en la misma comuna                          → 1.00
base operacional en la misma provincia                       → 0.90
base operacional en la misma región                          → 0.80
cobertura operacional declarada sobre la comuna              → 0.75
cobertura comercial sobre la región                          → 0.55
movilizable, mobilization_days <= plazo requerido            → 0.40
movilizable, mobilization_days > plazo requerido             → 0.15
```
(V2 con PostGIS: reemplazar los tres primeros por decaimiento continuo sobre distancia real.)

**4. `experience_fit`**:
```
experience_fit = 0.45 × f_industria + 0.35 × f_casos + 0.20 × f_clientes

f_industria = min(years_experience / 10, 1)          en la industria del evento
f_casos     = min(nº case_studies clasificados en el nodo o descendientes / 5, 1)
              × 1.15 si al menos uno está verificado (cap a 1.0)
f_clientes  = min(nº client_references verificadas en la industria / 3, 1)
```

**5. `accreditation_fit`**:
```
acreditado en el programa exigido, vigente > 90 días          → 1.00
acreditado, vigente pero vence en < 90 días                   → 0.85
acreditado en un programa de nivel superior o equivalente     → 0.90
acreditado ante ESTE comprador (AVL = APPROVED)               → 1.00
en revisión                                                    → 0.40
completitud >= 70% sin resolución                             → 0.25
sin proceso iniciado                                          → 0.00
```

**6. `performance_fit`** — solo con evidencia real:
```
n = nº de supplier_performance_reviews con contrato/award asociado

n = 0  → 0.55  (neutral: no penalizar al proveedor nuevo, no premiarlo tampoco)
n ≥ 1  → (promedio_ponderado_dimensiones / 5) × confianza
         confianza = min(n / 5, 1) ; para n<5 se interpola hacia 0.55
         penalización: −0.10 por cada incidente severity=HIGH en 12 meses
```
El "arranque neutral" es deliberado: si los proveedores nuevos arrancan en 0, el marketplace se cierra a los incumbentes y nunca entra oferta nueva.

**7. `responsiveness_fit`**:
```
responsiveness_fit = 0.6 × tasa_respuesta + 0.4 × velocidad

tasa_respuesta = respondidas / invitadas   (últimos 12 meses, mín. 3 invitaciones)
velocidad      = 1.0 si mediana de primera respuesta < 24 h
                 0.7 si < 72 h
                 0.4 si < 7 días
                 0.1 si mayor
sin historial → 0.55 (neutral)
```

**8. `capacity_fit`**:
```
ratio = monthly_capacity / cantidad_requerida
ratio >= 2.0  → 1.00
1.0 ≤ ratio < 2.0 → 0.70 + 0.30 × (ratio − 1)
0.7 ≤ ratio < 1.0 → 0.40    (podría cubrir parcialmente)
ratio < 0.7       → 0.15
dato no declarado → 0.50
```

### Modificadores multiplicativos

| Modificador | Factor | Motivo |
|---|---|---|
| Perfil incompleto (`profile_completion < 60%`) | × 0.90 | Datos insuficientes para confiar en el match |
| Documentación vencida | × 0.85 | Señal de riesgo operacional |
| Proveedor ya adjudicado por este comprador en la categoría | × 1.05 | Relación existente, menor fricción |
| Empresa local a la faena (`has_local_base` en la comuna) | × 1.05 | Alineado con políticas de desarrollo local (§34) |
| Suspendido en el AVL del comprador | × 0.50 | Se muestra, pero al fondo |
| Sin actividad en la plataforma > 180 días | × 0.85 | Probablemente no responderá |

**Ningún modificador depende del plan pagado.** El plan afecta cuántas oportunidades puede *ver* el proveedor y qué analítica recibe — jamás su posición en el ranking orgánico (§58). Las posiciones patrocinadas viven en `sponsored_placements`, se renderizan en un bloque visualmente separado y etiquetado "Patrocinado", y nunca se mezclan con `match_results`.

---

## H.5 Agregación por organización

El scoring es por *offering*, pero el comprador invita *empresas*:

```
score_organización = max(score_offerings) + bonus_cobertura

bonus_cobertura = min(nº offerings elegibles del evento − 1, 3) × 2 puntos
                  (cap: total_score ≤ 100)
```
Una empresa que puede cubrir 4 de las 5 líneas del evento vale más que una que cubre 1, aun si el mejor offering puntúa igual. `match_results` guarda la fila por offering y la vista `v_match_results_by_org` agrega.

---

## H.6 Explicabilidad — el entregable real

`match_results.score_breakdown` almacena un JSON legible que la UI renderiza directamente:

```json
{
  "engine_version": "1.0.0",
  "total_score": 96,
  "is_eligible": true,
  "components": [
    { "key": "category_fit",       "weight": 20, "score": 1.00, "points": 20.0,
      "label": "Categoría compatible",
      "detail": "Ofrece 'Transporte de trabajadores a faena' (coincidencia exacta)" },
    { "key": "territory_fit",      "weight": 15, "score": 1.00, "points": 15.0,
      "label": "Cobertura territorial",
      "detail": "Base operacional en Antofagasta" },
    { "key": "attribute_fit",      "weight": 20, "score": 0.92, "points": 18.4,
      "label": "Requisitos técnicos",
      "detail": "7 de 8 cumplidos. Pendiente: cinturón de 3 puntas no declarado" },
    { "key": "accreditation_fit",  "weight": 10, "score": 1.00, "points": 10.0,
      "label": "Acreditación vigente",
      "detail": "Programa Base Minería · vigente hasta 2027-03-15" },
    { "key": "experience_fit",     "weight": 12, "score": 0.88, "points": 10.6,
      "label": "Experiencia comprobada",
      "detail": "8 años en minería del cobre · 4 casos de éxito verificados" },
    { "key": "performance_fit",    "weight": 10, "score": 0.90, "points": 9.0,
      "label": "Desempeño histórico",
      "detail": "4.5/5 en 7 evaluaciones de contratos cerrados" },
    { "key": "responsiveness_fit", "weight":  8, "score": 0.95, "points": 7.6,
      "label": "Nivel de respuesta",
      "detail": "Responde en promedio en 6 horas · 92% de tasa de respuesta" },
    { "key": "capacity_fit",       "weight":  5, "score": 1.00, "points": 5.0,
      "label": "Capacidad disponible",
      "detail": "Flota de 42 buses · capacidad declarada 400 pax" }
  ],
  "modifiers": [
    { "key": "local_company", "factor": 1.05, "label": "Empresa local a la faena" }
  ],
  "blocking_reasons": []
}
```

Y para los no elegibles:

```json
{
  "total_score": 91,
  "is_eligible": false,
  "blocking_reasons": [
    "Falta certificación ISO 45001 vigente (MUST HAVE)",
    "Acreditación vencida el 2026-02-01 (MUST HAVE)"
  ],
  "hint_for_supplier": "Renovar acreditación te habría hecho elegible para esta y otras 4 oportunidades activas"
}
```

Ese `hint_for_supplier` es, simultáneamente, la funcionalidad de retención del §71 y el motor de enriquecimiento de la base de datos.

---

## H.7 Implementación

| Aspecto | Decisión |
|---|---|
| Dónde corre | **Función SQL en Postgres** (`fn_run_matching(event_id, weights jsonb)`), no en Node. Los datos ya están ahí; mover 40.000 filas al servidor de aplicación para puntuarlas es un error de diseño. |
| Cuándo corre | Al publicar el evento; bajo demanda ("recalcular"); y en el job nocturno para eventos abiertos (detecta proveedores nuevos que ahora califican). |
| Rendimiento objetivo | < 800 ms para 40.000 offerings. Etapa 1 sobre índices GIN, etapas 2-3 sobre el subconjunto reducido. |
| Versionado | `engine_version` semántico. Cambiar la fórmula **no** recalcula resultados históricos. |
| Pruebas | Suite de casos de oro: 25 escenarios con resultado esperado fijo. Cualquier cambio de fórmula debe justificar cada diferencia. |
| Preview | Modo `dry_run` para que el comprador ajuste pesos y vea el reordenamiento en vivo antes de invitar. |

---

## H.8 Supplier Score (§31) — distinto del match score

Son dos cosas y conviene no confundirlas:

- **Match score**: relativo a *un* evento. Cambia con cada RFQ.
- **Supplier Score**: absoluto, de la empresa, 0..100. Independiente de cualquier evento. Se recalcula a diario.

```
supplier_score = Σ (peso × componente_normalizado)
```

| Componente | Peso | Fuente | Normalización |
|---|---|---|---|
| Completitud de perfil | 12 | % de campos y bloques poblados | directo 0..1 |
| Acreditación | 18 | mejor enrollment vigente | ACCREDITED=1 · OBSERVED=0.4 · EN_REVISION=0.3 · ninguna=0 |
| Vigencia documental | 12 | docs vigentes / docs exigidos | directo; 0 si hay algún vencido crítico |
| Certificaciones | 8 | nº de certificaciones vigentes verificadas | min(n/3, 1) |
| Experiencia | 10 | años + casos de éxito verificados | min(años/10,1)×0.5 + min(casos/5,1)×0.5 |
| Desempeño | 20 | `supplier_performance_reviews` | promedio/5, con factor de confianza por n |
| Capacidad de respuesta | 10 | tasa y velocidad de respuesta | ver H.4.7 |
| Tasa de adjudicación | 5 | adjudicadas / cotizadas | min(tasa/0.3, 1) |
| Incidentes y reclamos | −10 | `supplier_incidents` abiertos | penalización, piso 0 |
| Verificaciones | 5 | `verification_checks` aprobadas | directo |

**Reglas de honestidad del score:**

1. Se publica la fórmula. Un score que el proveedor no entiende es un score en el que no confía y que no lo motiva a mejorar.
2. Se muestra siempre **desglosado** (`supplier_score_components`), con la acción sugerida para cada componente bajo.
3. No se muestra públicamente si `n_evaluaciones < 3` o `completitud < 50%`: se muestra "Score en construcción". Evita castigar al recién llegado con un número feo permanente.
4. Es histórico: `supplier_scores` guarda snapshots; el proveedor ve su evolución. Nunca se sobrescribe.
5. `formula_version` en cada snapshot. Al cambiar la fórmula se recalcula hacia adelante y se avisa al proveedor.
6. **No es comprable.** Ningún plan lo modifica.

---

## H.9 Camino hacia la IA (V2/V3), sin romper nada

| Etapa | Qué aporta la IA | Qué NO hace |
|---|---|---|
| V2.1 | **Structured intake**: convierte "necesito 20 camionetas 4x4 por 24 meses" en `taxonomy_node`, `industry`, cantidad, atributos y criterios MUST/NICE candidatos. El humano confirma antes de persistir. | No crea el evento sola |
| V2.2 | **Re-ranking semántico**: embeddings (`pgvector`) sobre descripciones de offerings y casos de éxito. Reordena **dentro** del conjunto elegible y aporta un 9º componente con peso ≤ 10. | No altera la elegibilidad |
| V2.3 | **Análisis de cotizaciones**: detecta diferencias de alcance, exclusiones asimétricas y outliers de precio entre ofertas. | No adjudica ni puntúa evaluación |
| V3 | **Supplier Intelligence**: resumen 360° en lenguaje natural con citas a filas concretas de la base. | No inventa datos: cada afirmación referencia su origen |

Regla permanente: **la fuente de verdad es el modelo relacional.** La IA lee de él, propone sobre él y siempre deja rastro de qué propuso y quién lo aceptó (`ai_suggestions` con `accepted_by` / `rejected_reason`).
