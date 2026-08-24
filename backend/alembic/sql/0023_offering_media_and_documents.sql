-- ============================================================================
-- 0023 · Media y documentos de un offering
-- ----------------------------------------------------------------------------
-- Fase 3.3 del roadmap. storage_path es relativo a Supabase Storage — fotos
-- en el bucket público `org-media`, documentos en el privado `org-documents`
-- (is_public controla si el backend emite una URL firmada o pública). Ver
-- backend/app/core/storage.py y scripts/storage-setup-buckets.mjs.
-- ============================================================================

create table public.offering_media (
  id            uuid primary key default gen_random_uuid(),
  offering_id   uuid not null references public.supplier_offerings (id) on delete cascade,

  storage_path  text not null,
  alt_text      text,
  sort_order    int not null default 0,

  created_at    timestamptz not null default now(),
  created_by    uuid references public.profiles (id) on delete set null
);

comment on table public.offering_media is
  'Fotos, videos, renders del offering. Bucket org-media (público).';

create index offering_media_offering_idx on public.offering_media (offering_id);


create table public.offering_documents (
  id            uuid primary key default gen_random_uuid(),
  offering_id   uuid not null references public.supplier_offerings (id) on delete cascade,

  name          text not null,
  storage_path  text not null,
  is_public     boolean not null default true,

  created_at    timestamptz not null default now(),
  created_by    uuid references public.profiles (id) on delete set null
);

comment on table public.offering_documents is
  'Fichas técnicas, catálogos PDF, manuales. Bucket org-documents (privado — is_public controla si se emite URL firmada de corta duración o de más largo alcance).';

create index offering_documents_offering_idx on public.offering_documents (offering_id);
