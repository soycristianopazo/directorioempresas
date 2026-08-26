import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { BookmarkPlus, GitCompare, MessageSquare, Search } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { SupplierProfileModal } from '@/components/SupplierProfileModal';
import { searchOfferings } from '@/lib/discoverApi';
import { listSupplierLists, createSupplierList, addSupplierListItem } from '@/lib/supplierListsApi';
import { cn } from '@/lib/utils';

const OFFERING_TYPE_LABELS = {
  PRODUCT: 'Producto', SERVICE: 'Servicio', RENTAL: 'Arriendo',
  SOFTWARE: 'Software', TRAINING: 'Capacitación', CONSULTING: 'Consultoría',
};

const PAGE_SIZE = 10;

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
  const [profileSlug, setProfileSlug] = useState(null);

  async function runSearch(signal) {
    setLoading(true);
    try {
      const data = await searchOfferings({ q, taxonomyNodeIds, industryIds, adminDivisionIds, page, pageSize: PAGE_SIZE }, { signal });
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

      {(result.facets.taxonomy_nodes.length > 0 ||
        result.facets.industries.length > 0 ||
        result.facets.admin_divisions.length > 0) && (
        <div className="flex flex-wrap gap-x-8 gap-y-3 rounded-lg border p-4">
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
        </div>
      )}

      <div className="space-y-3">
        <p className="text-sm text-muted-foreground">{result.total} resultado{result.total !== 1 && 's'}</p>

        {loading ? (
          <div className="space-y-2">
            <div className="h-10 animate-pulse rounded-lg bg-secondary" />
            <div className="h-10 animate-pulse rounded-lg bg-secondary/60" />
            <div className="h-10 animate-pulse rounded-lg bg-secondary/60" />
          </div>
        ) : (
          <div className="overflow-x-auto rounded-lg border">
            <table className="w-full text-left text-sm">
              <thead className="bg-secondary/50 text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="w-10 px-3 py-2"></th>
                  <th className="px-3 py-2 font-medium">Proveedor</th>
                  <th className="px-3 py-2 font-medium">Producto / servicio</th>
                  <th className="px-3 py-2 font-medium">Descripción</th>
                  <th className="px-3 py-2 font-medium">Comuna</th>
                  <th className="px-3 py-2 font-medium">Estado de acreditación</th>
                  <th className="w-10 px-3 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {result.results.map((r) => (
                  <tr key={r.offering_id} className="border-t align-top">
                    <td className="px-3 py-3">
                      <input
                        type="checkbox"
                        className="mt-0.5 size-4"
                        checked={selectedOrgIds.includes(r.organization_id)}
                        onChange={() => toggleSelect(r.organization_id)}
                      />
                    </td>
                    <td className="px-3 py-3">
                      <button
                        type="button"
                        onClick={() => setProfileSlug(r.organization_slug)}
                        className="font-medium text-primary hover:underline"
                      >
                        {r.trade_name || r.legal_name}
                      </button>
                    </td>
                    <td className="px-3 py-3">
                      <a
                        href={`/proveedores/${r.organization_slug}#offering-${r.offering_slug}`}
                        target="_blank"
                        rel="noreferrer"
                        className="font-medium hover:underline"
                      >
                        {r.offering_name}
                      </a>
                      <div className="mt-1 flex flex-wrap items-center gap-1.5">
                        <Badge variant="neutral">{OFFERING_TYPE_LABELS[r.offering_type] ?? r.offering_type}</Badge>
                        {r.deal_price != null && (
                          <Badge variant="destructive" className="gap-1">
                            🔥 {r.deal_price} {r.deal_currency_code}
                            {r.deal_stock_remaining != null && ` · quedan ${r.deal_stock_remaining}`}
                          </Badge>
                        )}
                      </div>
                    </td>
                    <td className="max-w-xs px-3 py-3 text-muted-foreground">{r.short_description || '—'}</td>
                    <td className="px-3 py-3 whitespace-nowrap text-muted-foreground">{r.comuna || '—'}</td>
                    <td className="px-3 py-3 whitespace-nowrap">
                      {r.is_accredited ? (
                        <Badge variant="success">✓ Acreditado</Badge>
                      ) : (
                        <Badge variant="neutral">Sin acreditar</Badge>
                      )}
                    </td>
                    <td className="relative px-3 py-3">
                      <div className="flex items-center gap-1.5">
                        <Link to={`/empresa/mensajes?withOrg=${r.organization_id}`}>
                          <Button variant="outline" size="sm" className="gap-1.5">
                            <MessageSquare className="size-3.5" />
                            Mensaje
                          </Button>
                        </Link>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setListPickerFor(listPickerFor === r.organization_id ? null : r.organization_id)}
                          className="gap-1.5"
                        >
                          <BookmarkPlus className="size-3.5" />
                          Guardar
                        </Button>
                      </div>
                      {listPickerFor === r.organization_id && (
                        <div className="absolute right-3 z-10 mt-1 w-48 rounded-lg border bg-popover p-1.5 shadow-md">
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
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {result.results.length === 0 && (
              <p className="px-4 py-8 text-center text-sm text-muted-foreground">
                No encontramos resultados con estos filtros.
              </p>
            )}
          </div>
        )}

        {result.total > PAGE_SIZE && (
          <div className="flex items-center gap-2 pt-2">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              Anterior
            </Button>
            <span className="text-sm text-muted-foreground">
              Página {page} de {Math.ceil(result.total / PAGE_SIZE)}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={page * PAGE_SIZE >= result.total}
              onClick={() => setPage((p) => p + 1)}
            >
              Siguiente
            </Button>
          </div>
        )}
      </div>

      <SupplierProfileModal
        slug={profileSlug}
        open={!!profileSlug}
        onOpenChange={(open) => !open && setProfileSlug(null)}
      />
    </div>
  );
}

function FacetGroup({ title, items, selected, onToggle }) {
  if (!items.length) return null;
  return (
    <div>
      <h3 className="mb-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">{title}</h3>
      <div className="flex flex-wrap gap-1.5">
        {items.map((f) => {
          const active = selected.includes(f.value);
          return (
            <button
              key={f.value}
              type="button"
              onClick={() => onToggle(f.value)}
              className={cn(
                'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-colors',
                active ? 'border-primary bg-primary/10 text-primary' : 'border-input hover:bg-accent',
              )}
            >
              {f.label}
              <span className={cn('text-[10px]', active ? 'text-primary/70' : 'text-muted-foreground')}>{f.count}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
