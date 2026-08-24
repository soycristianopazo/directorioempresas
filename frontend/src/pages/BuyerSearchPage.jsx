import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { BookmarkPlus, GitCompare, Search } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { searchOfferings } from '@/lib/discoverApi';
import { listSupplierLists, createSupplierList, addSupplierListItem } from '@/lib/supplierListsApi';

const OFFERING_TYPE_LABELS = {
  PRODUCT: 'Producto', SERVICE: 'Servicio', RENTAL: 'Arriendo',
  SOFTWARE: 'Software', TRAINING: 'Capacitación', CONSULTING: 'Consultoría',
};

export default function BuyerSearchPage() {
  const { activeOrg } = useAuth();
  const navigate = useNavigate();

  const [q, setQ] = useState('');
  const [taxonomyNodeIds, setTaxonomyNodeIds] = useState([]);
  const [industryIds, setIndustryIds] = useState([]);
  const [adminDivisionIds, setAdminDivisionIds] = useState([]);
  const [page, setPage] = useState(1);

  const [result, setResult] = useState({ results: [], total: 0, facets: { taxonomy_nodes: [], industries: [], admin_divisions: [] } });
  const [loading, setLoading] = useState(true);
  const [selectedOrgIds, setSelectedOrgIds] = useState([]);
  const [lists, setLists] = useState([]);
  const [listPickerFor, setListPickerFor] = useState(null);

  async function runSearch(signal) {
    setLoading(true);
    try {
      const data = await searchOfferings({ q, taxonomyNodeIds, industryIds, adminDivisionIds, page, pageSize: 20 }, { signal });
      setResult(data);
    } catch (error) {
      if (error.code !== 'ERR_CANCELED') toast.error('No se pudo buscar');
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }

  useEffect(() => {
    // AbortController real por la misma razón que en ComparePage.jsx: sin
    // cancelar la petición de la instancia anterior, StrictMode deja dos GET
    // idénticos en vuelo y el navegador puede resolver cualquiera de los dos.
    const controller = new AbortController();
    runSearch(controller.signal);
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taxonomyNodeIds, industryIds, adminDivisionIds, page]);

  useEffect(() => {
    if (activeOrg) listSupplierLists(activeOrg.id).then(setLists).catch(() => {});
  }, [activeOrg]);

  function toggleFacet(setter, current, value) {
    setPage(1);
    setter(current.includes(value) ? current.filter((v) => v !== value) : [...current, value]);
  }

  function toggleSelect(orgId) {
    setSelectedOrgIds((prev) => {
      if (prev.includes(orgId)) return prev.filter((id) => id !== orgId);
      if (prev.length >= 4) {
        toast.error('Puedes comparar hasta 4 proveedores a la vez');
        return prev;
      }
      return [...prev, orgId];
    });
  }

  async function handleSaveToList(organizationId, listId) {
    try {
      await addSupplierListItem(activeOrg.id, listId, { targetOrganizationId: organizationId });
      toast.success('Guardado en la lista');
      setListPickerFor(null);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo guardar');
    }
  }

  async function handleCreateListAndSave(organizationId) {
    const name = window.prompt('Nombre de la nueva lista');
    if (!name) return;
    try {
      const listId = await createSupplierList(activeOrg.id, { name });
      setLists((prev) => [...prev, { id: listId, name, is_shared_with_org: true }]);
      await handleSaveToList(organizationId, listId);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo crear la lista');
    }
  }

  if (!activeOrg) return null;

  return (
    <div className="space-y-6">
      <Helmet>
        <title>Buscar proveedores · Directorio de Empresas</title>
      </Helmet>

      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Buscar proveedores</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Filtra por categoría, industria y cobertura. Selecciona hasta 4 para comparar.
          </p>
        </div>
        {selectedOrgIds.length >= 2 && (
          <Button
            onClick={() => {
              const slugMap = Object.fromEntries(result.results.map((r) => [r.organization_id, r.organization_slug]));
              const slugs = selectedOrgIds.map((id) => slugMap[id]).filter(Boolean);
              navigate(`/comparar?ids=${slugs.join(',')}`);
            }}
            className="gap-1.5"
          >
            <GitCompare className="size-4" />
            Comparar ({selectedOrgIds.length})
          </Button>
        )}
      </header>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          setPage(1);
          runSearch();
        }}
        className="flex gap-2"
      >
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Ej. transporte de personal, EPP, mantención eléctrica"
          className="max-w-lg"
        />
        <Button type="submit" className="gap-1.5">
          <Search className="size-4" />
          Buscar
        </Button>
      </form>

      <div className="grid gap-6 sm:grid-cols-[240px_1fr]">
        <aside className="space-y-5">
          <FacetGroup
            title="Categoría"
            items={result.facets.taxonomy_nodes}
            selected={taxonomyNodeIds}
            onToggle={(v) => toggleFacet(setTaxonomyNodeIds, taxonomyNodeIds, v)}
          />
          <FacetGroup
            title="Industria"
            items={result.facets.industries}
            selected={industryIds}
            onToggle={(v) => toggleFacet(setIndustryIds, industryIds, v)}
          />
          <FacetGroup
            title="Región"
            items={result.facets.admin_divisions}
            selected={adminDivisionIds}
            onToggle={(v) => toggleFacet(setAdminDivisionIds, adminDivisionIds, v)}
          />
        </aside>

        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">{result.total} resultado{result.total !== 1 && 's'}</p>

          {loading ? (
            <div className="space-y-2">
              <div className="h-24 animate-pulse rounded-lg bg-secondary" />
              <div className="h-24 animate-pulse rounded-lg bg-secondary/60" />
            </div>
          ) : (
            result.results.map((r) => (
              <Card key={r.offering_id}>
                <CardContent className="flex items-start gap-3 p-4">
                  <input
                    type="checkbox"
                    className="mt-1 size-4"
                    checked={selectedOrgIds.includes(r.organization_id)}
                    onChange={() => toggleSelect(r.organization_id)}
                  />
                  <div className="flex-1 min-w-0">
                    <Link to={`/proveedores/${r.organization_slug}`} target="_blank" className="font-medium hover:underline">
                      {r.offering_name}
                    </Link>
                    <p className="text-xs font-medium text-primary">{r.trade_name || r.legal_name}</p>
                    {r.short_description && <p className="mt-1 text-sm text-muted-foreground">{r.short_description}</p>}
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      <Badge variant="neutral">{OFFERING_TYPE_LABELS[r.offering_type] ?? r.offering_type}</Badge>
                      {r.pricing_is_public && r.price_type === 'FROM' && (
                        <Badge variant="neutral">Desde {r.amount_min} {r.currency_code}</Badge>
                      )}
                    </div>
                  </div>
                  <div className="relative">
                    <Button variant="outline" size="sm" onClick={() => setListPickerFor(listPickerFor === r.organization_id ? null : r.organization_id)} className="gap-1.5">
                      <BookmarkPlus className="size-3.5" />
                      Guardar
                    </Button>
                    {listPickerFor === r.organization_id && (
                      <div className="absolute right-0 z-10 mt-1 w-48 rounded-lg border bg-popover p-1.5 shadow-md">
                        {lists.map((l) => (
                          <button
                            key={l.id}
                            onClick={() => handleSaveToList(r.organization_id, l.id)}
                            className="block w-full rounded px-2 py-1.5 text-left text-sm hover:bg-accent"
                          >
                            {l.name}
                          </button>
                        ))}
                        <button
                          onClick={() => handleCreateListAndSave(r.organization_id)}
                          className="block w-full rounded px-2 py-1.5 text-left text-sm text-primary hover:bg-accent"
                        >
                          + Nueva lista
                        </button>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))
          )}

          {!loading && result.results.length === 0 && (
            <p className="rounded-lg border border-dashed px-4 py-8 text-center text-sm text-muted-foreground">
              No encontramos resultados con estos filtros.
            </p>
          )}

          {result.total > 20 && (
            <div className="flex gap-2 pt-2">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                Anterior
              </Button>
              <Button variant="outline" size="sm" disabled={page * 20 >= result.total} onClick={() => setPage((p) => p + 1)}>
                Siguiente
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function FacetGroup({ title, items, selected, onToggle }) {
  if (!items.length) return null;
  return (
    <div>
      <h3 className="mb-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">{title}</h3>
      <ul className="space-y-1">
        {items.map((f) => (
          <li key={f.value}>
            <label className="flex items-center justify-between gap-2 rounded px-1.5 py-1 text-sm hover:bg-accent">
              <span className="flex items-center gap-1.5">
                <input type="checkbox" className="size-3.5" checked={selected.includes(f.value)} onChange={() => onToggle(f.value)} />
                {f.label}
              </span>
              <span className="text-xs text-muted-foreground">{f.count}</span>
            </label>
          </li>
        ))}
      </ul>
    </div>
  );
}
