-- ============================================================================
-- 0046 · Preguntas y respuestas del evento (fase 7.4)
-- ----------------------------------------------------------------------------
-- Fase 7.4 del roadmap. Ver docs/02-MODELO-DATOS.md §D8, docs/01-ARQUITECTURA.md §G.1.
--
-- Regla del propio diseño: "responder a todos NO revela quién preguntó" — al
-- publicar una respuesta con visibility=ALL_PARTICIPANTS, el autor de la
-- pregunta se anonimiza en la lectura (lo hace el service, no la fila:
-- sourcing_questions.asked_by_organization_id nunca se borra, es la única
-- forma de que el comprador siga sabiendo con quién habló si necesita
-- seguimiento — la anonimización es de cara a LOS OTROS participantes, no al
-- comprador).
-- ============================================================================

create type app.sourcing_answer_visibility as enum ('PRIVATE_TO_ASKER', 'ALL_PARTICIPANTS');

create table public.sourcing_questions (
  id                        uuid primary key default gen_random_uuid(),
  sourcing_event_id         uuid not null references public.sourcing_events (id) on delete cascade,
  asked_by_organization_id  uuid not null references public.organizations (id) on delete cascade,
  asked_by                  uuid references public.profiles (id) on delete set null,

  body                      text not null,
  is_answered               boolean not null default false,
  asked_at                  timestamptz not null default now()
);

comment on table public.sourcing_questions is
  'Consulta de un proveedor participante sobre el evento (§D8). is_answered se mantiene por el service al insertar la respuesta, no por trigger — mismo criterio que accreditation_enrollments.completion_pct.';

create index sourcing_questions_event_idx on public.sourcing_questions (sourcing_event_id);
create index sourcing_questions_org_idx on public.sourcing_questions (asked_by_organization_id);


create table public.sourcing_answers (
  id             uuid primary key default gen_random_uuid(),
  question_id    uuid not null references public.sourcing_questions (id) on delete cascade,

  body           text not null,
  visibility     app.sourcing_answer_visibility not null default 'ALL_PARTICIPANTS',
  answered_by    uuid references public.profiles (id) on delete set null,
  answered_at    timestamptz not null default now(),
  published_at   timestamptz,

  constraint sourcing_answers_unique_per_question unique (question_id)
);

comment on table public.sourcing_answers is
  'Respuesta del comprador. published_at nulo = borrador, no visible todavía para nadie salvo el comprador — se fija al publicar. visibility=ALL_PARTICIPANTS anonimiza al autor de la pregunta frente a los demás participantes (nunca frente al comprador).';

create index sourcing_answers_question_idx on public.sourcing_answers (question_id);
