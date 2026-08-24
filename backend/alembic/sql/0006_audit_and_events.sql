-- ============================================================================
-- 0005 · Auditoría inmutable y outbox de eventos de dominio
-- ----------------------------------------------------------------------------
-- Fase 1.9. Ver §52 del brief y mejora N.15.
--
-- Dos tablas con propósitos distintos que suelen confundirse:
--
--   audit_logs    · registro forense. Inmutable. Responde "quién cambió qué".
--                   Nadie puede editarlo ni borrarlo, ni service_role.
--
--   domain_events · outbox transaccional. Efímero. Responde "qué pasó, para
--                   que alguien reaccione". Los triggers escriben aquí y los
--                   workers consumen: notificaciones, analítica, webhooks.
--                   NUNCA enviar emails desde un trigger.
-- ============================================================================

-- ─── Auditoría ──────────────────────────────────────────────────────────────

create table public.audit_logs (
  id              bigint generated always as identity,
  occurred_at     timestamptz not null default now(),

  actor_id        uuid,
  organization_id uuid,

  action          text not null,
  entity_type     text not null,
  entity_id       uuid,

  previous_value  jsonb,
  new_value       jsonb,

  -- Contexto de la petición, poblado por la capa de aplicación.
  ip_address      inet,
  user_agent      text,
  request_id      text,

  -- Motivo obligatorio en acciones sensibles (impersonación, apertura de
  -- ofertas selladas, acceso administrativo a datos de una organización).
  reason          text,

  primary key (id, occurred_at)
) partition by range (occurred_at);

comment on table public.audit_logs is
  'Auditoría forense inmutable, particionada por mes. Sin UPDATE ni DELETE.';

-- Sin FK a profiles/organizations a propósito: el registro de auditoría debe
-- sobrevivir al borrado de la entidad auditada. Se guarda el uuid crudo.

create index audit_logs_org_idx    on public.audit_logs (organization_id, occurred_at desc);
create index audit_logs_actor_idx  on public.audit_logs (actor_id, occurred_at desc);
create index audit_logs_entity_idx on public.audit_logs (entity_type, entity_id, occurred_at desc);


-- Crea las particiones mensuales que falten en una ventana dada.
-- Se ejecuta abajo para cubrir 24 meses; en la fase 2 se agenda con pg_cron.
create or replace function app.ensure_audit_partitions(
  p_months_ahead int default 12,
  p_months_back  int default 1
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_start date;
  v_end   date;
  v_name  text;
  v_i     int;
begin
  for v_i in -p_months_back .. p_months_ahead loop
    v_start := date_trunc('month', now())::date + make_interval(months => v_i);
    v_end   := v_start + interval '1 month';
    v_name  := format('audit_logs_%s', to_char(v_start, 'YYYY_MM'));

    if not exists (
      select 1 from pg_class c
      join pg_namespace n on n.oid = c.relnamespace
      where c.relname = v_name and n.nspname = 'public'
    ) then
      execute format(
        'create table public.%I partition of public.audit_logs
           for values from (%L) to (%L)',
        v_name, v_start, v_end
      );
      -- La partición hereda RLS de la tabla padre, pero los GRANT no.
      execute format('revoke all on public.%I from public', v_name);
    end if;
  end loop;
end;
$$;

select app.ensure_audit_partitions(23, 1);


-- Inmutabilidad real: ni el rol de servicio puede modificar la auditoría.
revoke update, delete, truncate on public.audit_logs from public, app_user;

create or replace function app.audit_logs_deny_mutation()
returns trigger
language plpgsql
as $$
begin
  raise exception 'audit_logs es inmutable: % no está permitido', tg_op
    using errcode = 'insufficient_privilege';
end;
$$;

create trigger trg_audit_logs_immutable
  before update or delete on public.audit_logs
  for each row execute function app.audit_logs_deny_mutation();


-- Escritura de auditoría desde la capa de aplicación o desde triggers.
create or replace function app.write_audit(
  p_action        text,
  p_entity_type   text,
  p_entity_id     uuid    default null,
  p_organization_id uuid  default null,
  p_previous      jsonb   default null,
  p_new           jsonb   default null,
  p_reason        text    default null
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.audit_logs (
    actor_id, organization_id, action, entity_type, entity_id,
    previous_value, new_value, reason
  )
  values (
    app.current_user_id(), p_organization_id, p_action, p_entity_type, p_entity_id,
    p_previous, p_new, p_reason
  );
end;
$$;


-- ============================================================================
-- Outbox de eventos de dominio
-- ============================================================================

create table public.domain_events (
  id             bigint generated always as identity primary key,

  event_type     text not null,
  aggregate_type text not null,
  aggregate_id   uuid,
  organization_id uuid,

  payload        jsonb not null default '{}'::jsonb,

  occurred_at    timestamptz not null default now(),
  processed_at   timestamptz,
  attempts       smallint not null default 0,
  last_error     text,

  constraint domain_events_event_type_format check (event_type ~ '^[a-z_]+\.[a-z_]+$'),
  constraint domain_events_attempts check (attempts >= 0)
);

comment on table public.domain_events is
  'Outbox transaccional. Único punto de emisión de efectos secundarios (mejora N.15).';

-- El índice que consume el worker: solo lo pendiente.
create index domain_events_pending_idx
  on public.domain_events (occurred_at)
  where processed_at is null;

create index domain_events_aggregate_idx
  on public.domain_events (aggregate_type, aggregate_id, occurred_at desc);

-- Eventos que agotaron reintentos: cola de veneno para revisión manual.
create index domain_events_failed_idx
  on public.domain_events (occurred_at desc)
  where processed_at is null and attempts >= 5;


create or replace function app.emit_event(
  p_event_type     text,
  p_aggregate_type text,
  p_aggregate_id   uuid  default null,
  p_organization_id uuid default null,
  p_payload        jsonb default '{}'::jsonb
)
returns bigint
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_id bigint;
begin
  insert into public.domain_events (
    event_type, aggregate_type, aggregate_id, organization_id, payload
  )
  values (
    p_event_type, p_aggregate_type, p_aggregate_id, p_organization_id, p_payload
  )
  returning id into v_id;

  return v_id;
end;
$$;

comment on function app.emit_event is
  'Emite un evento de dominio al outbox. Los triggers usan esto en vez de efectos directos.';
