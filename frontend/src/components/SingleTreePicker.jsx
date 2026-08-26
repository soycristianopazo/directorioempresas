import { useEffect, useMemo, useState } from 'react';
import { SelectNative } from '@/components/ui/select-native';

function flatten(nodes, depth = 0, acc = []) {
  for (const node of nodes) {
    acc.push({ ...node, depth });
    if (node.children?.length) flatten(node.children, depth + 1, acc);
  }
  return acc;
}

/** Selector en cascada categoría → subcategoría de UN solo valor — dos
 * `<select>` angostos en vez de un árbol de checkboxes que crece hacia abajo
 * sin límite. Sirve tanto para taxonomía de producto (`getTaxonomyTree`)
 * como para industrias (`getIndustries`), cualquier árbol de 2 niveles.
 */
export function SingleTreePicker({ loader, value, onChange, placeholder, subPlaceholder }) {
  const [tree, setTree] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loader().then(setTree).finally(() => setLoading(false));
  }, [loader]);

  const flat = useMemo(() => flatten(tree), [tree]);
  const selectedNode = flat.find((n) => n.id === value);
  const topId = useMemo(() => {
    if (!selectedNode) return '';
    let node = selectedNode;
    while (node.parent_id && flat.find((n) => n.id === node.parent_id)) {
      node = flat.find((n) => n.id === node.parent_id);
    }
    return node.id;
  }, [selectedNode, flat]);
  const top = tree.find((n) => n.id === topId);
  const children = top?.children ?? [];

  if (loading) return <div className="h-10 animate-pulse rounded-lg bg-secondary" />;

  return (
    <div className="flex flex-wrap gap-2">
      <SelectNative value={topId} onChange={(e) => onChange(e.target.value || null)}>
        <option value="">{placeholder}</option>
        {tree.map((node) => (
          <option key={node.id} value={node.id}>
            {node.name}
          </option>
        ))}
      </SelectNative>
      {children.length > 0 && (
        <SelectNative
          value={value && children.some((c) => c.id === value) ? value : ''}
          onChange={(e) => onChange(e.target.value || topId)}
        >
          <option value="">{subPlaceholder}</option>
          {children.map((node) => (
            <option key={node.id} value={node.id}>
              {node.name}
            </option>
          ))}
        </SelectNative>
      )}
    </div>
  );
}
