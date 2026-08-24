-- ============================================================================
-- 0012 · Divisiones administrativas + trigger genérico de jerarquías
-- ----------------------------------------------------------------------------
-- Fase 2.2 del roadmap. Ver docs/02-MODELO-DATOS.md §D.1 ("tres árboles, una
-- técnica"): admin_divisions, taxonomy_nodes (0014) e industries (0014)
-- comparten la misma forma (self-FK + level + path ltree) y por eso comparten
-- una sola función de trigger, en vez de triplicar la lógica.
-- ============================================================================

-- ============================================================================
-- Privilegios sobre el esquema extensions — y por qué el trigger de más
-- abajo NUNCA escribe "ltree" a secas.
-- ----------------------------------------------------------------------------
-- `extensions` (donde vive ltree, creado en 0001) nunca recibió GRANT USAGE
-- para `app_user` — 0010_hardening.sql solo otorga `public` y `app`. Se
-- otorga aquí por completitud/defensa en profundidad, pero NO es la causa
-- real de que un cast a ltree falle para app_user — Postgres da USAGE sobre
-- un tipo a PUBLIC por defecto salvo REVOKE explícito, y nadie lo revocó.
--
-- La causa real es search_path. `postgres` tiene, por convención propia de
-- Supabase, `"$user", public, extensions` — pero `app_user` (un rol creado
-- por esta aplicación, no por Supabase) tiene el default de Postgres liso:
-- `"$user", public`, SIN `extensions`. El trigger app.maintain_hierarchy_path()
-- (más abajo) no es SECURITY DEFINER — corre con los privilegios Y el
-- search_path de quien dispara el INSERT, que en producción es siempre
-- `app_user` — así que cualquier `::ltree` sin calificar dentro de ese
-- trigger no lo encuentra.
--
-- El síntoma apunta exactamente al lugar equivocado: "type ltree does not
-- exist" — el mismo mensaje, palabra por palabra, que Postgres daría si la
-- extensión no estuviera instalada. Se probó y descartó primero la hipótesis
-- de permisos (de ahí el GRANT de abajo, que no cambió nada), después la de
-- Supavisor/pooler de transacciones (mismo error conectando por el pooler de
-- sesión), y recién con `show search_path` conectado explícitamente como
-- `app_user` apareció la diferencia real frente a `postgres`. La lección:
-- reproducir con el ROL exacto de producción, no con un superusuario que
-- ignora silenciosamente esta clase entera de problemas.
--
-- La solución que de verdad importa es la de la función de abajo: calificar
-- `extensions.ltree` explícitamente en cada cast y cada declaración de
-- variable, en vez de depender de que el search_path de quien ejecute el
-- trigger incluya `extensions` — ni app_user hoy ni cualquier rol futuro
-- deberían necesitar un search_path especial solo para que este trigger
-- funcione.
grant usage on schema extensions to app_user;


create table public.admin_divisions (
  id                uuid primary key default gen_random_uuid(),
  country_code      char(2) not null references public.countries (code),
  parent_id         uuid references public.admin_divisions (id) on delete restrict,

  level             smallint not null,
  -- Texto libre, no ENUM: el vocabulario de niveles varía por país (Chile usa
  -- región/provincia/comuna; otro país podría no tener un nivel intermedio, o
  -- llamarlo distinto). Es exactamente el caso que docs/01-ARQUITECTURA.md
  -- §A.5 marca como catálogo, no ENUM: el negocio puede necesitar vocabulario
  -- nuevo sin deploy.
  level_name        text not null,

  slug              text not null,
  path              ltree not null,
  official_code     text,  -- CUT en Chile; equivalente local en otros países
  name              text not null,
  lat               numeric(9, 6),
  lng               numeric(9, 6),
  is_active         boolean not null default true,

  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now(),

  constraint admin_divisions_unique_slug unique (country_code, parent_id, slug)
);

comment on table public.admin_divisions is
  'Jerarquía territorial genérica multi-país (región→provincia→comuna en Chile). Ver 0013 para el seed de Chile.';

create index admin_divisions_path_gist_idx on public.admin_divisions using gist (path);
create index admin_divisions_country_level_idx on public.admin_divisions (country_code, level);
create unique index admin_divisions_official_code_idx
  on public.admin_divisions (country_code, official_code)
  where official_code is not null;

-- La constraint unique(country_code, parent_id, slug) de arriba NO cubre las
-- filas raíz: Postgres trata cada NULL de parent_id como distinto de
-- cualquier otro NULL, así que dos regiones con el mismo slug no chocarían
-- contra esa constraint. Mismo patrón que roles_system_code_key en 0004.
create unique index admin_divisions_root_slug_idx
  on public.admin_divisions (country_code, slug)
  where parent_id is null;

select app.apply_table_conventions('public.admin_divisions');


-- ============================================================================
-- app.maintain_hierarchy_path() — trigger genérico y reutilizable
-- ----------------------------------------------------------------------------
-- Se aplica a admin_divisions (aquí) y a taxonomy_nodes/industries (0014).
-- Requiere que la tabla tenga exactamente las columnas: id, parent_id, slug,
-- level, path.
--
-- GOTCHA QUE ESTE TRIGGER EXISTE PARA EVITAR — leer antes de tocar esta
-- función:
-- ----------------------------------------------------------------------------
-- Los labels de ltree solo aceptan el alfabeto [A-Za-z0-9_] (documentado en
-- la propia extensión: cualquier otro carácter, incluido el guion, revienta
-- con "invalid label"). Pero app.slugify() —usada en toda la aplicación para
-- generar slugs URL-safe— produce guiones para separar palabras:
-- "Plantas concentradoras" → "plantas-concentradoras". Un slug así es
-- perfectamente válido como slug, pero NO es un label de ltree válido.
--
-- Si este trigger construyera el path concatenando new.slug tal cual, el
-- primer nodo con un slug de más de una palabra (que es casi cualquiera:
-- "servicios-electricos", "arriendo-de-maquinaria", "plantas-concentradoras")
-- haría fallar el INSERT con:
--
--   ERROR: syntax error at or near "-"
--   LINE 1: ...concentradoras
--   invalid label
--
-- Ese error no apunta a la causa real (guion en un label de ltree) desde
-- ningún lado obvio del mensaje — hay que saber de antemano que ltree es
-- quisquilloso con esto para no perder tiempo buscando en el lugar
-- equivocado (¿el path del padre? ¿el índice GiST? ¿una constraint?).
--
-- La solución es simple una vez conocida: reemplazar '-' por '_' SOLO al
-- construir el label de ltree, dejando slug intacto (slug sigue siendo el
-- valor URL-safe con guiones que usa el resto de la aplicación, ej. en
-- rutas). ltree y slug son dos representaciones distintas del mismo nodo,
-- no la misma columna vista dos veces.
-- ============================================================================

-- set search_path = public, extensions: fija el search_path DE ESTA FUNCIÓN
-- para su propia ejecución, sin importar el del rol que la invoque (Postgres
-- restaura el search_path del llamador automáticamente al retornar — el
-- mismo mecanismo que ya usan los helpers SECURITY DEFINER de 0007, aquí sin
-- SECURITY DEFINER: el trigger sigue corriendo con los privilegios de quien
-- dispara el INSERT, RLS incluido, solo cambia qué nombres resuelve).
--
-- Hace falta por DOS razones, no una: calificar `extensions.ltree` en cada
-- cast (ver más abajo) resuelve el TIPO, pero el operador de concatenación
-- `path || label` sigue sin encontrarse — a diferencia de las funciones, un
-- operador infijo como `||` no admite calificarse inline
-- (`a extensions.|| b` no es sintaxis válida; existiría `OPERATOR(extensions.||)`
-- pero es más críptico que fijar el search_path una vez acá). Sin este SET,
-- el síntoma cambia pero la causa es la misma: "operator does not exist:
-- extensions.ltree || extensions.ltree" — search_path sigue sin incluir
-- `extensions` para app_user aunque el tipo ya esté calificado.
create or replace function app.maintain_hierarchy_path()
returns trigger
language plpgsql
set search_path = public, extensions
as $$
declare
  v_parent_level int;
  v_parent_path  extensions.ltree;
  v_label        text := replace(new.slug, '-', '_');
begin
  if new.parent_id is null then
    new.level := 1;
    new.path  := v_label::extensions.ltree;
    return new;
  end if;

  execute format(
    'select level, path from %s where id = $1',
    tg_relid::regclass
  )
  into v_parent_level, v_parent_path
  using new.parent_id;

  if v_parent_path is null then
    raise exception 'parent_id % no existe en % (¿se insertó fuera de orden?)',
      new.parent_id, tg_table_name
      using errcode = 'foreign_key_violation';
  end if;

  new.level := v_parent_level + 1;
  new.path  := v_parent_path || v_label::extensions.ltree;

  return new;
end;
$$;

comment on function app.maintain_hierarchy_path() is
  'Trigger BEFORE INSERT/UPDATE OF parent_id, slug — calcula level y path (ltree) a partir del padre. Reutilizado por admin_divisions, taxonomy_nodes e industries. Convierte "-" a "_" en el label: ver el comentario extenso arriba.';

create trigger trg_admin_divisions_path
  before insert or update of parent_id, slug on public.admin_divisions
  for each row execute function app.maintain_hierarchy_path();
