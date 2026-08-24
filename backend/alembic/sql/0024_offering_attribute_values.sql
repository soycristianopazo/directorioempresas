-- ============================================================================
-- 0024 · Valores de atributos dinámicos declarados por el proveedor
-- ----------------------------------------------------------------------------
-- Fase 3.3 del roadmap. Ver docs/02-MODELO-DATOS.md §D3.
--
-- Un offering_attribute_values por (offering, attribute_definition). Columnas
-- tipadas — exactamente una poblada, la que corresponde al data_type del
-- atributo. A diferencia del doc original ("CHECK: exactamente una poblada
-- según data_type"), un CHECK de fila no puede consultar otra tabla
-- (attribute_definitions) para saber CUÁL debe estar poblada — así que la
-- regla completa vive en un trigger (app.validate_offering_attribute_value),
-- no en un CHECK. El CHECK de abajo sí cubre la parte que no necesita JOIN:
-- nunca más de una columna poblada a la vez.
-- ============================================================================

create table public.offering_attribute_values (
  id                       uuid primary key default gen_random_uuid(),
  offering_id              uuid not null references public.supplier_offerings (id) on delete cascade,
  attribute_definition_id  uuid not null references public.attribute_definitions (id),

  value_text               text,
  value_number             numeric,
  value_boolean            boolean,
  value_date               date,
  value_range              numrange,
  option_id                uuid references public.attribute_options (id),

  created_at               timestamptz not null default now(),
  updated_at               timestamptz not null default now(),

  constraint offering_attribute_values_unique unique (offering_id, attribute_definition_id),
  constraint offering_attribute_values_single_slot check (
    num_nonnulls(value_text, value_number, value_boolean, value_date, value_range, option_id) <= 1
  )
);

comment on table public.offering_attribute_values is
  'Valor declarado por el proveedor para un atributo dinámico (0016). option_id se usa para SELECT; MULTISELECT usa offering_attribute_option_values en su lugar y deja esta fila sin ningún slot poblado (solo marca que el atributo fue considerado).';

create index offering_attribute_values_offering_idx on public.offering_attribute_values (offering_id);
create index offering_attribute_values_def_idx on public.offering_attribute_values (attribute_definition_id);

select app.apply_table_conventions('public.offering_attribute_values');


create or replace function app.validate_offering_attribute_value()
returns trigger
language plpgsql
as $$
declare
  v_data_type app.attribute_data_type;
  v_slots_filled int;
begin
  select data_type into v_data_type
  from public.attribute_definitions
  where id = new.attribute_definition_id;

  v_slots_filled := num_nonnulls(
    new.value_text, new.value_number, new.value_boolean,
    new.value_date, new.value_range, new.option_id
  );

  -- MULTISELECT no llena ningún slot en esta fila: los valores viven en
  -- offering_attribute_option_values. Cualquier otro tipo debe llenar
  -- exactamente el slot que le corresponde.
  if v_data_type = 'MULTISELECT' then
    if v_slots_filled > 0 then
      raise exception 'Un atributo MULTISELECT no debe poblar ningún slot en offering_attribute_values (usar offering_attribute_option_values)'
        using errcode = 'check_violation';
    end if;
    return new;
  end if;

  if v_slots_filled <> 1 then
    raise exception 'El atributo % (tipo %) debe poblar exactamente un slot de valor', new.attribute_definition_id, v_data_type
      using errcode = 'check_violation';
  end if;

  if (v_data_type = 'TEXT' and new.value_text is null)
     or (v_data_type = 'NUMBER' and new.value_number is null)
     or (v_data_type = 'BOOLEAN' and new.value_boolean is null)
     or (v_data_type = 'DATE' and new.value_date is null)
     or (v_data_type = 'RANGE' and new.value_range is null)
     or (v_data_type = 'SELECT' and new.option_id is null)
  then
    raise exception 'El slot poblado no corresponde al data_type % del atributo', v_data_type
      using errcode = 'check_violation';
  end if;

  return new;
end;
$$;

comment on function app.validate_offering_attribute_value() is
  'Trigger BEFORE INSERT/UPDATE — valida que el slot de valor poblado corresponda al data_type real del atributo (consulta que un CHECK de fila no puede hacer).';

create trigger trg_offering_attribute_values_validate
  before insert or update on public.offering_attribute_values
  for each row execute function app.validate_offering_attribute_value();


create table public.offering_attribute_option_values (
  offering_attribute_value_id  uuid not null references public.offering_attribute_values (id) on delete cascade,
  option_id                     uuid not null references public.attribute_options (id),

  primary key (offering_attribute_value_id, option_id)
);

comment on table public.offering_attribute_option_values is
  'Valores múltiples para atributos MULTISELECT — N filas por offering_attribute_values.';
