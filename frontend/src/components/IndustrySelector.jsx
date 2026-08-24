import { useEffect, useState } from 'react';
import { getIndustries } from '@/lib/taxonomyApi';

function flatten(nodes, depth = 0, acc = []) {
  for (const node of nodes) {
    acc.push({ ...node, depth });
    if (node.children?.length) flatten(node.children, depth + 1, acc);
  }
  return acc;
}

/** Selector de industrias (checkbox por nodo, árbol aplanado con indentación).
 * Controlado: `selectedIds` es un array de industry_id, `onChange` recibe el
 * array actualizado completo.
 */
export function IndustrySelector({ selectedIds = [], onChange, className }) {
  const [industries, setIndustries] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getIndustries()
      .then((tree) => setIndustries(flatten(tree)))
      .finally(() => setLoading(false));
  }, []);

  function toggle(id) {
    const set = new Set(selectedIds);
    set.has(id) ? set.delete(id) : set.add(id);
    onChange([...set]);
  }

  if (loading) return <div className="h-24 animate-pulse rounded-lg bg-secondary" />;

  return (
    <div className={className}>
      <ul className="max-h-64 space-y-0.5 overflow-y-auto rounded-lg border p-2">
        {industries.map((node) => (
          <li key={node.id} style={{ paddingLeft: `${node.depth * 16}px` }}>
            <label className="flex items-center gap-2 rounded px-1.5 py-1 text-sm hover:bg-accent">
              <input
                type="checkbox"
                className="size-4"
                checked={selectedIds.includes(node.id)}
                onChange={() => toggle(node.id)}
              />
              {node.name}
            </label>
          </li>
        ))}
      </ul>
    </div>
  );
}
