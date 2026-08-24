import { useEffect, useState } from 'react';
import { Star } from 'lucide-react';
import { cn } from '@/lib/utils';
import { getTaxonomyTree } from '@/lib/taxonomyApi';

function flatten(nodes, depth = 0, acc = []) {
  for (const node of nodes) {
    acc.push({ ...node, depth });
    if (node.children?.length) flatten(node.children, depth + 1, acc);
  }
  return acc;
}

/** Selector de categorías de taxonomía (qué se vende). `selected` es un
 * array de { node_id, is_primary }. Con allowPrimary, un clic en la
 * estrella marca esa categoría como la principal (única).
 */
export function CategorySelector({ selected = [], onChange, allowPrimary = true, className }) {
  const [nodes, setNodes] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getTaxonomyTree()
      .then((tree) => setNodes(flatten(tree)))
      .finally(() => setLoading(false));
  }, []);

  const selectedIds = new Set(selected.map((s) => s.node_id));

  function toggle(nodeId) {
    if (selectedIds.has(nodeId)) {
      onChange(selected.filter((s) => s.node_id !== nodeId));
    } else {
      const isFirst = selected.length === 0;
      onChange([...selected, { node_id: nodeId, is_primary: allowPrimary && isFirst }]);
    }
  }

  function makePrimary(nodeId) {
    onChange(selected.map((s) => ({ ...s, is_primary: s.node_id === nodeId })));
  }

  if (loading) return <div className="h-24 animate-pulse rounded-lg bg-secondary" />;

  return (
    <div className={className}>
      <ul className="max-h-64 space-y-0.5 overflow-y-auto rounded-lg border p-2">
        {nodes.map((node) => {
          const isSelected = selectedIds.has(node.id);
          const isPrimary = selected.find((s) => s.node_id === node.id)?.is_primary;
          return (
            <li key={node.id} style={{ paddingLeft: `${node.depth * 16}px` }}>
              <div className="flex items-center gap-2 rounded px-1.5 py-1 text-sm hover:bg-accent">
                <label className="flex flex-1 items-center gap-2">
                  <input
                    type="checkbox"
                    className="size-4"
                    checked={isSelected}
                    onChange={() => toggle(node.id)}
                  />
                  {node.name}
                </label>
                {allowPrimary && isSelected && (
                  <button
                    type="button"
                    onClick={() => makePrimary(node.id)}
                    title="Marcar como categoría principal"
                    className={cn(
                      'text-muted-foreground hover:text-primary',
                      isPrimary && 'text-primary',
                    )}
                  >
                    <Star className="size-3.5" fill={isPrimary ? 'currentColor' : 'none'} />
                  </button>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
