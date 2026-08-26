"""Motor de matching — acceso a datos (fase 6.4-6.7).

Etapas 1 y 2 (Recall, Elegibilidad) son SQL: trabajo de conjuntos sobre
hasta ~500 candidatos, exactamente lo que Postgres resuelve mejor que un
bucle en Python fila a fila — ver la decisión de diseño en el plan de fase
6. `evaluate_eligibility_for_criterion()` corre UNA vez por criterio
MUST_HAVE del evento (no por candidato): son pocos por evento, cada consulta
es un lookup indexado sobre el conjunto ya reducido, y el resultado se
combina en Python — más simple y más correcto que una única consulta
genérica con LATERAL por los 7 tipos de criterio a la vez.

`category_fit`/`territory_fit` son el primer uso de operadores `ltree` en
una consulta de este proyecto (no en objetos Python — la app nunca
parsea/compara `path` en Python, ver `models/taxonomy.py`). `app_user` no
tiene `extensions` en su search_path (mismo motivo documentado en
`0012_admin_divisions.sql` para los casts `::ltree` sin calificar dentro de
triggers) — a diferencia de un cast, un OPERADOR (`<@`/`@>`) o función
(`nlevel`/`subpath`) sin calificar falla con "operator/function does not
exist", no con un mensaje que apunte a la causa real. `_set_ltree_search_path()`
lo resuelve una vez por función, en vez de calificar cada operador
individualmente con la sintaxis `operator(extensions.<@)`.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.matching import MatchResult, MatchRun

_SET_LTREE_SEARCH_PATH = text('set local search_path = "$user", public, extensions')


async def _set_ltree_search_path(session: AsyncSession) -> None:
    await session.execute(_SET_LTREE_SEARCH_PATH)


# ─── Etapa 1 · Recall ─────────────────────────────────────────────────────────

_RECALL_SQL = text(
    """
    select
      si.offering_id, si.organization_id, si.taxonomy_node_ids,
      si.admin_division_ids, si.availability_status, si.completion_pct
    from public.supplier_search_index si
    where si.is_matchable
      and si.organization_id <> :buyer_organization_id
      and (
        cast(:taxonomy_node_id as uuid) is null
        or exists (
          select 1
          from public.taxonomy_nodes requested
          join public.taxonomy_nodes candidate_node
            on candidate_node.id = any (si.taxonomy_node_ids)
          where requested.id = cast(:taxonomy_node_id as uuid)
            and candidate_node.path <@ requested.path
        )
      )
      and (
        cast(:admin_division_ids as uuid[]) is null
        or si.admin_division_ids && cast(:admin_division_ids as uuid[])
      )
      -- BLOCKED en el AVL de ESTE comprador (fase 8.8) es un filtro duro de
      -- elegibilidad, no una señal de puntaje — mismo criterio que ya usa
      -- docs/03-MATCHING-ENGINE.md para un MUST_HAVE bloqueante: si el
      -- comprador bloqueó a este proveedor, ni siquiera debe aparecer como
      -- candidato, no solo puntuar bajo.
      and not exists (
        select 1
        from public.buyer_supplier_relationships bsr
        where bsr.buyer_organization_id = :buyer_organization_id
          and bsr.supplier_organization_id = si.organization_id
          and bsr.status = 'BLOCKED'
      )
    """
)


async def recall_candidates(
    session: AsyncSession,
    *,
    buyer_organization_id: UUID,
    taxonomy_node_id: UUID | None,
    admin_division_ids: list[UUID] | None,
) -> list[dict]:
    await _set_ltree_search_path(session)
    result = await session.execute(
        _RECALL_SQL,
        {
            "buyer_organization_id": str(buyer_organization_id),
            "taxonomy_node_id": str(taxonomy_node_id) if taxonomy_node_id else None,
            "admin_division_ids": (
                [str(i) for i in admin_division_ids] if admin_division_ids else None
            ),
        },
    )
    return [dict(row._mapping) for row in result]


_CATEGORY_FIT_SQL = text(
    """
    select
      cand.id as candidate_node_id,
      case
        when cand.id = requested.id then 1.00
        when cand.path <@ requested.path then 0.90
        when requested.path <@ cand.path and nlevel(requested.path) - nlevel(cand.path) = 1 then 0.70
        when requested.path <@ cand.path then 0.70
        when nlevel(requested.path) > 1 and nlevel(cand.path) > 1
             and subpath(requested.path, 0, nlevel(requested.path) - 1)
                 = subpath(cand.path, 0, nlevel(cand.path) - 1)
          then 0.50
        when nlevel(requested.path) > 2 and nlevel(cand.path) > 2
             and subpath(requested.path, 0, nlevel(requested.path) - 2)
                 = subpath(cand.path, 0, nlevel(cand.path) - 2)
          then 0.30
        else 0.00
      end as score
    from public.taxonomy_nodes requested
    cross join public.taxonomy_nodes cand
    where requested.id = cast(:requested_node_id as uuid)
      and cand.id = any (cast(:candidate_node_ids as uuid[]))
    """
)


async def category_fit_scores(
    session: AsyncSession, *, requested_node_id: UUID, candidate_node_ids: list[UUID]
) -> dict[str, float]:
    """nodo_id (de cualquiera de los nodos ligados a un offering) → score de
    distancia en el árbol (§H.4.1). El llamador toma el máximo entre los
    nodos de cada offering."""
    if not candidate_node_ids:
        return {}
    await _set_ltree_search_path(session)
    result = await session.execute(
        _CATEGORY_FIT_SQL,
        {
            "requested_node_id": str(requested_node_id),
            "candidate_node_ids": [str(i) for i in candidate_node_ids],
        },
    )
    return {str(row.candidate_node_id): float(row.score) for row in result}


# ─── Etapa 2 · Elegibilidad ────────────────────────────────────────────────────

_ELIGIBLE_BY_CRITERION_SQL = {
    "ACCREDITATION": text(
        """
        select so.id as offering_id
        from public.supplier_offerings so
        join public.accreditation_enrollments ae
          on ae.organization_id = so.organization_id
         and (
           ae.program_id = cast(:program_id as uuid)
           or ae.program_id in (
             select accepted_program_id from public.accreditation_program_equivalences
             where program_id = cast(:program_id as uuid)
           )
         )
        where so.id = any (cast(:candidate_offering_ids as uuid[]))
          and ae.status = 'ACCREDITED'
          and (ae.valid_until is null or ae.valid_until >= current_date)
        """
    ),
    "CERTIFICATION": text(
        """
        select so.id as offering_id
        from public.supplier_offerings so
        join public.organization_certifications oc
          on oc.organization_id = so.organization_id
         and oc.certification_type_id = cast(:certification_type_id as uuid)
        where so.id = any (cast(:candidate_offering_ids as uuid[]))
          and (oc.valid_until is null or oc.valid_until >= current_date)
        """
    ),
    "TERRITORY": text(
        """
        select distinct so.id as offering_id
        from public.supplier_offerings so
        join public.offering_territories ot on ot.offering_id = so.id
        where so.id = any (cast(:candidate_offering_ids as uuid[]))
          and (
            ot.admin_division_id = cast(:admin_division_id as uuid)
            or (
              ot.coverage_type = 'MOBILIZABLE'
              and (
                cast(:max_mobilization_days as int) is null
                or ot.mobilization_days is null
                or ot.mobilization_days <= cast(:max_mobilization_days as int)
              )
            )
          )
        """
    ),
    "EXPERIENCE_YEARS": text(
        """
        select so.id as offering_id
        from public.supplier_offerings so
        join public.organizations o on o.id = so.organization_id
        where so.id = any (cast(:candidate_offering_ids as uuid[]))
          and o.founded_year is not null
          and (extract(year from current_date) - o.founded_year) >= cast(:min_years as int)
        """
    ),
    "INDUSTRY_EXPERIENCE": text(
        """
        select so.id as offering_id
        from public.supplier_offerings so
        join public.organization_industries oi on oi.organization_id = so.organization_id
        where so.id = any (cast(:candidate_offering_ids as uuid[]))
          and oi.industry_id = cast(:industry_id as uuid)
          and coalesce(oi.years_experience, 0) >= cast(:min_years as int)
        """
    ),
    "CAPACITY": text(
        """
        select so.id as offering_id
        from public.supplier_offerings so
        where so.id = any (cast(:candidate_offering_ids as uuid[]))
          and so.monthly_capacity is not null
          and so.monthly_capacity >= cast(:min_capacity as numeric)
        """
    ),
}


async def eligible_offering_ids_for_criterion(
    session: AsyncSession, *, criterion: dict, candidate_offering_ids: list[UUID]
) -> set[str]:
    """Offering ids del conjunto candidato que CUMPLEN este criterio. CUSTOM
    nunca bloquea (no se llama para ese tipo); ATTRIBUTE se resuelve aparte
    (evaluate_attribute_criterion, evaluador tipado D.4)."""
    query = _ELIGIBLE_BY_CRITERION_SQL.get(criterion["criterion_type"])
    if query is None or not candidate_offering_ids:
        return set()
    params = {
        "candidate_offering_ids": [str(i) for i in candidate_offering_ids],
        "program_id": (
            str(criterion["accreditation_program_id"])
            if criterion.get("accreditation_program_id")
            else None
        ),
        "certification_type_id": (
            str(criterion["certification_type_id"])
            if criterion.get("certification_type_id")
            else None
        ),
        "admin_division_id": (
            str(criterion["admin_division_id"])
            if criterion.get("admin_division_id")
            else None
        ),
        "max_mobilization_days": criterion.get("max_mobilization_days"),
        "min_years": criterion.get("min_years"),
        "industry_id": (
            str(criterion["industry_id"]) if criterion.get("industry_id") else None
        ),
        "min_capacity": criterion.get("min_capacity"),
    }
    result = await session.execute(query, params)
    return {str(row.offering_id) for row in result}


_NUMBER_OPERATORS = {
    "EQ": "v.value_number = cast(:value_number as numeric)",
    "NEQ": "v.value_number <> cast(:value_number as numeric)",
    "GT": "v.value_number > cast(:value_number as numeric)",
    "GTE": "v.value_number >= cast(:value_number as numeric)",
    "LT": "v.value_number < cast(:value_number as numeric)",
    "LTE": "v.value_number <= cast(:value_number as numeric)",
    "BETWEEN": "v.value_number between cast(:value_number as numeric) and cast(:value_number_max as numeric)",
}
_DATE_OPERATORS = {
    "EQ": "v.value_date = cast(:value_date as date)",
    "NEQ": "v.value_date <> cast(:value_date as date)",
    "GT": "v.value_date > cast(:value_date as date)",
    "GTE": "v.value_date >= cast(:value_date as date)",
    "LT": "v.value_date < cast(:value_date as date)",
    "LTE": "v.value_date <= cast(:value_date as date)",
    "BETWEEN": "v.value_date between cast(:value_date as date) and cast(:value_date_max as date)",
}
_TEXT_OPERATORS = {
    "EQ": "extensions.unaccent(v.value_text) ilike extensions.unaccent(cast(:value_text as text))",
    "NEQ": "extensions.unaccent(v.value_text) not ilike extensions.unaccent(cast(:value_text as text))",
    "CONTAINS": "extensions.unaccent(v.value_text) ilike '%' || extensions.unaccent(cast(:value_text as text)) || '%'",
}
_BOOLEAN_OPERATORS = {"EQ": "v.value_boolean = cast(:value_boolean as boolean)"}
_SELECT_OPERATORS = {
    "EQ": "opt.value = cast(:value_options as text[]) [1]",
    "NEQ": "opt.value <> cast(:value_options as text[]) [1]",
    "IN": "opt.value = any (cast(:value_options as text[]))",
    "NOT_IN": "opt.value <> all (cast(:value_options as text[]))",
}


async def evaluate_attribute_criterion(
    session: AsyncSession, *, criterion: dict, candidate_offering_ids: list[UUID]
) -> set[str]:
    """Evaluador de operadores tipados (docs/02-MODELO-DATOS.md §D.4) —
    NUMBER/DATE/TEXT/BOOLEAN/SELECT resueltos vía SQL (Postgres compara
    tipos nativos mejor que Python). MULTISELECT/RANGE se resuelven aparte
    por su forma de almacenamiento distinta (ver evaluate_multiselect_criterion)."""
    if not candidate_offering_ids:
        return set()

    data_type_result = await session.execute(
        text("select data_type from public.attribute_definitions where id = :id"),
        {"id": str(criterion["attribute_definition_id"])},
    )
    data_type = data_type_result.scalar_one_or_none()
    if data_type is None:
        return set()

    if data_type == "MULTISELECT":
        return await evaluate_multiselect_criterion(
            session, criterion=criterion, candidate_offering_ids=candidate_offering_ids
        )

    operator_map = {
        "NUMBER": _NUMBER_OPERATORS,
        "DATE": _DATE_OPERATORS,
        "TEXT": _TEXT_OPERATORS,
        "BOOLEAN": _BOOLEAN_OPERATORS,
        "SELECT": _SELECT_OPERATORS,
    }.get(data_type)
    if operator_map is None:
        return set()
    condition = operator_map.get(criterion["operator"])
    if condition is None:
        return set()

    join_option = (
        "left join public.attribute_options opt on opt.id = v.option_id"
        if data_type == "SELECT"
        else ""
    )
    query = text(
        f"""
        select v.offering_id
        from public.offering_attribute_values v
        {join_option}
        where v.offering_id = any (cast(:candidate_offering_ids as uuid[]))
          and v.attribute_definition_id = cast(:attribute_definition_id as uuid)
          and ({condition})
        """
    )
    result = await session.execute(
        query,
        {
            "candidate_offering_ids": [str(i) for i in candidate_offering_ids],
            "attribute_definition_id": str(criterion["attribute_definition_id"]),
            "value_text": criterion.get("value_text"),
            "value_number": criterion.get("value_number"),
            "value_number_max": criterion.get("value_number_max"),
            "value_boolean": criterion.get("value_boolean"),
            "value_date": criterion.get("value_date"),
            "value_date_max": criterion.get("value_date_max"),
            "value_options": criterion.get("value_options"),
        },
    )
    return {str(row.offering_id) for row in result}


async def evaluate_multiselect_criterion(
    session: AsyncSession, *, criterion: dict, candidate_offering_ids: list[UUID]
) -> set[str]:
    operator = criterion["operator"]
    condition = {
        "IN": "arr.selected && cast(:value_options as text[])",
        "NOT_IN": "not (arr.selected && cast(:value_options as text[]))",
        "CONTAINS": "arr.selected && cast(:value_options as text[])",
        "CONTAINS_ALL": "arr.selected @> cast(:value_options as text[])",
    }.get(operator)
    if condition is None:
        return set()
    query = text(
        f"""
        select v.offering_id
        from public.offering_attribute_values v
        join lateral (
          select array_agg(ao.value) as selected
          from public.offering_attribute_option_values oaov
          join public.attribute_options ao on ao.id = oaov.option_id
          where oaov.offering_attribute_value_id = v.id
        ) arr on true
        where v.offering_id = any (cast(:candidate_offering_ids as uuid[]))
          and v.attribute_definition_id = cast(:attribute_definition_id as uuid)
          and ({condition})
        """
    )
    result = await session.execute(
        query,
        {
            "candidate_offering_ids": [str(i) for i in candidate_offering_ids],
            "attribute_definition_id": str(criterion["attribute_definition_id"]),
            "value_options": criterion.get("value_options"),
        },
    )
    return {str(row.offering_id) for row in result}


async def has_declared_attribute(
    session: AsyncSession,
    *,
    attribute_definition_id: UUID,
    candidate_offering_ids: list[UUID],
) -> set[str]:
    """Para distinguir "no cumple" de "no declaró" (§H.3: ausencia de dato
    ≠ incumplimiento) — el llamador usa esto para no bloquear por un MUST
    que el proveedor simplemente no completó."""
    if not candidate_offering_ids:
        return set()
    result = await session.execute(
        text(
            "select offering_id from public.offering_attribute_values "
            "where offering_id = any (cast(:ids as uuid[])) "
            "and attribute_definition_id = cast(:attr_id as uuid)"
        ),
        {
            "ids": [str(i) for i in candidate_offering_ids],
            "attr_id": str(attribute_definition_id),
        },
    )
    return {str(row.offering_id) for row in result}


_TERRITORY_FIT_SQL = text(
    """
    with requested as (
      select id, path from public.admin_divisions where id = any (cast(:admin_division_ids as uuid[]))
    )
    select
      so.id as offering_id,
      max(case
        when loc.admin_division_id is not null and loc_div.id = r.id then 1.00
        when loc.admin_division_id is not null and nlevel(loc_div.path) >= 2
             and subpath(loc_div.path, 0, nlevel(loc_div.path) - 1)
                 = subpath(r.path, 0, greatest(nlevel(r.path) - 1, 0))
             and nlevel(loc_div.path) = nlevel(r.path) then 0.90
        when loc.admin_division_id is not null and loc_div.path @> r.path
             and loc_div.id <> r.id then 0.80
        when ot.coverage_type = 'OPERATIONAL' and ot_div.id = r.id then 0.75
        when ot.coverage_type = 'COMMERCIAL' and ot_div.path @> r.path and ot_div.id <> r.id then 0.55
        when ot.coverage_type = 'MOBILIZABLE'
             and (cast(:max_mobilization_days as int) is null or ot.mobilization_days is null
                  or ot.mobilization_days <= cast(:max_mobilization_days as int))
          then 0.40
        when ot.coverage_type = 'MOBILIZABLE' then 0.15
        else 0.00
      end) as score
    from public.supplier_offerings so
    cross join requested r
    left join public.organization_locations loc
      on loc.organization_id = so.organization_id and loc.is_headquarters
    left join public.admin_divisions loc_div on loc_div.id = loc.admin_division_id
    left join public.offering_territories ot on ot.offering_id = so.id
    left join public.admin_divisions ot_div on ot_div.id = ot.admin_division_id
    where so.id = any (cast(:candidate_offering_ids as uuid[]))
    group by so.id
    """
)


async def territory_fit_scores(
    session: AsyncSession,
    *,
    admin_division_ids: list[UUID],
    candidate_offering_ids: list[UUID],
    max_mobilization_days: int | None,
) -> dict[str, float]:
    if not admin_division_ids or not candidate_offering_ids:
        return {}
    await _set_ltree_search_path(session)
    result = await session.execute(
        _TERRITORY_FIT_SQL,
        {
            "admin_division_ids": [str(i) for i in admin_division_ids],
            "candidate_offering_ids": [str(i) for i in candidate_offering_ids],
            "max_mobilization_days": max_mobilization_days,
        },
    )
    return {str(row.offering_id): float(row.score or 0.0) for row in result}


# ─── Etapa 3 · Insumos de scoring (una consulta agrupada, no por candidato) ───

_SCORING_INPUTS_SQL = text(
    """
    select
      so.id as offering_id,
      so.organization_id,
      so.monthly_capacity,
      o.completion_pct,
      o.founded_year,
      coalesce(cases.n, 0) as case_study_count,
      coalesce(cases.verified_n, 0) as verified_case_study_count,
      coalesce(refs.n, 0) as client_reference_count,
      exp.years_experience,
      coalesce(local.has_local_base, false) as has_local_base,
      coalesce(expired.n, 0) > 0 as has_expired_documents
    from public.supplier_offerings so
    join public.organizations o on o.id = so.organization_id
    left join lateral (
      select bool_or(ot.has_local_base) as has_local_base
      from public.offering_territories ot
      where ot.offering_id = so.id
        and (
          cast(:admin_division_ids as uuid[]) is null
          or ot.admin_division_id = any (cast(:admin_division_ids as uuid[]))
        )
    ) local on true
    left join lateral (
      select count(*) as n
      from public.organization_document_versions v
      join public.organization_documents d on d.id = v.document_id
      where d.organization_id = so.organization_id
        and v.status = 'ACTIVE'
        and v.valid_until is not null
        and v.valid_until < current_date
    ) expired on true
    left join lateral (
      -- "clasificados en el nodo o descendientes" (§H.4.4) — mismo criterio
      -- ltree que category_fit, confinado a esta consulta.
      select
        count(distinct cs.id) as n,
        count(distinct cs.id) filter (where cs.verification_status = 'VERIFIED') as verified_n
      from public.case_studies cs
      join public.case_study_taxonomy_nodes cstn on cstn.case_study_id = cs.id
      join public.taxonomy_nodes classified on classified.id = cstn.node_id
      join public.taxonomy_nodes requested on requested.id = cast(:taxonomy_node_id as uuid)
      where cs.organization_id = so.organization_id
        and (cast(:taxonomy_node_id as uuid) is null or classified.path <@ requested.path)
    ) cases on true
    left join lateral (
      select count(*) as n
      from public.client_references cr
      where cr.organization_id = so.organization_id
        and cr.is_verified
        and (cast(:industry_id as uuid) is null or cr.industry_id = cast(:industry_id as uuid))
    ) refs on true
    left join lateral (
      select oi.years_experience
      from public.organization_industries oi
      where oi.organization_id = so.organization_id
        and (cast(:industry_id as uuid) is null or oi.industry_id = cast(:industry_id as uuid))
      order by oi.years_experience desc nulls last
      limit 1
    ) exp on true
    where so.id = any (cast(:offering_ids as uuid[]))
    """
)


async def fetch_scoring_inputs(
    session: AsyncSession,
    *,
    offering_ids: list[UUID],
    industry_id: UUID | None,
    taxonomy_node_id: UUID | None,
    admin_division_ids: list[UUID] | None = None,
) -> dict[str, dict]:
    if not offering_ids:
        return {}
    await _set_ltree_search_path(session)
    result = await session.execute(
        _SCORING_INPUTS_SQL,
        {
            "offering_ids": [str(i) for i in offering_ids],
            "industry_id": str(industry_id) if industry_id else None,
            "taxonomy_node_id": str(taxonomy_node_id) if taxonomy_node_id else None,
            "admin_division_ids": (
                [str(i) for i in admin_division_ids] if admin_division_ids else None
            ),
        },
    )
    return {str(row.offering_id): dict(row._mapping) for row in result}


async def fetch_accreditation_status(
    session: AsyncSession, *, organization_ids: list[UUID], program_id: UUID | None
) -> dict[str, dict]:
    if not organization_ids or program_id is None:
        return {}
    result = await session.execute(
        text(
            "select organization_id, status, completion_pct, valid_until "
            "from public.accreditation_enrollments "
            "where organization_id = any (cast(:org_ids as uuid[])) and program_id = cast(:program_id as uuid)"
        ),
        {"org_ids": [str(i) for i in organization_ids], "program_id": str(program_id)},
    )
    return {str(row.organization_id): dict(row._mapping) for row in result}


async def fetch_equivalent_accreditation_status(
    session: AsyncSession, *, organization_ids: list[UUID], program_id: UUID | None
) -> dict[str, dict]:
    """organization_id → estado de acreditación ACCREDITED vigente en
    CUALQUIER programa que el dueño de program_id declaró equivalente
    (accreditation_program_equivalences, fase 9.1) — homologación cruzada:
    estar acreditado en un programa homologado también satisface program_id.
    Alimenta la rama accredited_via_equivalent de compute_accreditation_fit()
    en services/matching.py. Hermana de fetch_accreditation_status()."""
    if not organization_ids or program_id is None:
        return {}
    result = await session.execute(
        text(
            "select distinct on (ae.organization_id) "
            "  ae.organization_id, ae.status, ae.completion_pct, ae.valid_until "
            "from public.accreditation_enrollments ae "
            "where ae.organization_id = any (cast(:org_ids as uuid[])) "
            "and ae.program_id in ("
            "  select accepted_program_id from public.accreditation_program_equivalences "
            "  where program_id = cast(:program_id as uuid)"
            ") "
            "and ae.status = 'ACCREDITED' "
            "and (ae.valid_until is null or ae.valid_until >= current_date) "
            "order by ae.organization_id, ae.valid_until desc nulls last"
        ),
        {"org_ids": [str(i) for i in organization_ids], "program_id": str(program_id)},
    )
    return {str(row.organization_id): dict(row._mapping) for row in result}


async def fetch_avl_status(
    session: AsyncSession, *, buyer_organization_id: UUID, organization_ids: list[UUID]
) -> dict[str, str]:
    """supplier_organization_id → status del AVL de ESTE comprador (fase
    8.8) — usado por compute_accreditation_fit para dar prioridad a un
    APPROVED sobre la acreditación de programa (§H.4.5)."""
    if not organization_ids:
        return {}
    result = await session.execute(
        text(
            "select supplier_organization_id, status "
            "from public.buyer_supplier_relationships "
            "where buyer_organization_id = cast(:buyer_organization_id as uuid) "
            "and supplier_organization_id = any (cast(:org_ids as uuid[]))"
        ),
        {
            "buyer_organization_id": str(buyer_organization_id),
            "org_ids": [str(i) for i in organization_ids],
        },
    )
    return {str(row.supplier_organization_id): row.status for row in result}


# ─── Persistencia ──────────────────────────────────────────────────────────────


async def create_match_run(session: AsyncSession, **fields: object) -> MatchRun:
    run = MatchRun(**fields)
    session.add(run)
    await session.flush()
    return run


async def save_match_results(session: AsyncSession, results: list[dict]) -> None:
    session.add_all([MatchResult(**r) for r in results])
    await session.flush()


async def get_latest_run(session: AsyncSession, event_id: UUID) -> MatchRun | None:
    result = await session.execute(
        select(MatchRun)
        .where(MatchRun.sourcing_event_id == event_id)
        .order_by(MatchRun.executed_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def list_results(session: AsyncSession, match_run_id: UUID) -> list[dict]:
    result = await session.execute(
        text(
            "select id, organization_id, offering_id, total_score, is_eligible, "
            "blocking_reasons, score_breakdown, rank "
            "from public.match_results where match_run_id = :run_id "
            "order by is_eligible desc, rank nulls last, total_score desc"
        ),
        {"run_id": str(match_run_id)},
    )
    return [dict(row._mapping) for row in result]
