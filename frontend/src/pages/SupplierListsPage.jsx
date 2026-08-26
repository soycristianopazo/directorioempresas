import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { toast } from 'sonner';
import { List, Plus, Trash2 } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import {
  listSupplierLists,
  createSupplierList,
  deleteSupplierList,
  listSupplierListItems,
  removeSupplierListItem,
} from '@/lib/supplierListsApi';

export default function SupplierListsPage() {
  const { activeOrg } = useAuth();
  const [lists, setLists] = useState([]);
  const [items, setItems] = useState({});
  const [loading, setLoading] = useState(true);
  const [newName, setNewName] = useState('');

  async function load() {
    try {
      const rows = await listSupplierLists(activeOrg.id);
      setLists(rows);
      const entries = await Promise.all(
        rows.map(async (l) => [l.id, await listSupplierListItems(activeOrg.id, l.id)]),
      );
      setItems(Object.fromEntries(entries));
    } catch (error) {
      toast.error(
        error.response?.data?.detail || 'No se pudieron cargar las listas de proveedores',
      );
    }
  }

  useEffect(() => {
    if (!activeOrg) return;
    setLoading(true);
    load().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrg?.id]);

  async function handleCreate(e) {
    e.preventDefault();
    if (!newName.trim()) return;
    try {
      await createSupplierList(activeOrg.id, { name: newName.trim() });
      setNewName('');
      toast.success('Lista creada');
      await load();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo crear');
    }
  }

  async function handleDeleteList(listId) {
    try {
      await deleteSupplierList(activeOrg.id, listId);
      await load();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo eliminar');
    }
  }

  async function handleRemoveItem(listId, itemId) {
    try {
      await removeSupplierListItem(activeOrg.id, listId, itemId);
      await load();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo quitar');
    }
  }

  if (!activeOrg) return null;

  return (
    <div className="space-y-6">
      <Helmet>
        <title>Listas de proveedores · Directorio de Empresas</title>
      </Helmet>

      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Listas de proveedores</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Guarda proveedores desde la búsqueda para encontrarlos rápido después.
        </p>
      </header>

      <form onSubmit={handleCreate} className="flex gap-2">
        <Input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="Ej. Transportistas Antofagasta" className="max-w-sm" />
        <Button type="submit" className="gap-1.5">
          <Plus className="size-4" />
          Nueva lista
        </Button>
      </form>

      {loading ? (
        <div className="h-32 animate-pulse rounded-lg bg-secondary" />
      ) : lists.length === 0 ? (
        <p className="rounded-lg border border-dashed px-4 py-8 text-center text-sm text-muted-foreground">
          Todavía no tienes listas guardadas. Guarda proveedores desde{' '}
          <a href="/buscar" className="text-primary hover:underline">Buscar proveedores</a>.
        </p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {lists.map((l) => (
            <Card key={l.id}>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="flex items-center gap-2 text-base">
                  <List className="size-4 text-primary" />
                  {l.name}
                </CardTitle>
                <Button variant="ghost" size="sm" onClick={() => handleDeleteList(l.id)}>
                  <Trash2 className="size-3.5" />
                </Button>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {(items[l.id] ?? []).map((item) => (
                    <li key={item.id} className="flex items-center justify-between gap-2 rounded-lg border px-3 py-2 text-sm">
                      <a href={`/proveedores/${item.slug}`} target="_blank" rel="noreferrer" className="font-medium hover:underline">
                        {item.trade_name || item.legal_name}
                      </a>
                      <Button variant="ghost" size="sm" onClick={() => handleRemoveItem(l.id, item.id)}>
                        <Trash2 className="size-3.5" />
                      </Button>
                    </li>
                  ))}
                  {(items[l.id] ?? []).length === 0 && (
                    <p className="text-sm text-muted-foreground">Sin proveedores guardados todavía.</p>
                  )}
                </ul>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
