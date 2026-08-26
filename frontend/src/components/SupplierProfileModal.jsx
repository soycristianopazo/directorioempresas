import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ExternalLink, MapPinned, MessageSquare, Package } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { getPublicOrganization } from '@/lib/discoverApi';

const OFFERING_TYPE_LABELS = {
  PRODUCT: 'Producto', SERVICE: 'Servicio', RENTAL: 'Arriendo',
  SOFTWARE: 'Software', TRAINING: 'Capacitación', CONSULTING: 'Consultoría',
};

/** Ficha del proveedor en un modal — se abre al hacer click en el nombre del
 * proveedor desde una tabla de resultados, sin sacar al usuario de la
 * búsqueda. Reutiliza /api/discover/organizations/{slug}, la misma data que
 * sirve la página pública Jinja2 (/proveedores/:slug) fuera de la SPA — acá
 * se muestra un resumen, con link a esa página completa para más detalle.
 */
export function SupplierProfileModal({ slug, open, onOpenChange }) {
  const [org, setOrg] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open || !slug) return;
    setLoading(true);
    setOrg(null);
    const controller = new AbortController();
    getPublicOrganization(slug, { signal: controller.signal })
      .then(setOrg)
      .catch(() => {})
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [open, slug]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        {loading && <div className="h-40 animate-pulse rounded-lg bg-secondary" />}

        {!loading && org && (
          <>
            <DialogHeader>
              <div className="flex items-center gap-3">
                {org.logo_url && (
                  <img src={org.logo_url} alt="" className="size-12 rounded-lg border object-contain p-1" />
                )}
                <div>
                  <DialogTitle>{org.trade_name || org.legal_name}</DialogTitle>
                  {org.short_description && (
                    <p className="mt-0.5 text-sm text-muted-foreground">{org.short_description}</p>
                  )}
                </div>
              </div>
            </DialogHeader>

            <div className="space-y-4">
              {org.description && <p className="text-sm">{org.description}</p>}

              {org.badges.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {org.badges.map((b) => (
                    <Badge key={b.code} variant="success" title={b.description || undefined}>
                      ✓ {b.name}
                    </Badge>
                  ))}
                </div>
              )}

              {org.industries.length > 0 && (
                <div>
                  <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">Industrias</p>
                  <div className="flex flex-wrap gap-1.5">
                    {org.industries.map((i) => (
                      <Badge key={i} variant="neutral">{i}</Badge>
                    ))}
                  </div>
                </div>
              )}

              {org.territories.length > 0 && (
                <div>
                  <p className="mb-1 flex items-center gap-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    <MapPinned className="size-3" />
                    Cobertura
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {org.territories.map((t) => (
                      <Badge key={t} variant="neutral">{t}</Badge>
                    ))}
                  </div>
                </div>
              )}

              {org.offerings.length > 0 && (
                <div>
                  <p className="mb-1.5 flex items-center gap-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    <Package className="size-3" />
                    Catálogo ({org.offerings.length})
                  </p>
                  <ul className="divide-y rounded-lg border">
                    {org.offerings.map((o) => (
                      <li key={o.id}>
                        <a
                          href={`/proveedores/${org.slug}#offering-${o.slug}`}
                          target="_blank"
                          rel="noreferrer"
                          className="flex items-center justify-between gap-2 px-3 py-2 text-sm hover:bg-accent"
                        >
                          <span>
                            <span className="font-medium">{o.name}</span>{' '}
                            <span className="text-xs text-muted-foreground">
                              ({OFFERING_TYPE_LABELS[o.offering_type] ?? o.offering_type})
                            </span>
                          </span>
                          <ExternalLink className="size-3.5 shrink-0 text-muted-foreground" />
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="flex flex-wrap gap-2">
                <Link to={`/empresa/mensajes?withOrg=${org.id}`}>
                  <Button size="sm" className="gap-1.5">
                    <MessageSquare className="size-3.5" />
                    Mensaje
                  </Button>
                </Link>
                <Button asChild variant="outline" size="sm" className="gap-1.5">
                  <a href={`/proveedores/${org.slug}`} target="_blank" rel="noreferrer">
                    Ver perfil completo
                    <ExternalLink className="size-3.5" />
                  </a>
                </Button>
              </div>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
