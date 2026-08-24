import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { getPublicOrganization } from '@/lib/discoverApi';

export default function ComparePage() {
  const [searchParams] = useSearchParams();
  const slugs = (searchParams.get('ids') || '').split(',').filter(Boolean);
  const [orgs, setOrgs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // AbortController real, no solo una bandera: en React 18 StrictMode el
    // efecto se invoca dos veces seguidas (montar → limpiar → montar), y sin
    // cancelar la petición de verdad quedan dos GET idénticos en vuelo — el
    // navegador puede abortar cualquiera de los dos indistintamente, así que
    // una bandera "cancelled" no garantiza que la respuesta que sí se aplica
    // sea la de la instancia todavía montada.
    const controller = new AbortController();
    setLoading(true);
    Promise.all(
      slugs.map((slug) => getPublicOrganization(slug, { signal: controller.signal }).catch(() => null)),
    )
      .then((results) => setOrgs(results.filter(Boolean)))
      .finally(() => setLoading(false));
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams.get('ids')]);

  if (loading) {
    return <div className="h-64 animate-pulse rounded-lg bg-secondary" />;
  }

  return (
    <div className="space-y-6">
      <Helmet>
        <title>Comparar proveedores · Directorio de Empresas</title>
      </Helmet>

      <div>
        <Link to="/buscar" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="size-3.5" />
          Buscar proveedores
        </Link>
      </div>

      <h1 className="text-2xl font-semibold tracking-tight">Comparar proveedores</h1>

      {orgs.length === 0 ? (
        <p className="text-sm text-muted-foreground">No se pudo cargar ninguno de los proveedores seleccionados.</p>
      ) : (
        <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${orgs.length}, minmax(240px, 1fr))` }}>
          {orgs.map((org) => (
            <Card key={org.id}>
              <CardHeader className="flex flex-row items-center gap-3">
                {org.logo_url && <img src={org.logo_url} alt={org.trade_name} className="size-10 rounded-lg border object-contain p-1" />}
                <CardTitle className="text-base">{org.trade_name || org.legal_name}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 text-sm">
                {org.short_description && <p className="text-muted-foreground">{org.short_description}</p>}

                <div>
                  <dt className="text-xs font-medium text-muted-foreground">Completitud del perfil</dt>
                  <dd className="font-medium">{org.completion_pct}%</dd>
                </div>

                <div>
                  <dt className="text-xs font-medium text-muted-foreground">Industrias</dt>
                  <dd className="mt-1 flex flex-wrap gap-1">
                    {org.industries.map((i) => <Badge key={i} variant="neutral">{i}</Badge>)}
                    {org.industries.length === 0 && <span className="text-muted-foreground">—</span>}
                  </dd>
                </div>

                <div>
                  <dt className="text-xs font-medium text-muted-foreground">Cobertura</dt>
                  <dd className="mt-1 flex flex-wrap gap-1">
                    {org.territories.map((t) => <Badge key={t} variant="neutral">{t}</Badge>)}
                    {org.territories.length === 0 && <span className="text-muted-foreground">—</span>}
                  </dd>
                </div>

                <div>
                  <dt className="text-xs font-medium text-muted-foreground">Certificaciones</dt>
                  <dd className="mt-1 flex flex-wrap gap-1">
                    {org.certifications.map((c) => <Badge key={c} variant="success">{c}</Badge>)}
                    {org.certifications.length === 0 && <span className="text-muted-foreground">Sin certificaciones declaradas</span>}
                  </dd>
                </div>

                <div>
                  <dt className="text-xs font-medium text-muted-foreground">Catálogo ({org.offerings.length})</dt>
                  <dd className="mt-1 space-y-1">
                    {org.offerings.map((o) => (
                      <p key={o.id} className="text-sm">
                        {o.name}
                        {o.price_type === 'FROM' && o.amount_min && (
                          <span className="text-muted-foreground"> — desde {o.amount_min} {o.currency_code}</span>
                        )}
                      </p>
                    ))}
                  </dd>
                </div>

                <Button asChild variant="outline" size="sm" className="w-full">
                  <a href={`/proveedores/${org.slug}`} target="_blank" rel="noreferrer">Ver perfil completo</a>
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
