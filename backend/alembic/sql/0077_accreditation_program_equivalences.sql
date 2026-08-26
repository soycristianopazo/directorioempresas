-- ============================================================================
-- 0077 · Homologación cruzada de programas de acreditación (fase 9.1)
-- ----------------------------------------------------------------------------
-- "Estar ACCREDITED en accepted_program_id también satisface program_id, con
-- score 0.90 (nunca 1.00, reservado a la acreditación directa)" — la rama
-- documentada sin implementar en docs/03-MATCHING-ENGINE.md §H.4.5
-- ("acreditado en un programa de nivel superior o equivalente → 0.90").
--
-- Dirigida y unilateral a propósito: el dueño de program_id decide qué
-- acepta, sin necesitar consentimiento del otro programa; homologar en
-- ambos sentidos requiere dos filas. No es append-only (a diferencia de
-- accreditation_status_history/_review_events) — es una decisión de
-- configuración del dueño del programa, revocable, mismo criterio que
-- requirement_groups/accreditation_requirements. Sin updated_at: una
-- equivalencia se crea o se borra, nunca se edita.
-- ============================================================================

create table public.accreditation_program_equivalences (
  id                  uuid primary key default gen_random_uuid(),
  program_id          uuid not null references public.accreditation_programs (id) on delete cascade,
  accepted_program_id uuid not null references public.accreditation_programs (id) on delete cascade,
  created_at          timestamptz not null default now(),
  created_by          uuid references public.profiles (id) on delete set null,

  constraint accreditation_program_equivalences_unique unique (program_id, accepted_program_id),
  constraint accreditation_program_equivalences_distinct check (program_id <> accepted_program_id)
);

comment on table public.accreditation_program_equivalences is
  'Homologación cruzada (fase 9): estar ACCREDITED en accepted_program_id satisface también program_id, con score 0.90 — ver compute_accreditation_fit() en services/matching.py. Dirigida: homologar en ambos sentidos requiere dos filas.';

create index accreditation_program_equivalences_program_idx
  on public.accreditation_program_equivalences (program_id);
create index accreditation_program_equivalences_accepted_idx
  on public.accreditation_program_equivalences (accepted_program_id);
