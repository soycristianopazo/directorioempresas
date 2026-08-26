-- ============================================================================
-- 0086 · Forma del logo (cuadrado / horizontal)
-- ----------------------------------------------------------------------------
-- El proveedor sube un único LOGO (0020) pero puede declarar si es un
-- isotipo cuadrado o un logotipo horizontal — el perfil público (y la vista
-- previa desde "Mi empresa") usan esto para elegir el contenedor correcto en
-- vez de forzar todo a una caja 1:1 con letterboxing.
-- ============================================================================

alter table public.organization_media
  add column logo_shape text
    constraint organization_media_logo_shape_check
    check (logo_shape in ('SQUARE', 'HORIZONTAL'));

comment on column public.organization_media.logo_shape is
  'Solo aplica a media_type=LOGO. NULL para BANNER/GALLERY/VIDEO y para logos subidos antes de esta columna (el frontend los trata como SQUARE).';
