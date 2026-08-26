import { useEffect, useMemo, useState } from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { SelectNative } from '@/components/ui/select-native';
import { getIndustries } from '@/lib/taxonomyApi';

function flatten(nodes, depth = 0, acc = []) {
  for (const node of nodes) {
    acc.push({ ...node, depth });
    if (node.children?.length) flatten(node.children, depth + 1, acc);
  }
  return acc;
}

/** Selector de industrias en cascada (categoría → subcategoría, mismo patrón
 * que AdminDivisionSelector para región → provincia → comuna) — usa el
 * espacio horizontal del recuadro en vez de crecer en un scroll vertical
 * eterno. Las industrias ya elegidas se listan abajo como chips removibles,
 * igual que la cobertura territorial. Controlado: `selectedIds` es un array
 * de industry_id, `onChange` recibe el array actualizado completo.
 */
export function IndustrySelector({ selectedIds = [], onChange, className }) {
  const [tree, setTree] = useState([]);
  const [loading, setLoading] = useState(true);
  const [categoryId, setCategoryId] = useState('');
  const [subcategoryId, setSubcategoryId] = useState('');

  useEffect(() => {
    getIndustries()
      .then(setTree)
      .finally(() => setLoading(false));
  }, []);

  const flat = useMemo(() => flatten(tree), [tree]);
  const nameById = useMemo(() => new Map(flat.map((n) => [n.id, n.name])), [flat]);
  const category = tree.find((n) => n.id === categoryId);
  const subcategories = category?.children ?? [];

  function handleCategoryChange(id) {
    setCategoryId(id);
    setSubcategoryId('');
  }

  function handleAdd() {
    const id = subcategoryId || categoryId;
    if (!id || selectedIds.includes(id)) return;
    onChange([...selectedIds, id]);
    setCategoryId('');
    setSubcategoryId('');
  }

  function handleRemove(id) {
    onChange(selectedIds.filter((existing) => existing !== id));
  }

  if (loading) return <div className="h-24 animate-pulse rounded-lg bg-secondary" />;

  return (
    <div className={className}>
      <div className="flex flex-wrap items-end gap-2">
        <SelectNative value={categoryId} onChange={(e) => handleCategoryChange(e.target.value)}>
          <option value="">Industria</option>
          {tree.map((node) => (
            <option key={node.id} value={node.id}>
              {node.name}
            </option>
          ))}
        </SelectNative>
        {subcategories.length > 0 && (
          <SelectNative value={subcategoryId} onChange={(e) => setSubcategoryId(e.target.value)}>
            <option value="">Subcategoría (opcional)</option>
            {subcategories.map((node) => (
              <option key={node.id} value={node.id}>
                {node.name}
              </option>
            ))}
          </SelectNative>
        )}
        <Button type="button" variant="outline" size="sm" disabled={!categoryId} onClick={handleAdd} className="gap-1.5">
          <Plus className="size-3.5" />
          Agregar
        </Button>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {selectedIds.map((id) => (
          <Badge key={id} variant="neutral" className="gap-1.5">
            {nameById.get(id) ?? id}
            <button type="button" onClick={() => handleRemove(id)} aria-label="Quitar">
              <Trash2 className="size-3" />
            </button>
          </Badge>
        ))}
        {selectedIds.length === 0 && (
          <p className="text-sm text-muted-foreground">Todavía no hay industrias declaradas.</p>
        )}
      </div>
    </div>
  );
}
