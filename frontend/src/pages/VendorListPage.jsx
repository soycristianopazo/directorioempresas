import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { toast } from 'sonner';
import { Search, ShieldCheck, StickyNote } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { SelectNative } from '@/components/ui/select-native';
import { Textarea } from '@/components/ui/textarea';
import { searchOfferings } from '@/lib/discoverApi';
import { listRelationships, setRelationshipStatus, listNotes, addNote } from '@/lib/vendorListApi';

const STATUSES = [
  { value: 'POTENTIAL', label: 'Potencial' },
  { value: 'IN_EVALUATION', label: 'En evaluación' },
  { value: 'APPROVED', label: 'Aprobado' },
  { value: 'CONDITIONAL', label: 'Condicional' },
  { value: 'SUSPENDED', label: 'Suspendido' },
  { value: 'BLOCKED', label: 'Bloqueado' },
];

const STATUS_VARIANT = {
  POTENTIAL: 'neutral',
  IN_EVALUATION: 'brand',
  APPROVED: 'success',
  CONDITIONAL: 'warning',
  SUSPENDED: 'warning',
  BLOCKED: 'destructive',
};

export default function VendorListPage() {
  const { activeOrg } = useAuth();
  const [relationships, setRelationships] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [expandedId, setExpandedId] = useState(null);
  const [notes, setNotes] = useState({});
  const [noteDraft, setNoteDraft] = useState('');

  async function load() {
    setRelationships(await listRelationships(activeOrg.id));
  }

  useEffect(() => {
    if (!activeOrg) return;
    setLoading(true);
    load().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrg?.id]);

  async function handleSearch(e) {
    e.preventDefault();
    if (!query.trim()) return;
    const result = await searchOfferings({ q: query.trim(), pageSize: 5 });
    setResults(result.results || []);
  }

  async function handleAdd(organizationId) {
    try {
      await setRelationshipStatus(activeOrg.id, organizationId, 'POTENTIAL');
      toast.success('Agregado a la Vendor List');
      setResults([]);
      setQuery('');
      await load();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo agregar');
    }
  }

  async function handleStatusChange(supplierOrganizationId, status) {
    try {
      await setRelationshipStatus(activeOrg.id, supplierOrganizationId, status);
      toast.success('Estado actualizado');
      await load();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo actualizar el estado');
    }
  }

  async function handleExpand(relationship) {
    if (expandedId === relationship.id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(relationship.id);
    if (!notes[relationship.id]) {
      const rows = await listNotes(activeOrg.id, relationship.id);
      setNotes((prev) => ({ ...prev, [relationship.id]: rows }));
    }
  }

  async function handleAddNote(relationshipId) {
    if (!noteDraft.trim()) return;
    try {
      await addNote(activeOrg.id, relationshipId, noteDraft.trim());
      setNoteDraft('');
      setNotes((prev) => ({ ...prev, [relationshipId]: undefined }));
      setNotes((prev) => ({ ...prev, [relationshipId]: null }));
      const rows = await listNotes(activeOrg.id, relationshipId);
      setNotes((prev) => ({ ...prev, [relationshipId]: rows }));
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo agregar la nota');
    }
  }

  if (!activeOrg) return null;

  return (
    <div className="space-y-6">
      <Helmet>
        <title>Vendor List · Directorio de Empresas</title>
      </Helmet>

      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Vendor List (AVL)</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Proveedores aprobados o en evaluación por tu organización. Nunca visible para el proveedor.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Agregar proveedor</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <form onSubmit={handleSearch} className="flex gap-2">
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Buscar proveedor por nombre…"
              className="max-w-sm"
            />
            <Button type="submit" variant="outline" className="gap-1.5">
              <Search className="size-4" />
              Buscar
            </Button>
          </form>
          {results.length > 0 && (
            <ul className="space-y-1">
              {results.map((r) => (
                <li
                  key={r.organization_id}
                  className="flex items-center justify-between gap-2 rounded-lg border px-3 py-2 text-sm"
                >
                  <span>{r.trade_name || r.legal_name}</span>
                  <Button size="sm" onClick={() => handleAdd(r.organization_id)}>
                    Agregar
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {loading ? (
        <div className="h-24 animate-pulse rounded-lg bg-secondary" />
      ) : relationships.length === 0 ? (
        <p className="rounded-lg border border-dashed px-4 py-8 text-center text-sm text-muted-foreground">
          Todavía no tienes proveedores en tu Vendor List.
        </p>
      ) : (
        <div className="space-y-3">
          {relationships.map((r) => (
            <Card key={r.id}>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="flex items-center gap-2 text-base">
                  <ShieldCheck className="size-4 text-primary" />
                  Proveedor {String(r.supplier_organization_id).slice(0, 8)}
                </CardTitle>
                <div className="flex items-center gap-2">
                  <Badge variant={STATUS_VARIANT[r.status] || 'outline'}>{r.status}</Badge>
                  <SelectNative
                    value={r.status}
                    onChange={(e) => handleStatusChange(r.supplier_organization_id, e.target.value)}
                    className="w-40"
                  >
                    {STATUSES.map((s) => (
                      <option key={s.value} value={s.value}>
                        {s.label}
                      </option>
                    ))}
                  </SelectNative>
                  <Button variant="ghost" size="sm" className="gap-1.5" onClick={() => handleExpand(r)}>
                    <StickyNote className="size-3.5" />
                    Notas
                  </Button>
                </div>
              </CardHeader>
              {expandedId === r.id && (
                <CardContent className="space-y-2">
                  {(notes[r.id] || []).map((n) => (
                    <p key={n.id} className="rounded-lg bg-secondary/50 px-3 py-2 text-sm">
                      {n.body}
                    </p>
                  ))}
                  <div className="flex gap-2">
                    <Textarea
                      value={noteDraft}
                      onChange={(e) => setNoteDraft(e.target.value)}
                      placeholder="Nueva nota privada…"
                      className="flex-1"
                    />
                    <Button onClick={() => handleAddNote(r.id)}>Agregar</Button>
                  </div>
                </CardContent>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
