import { useState } from 'react';
import { X } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';

/** Input de hashtags libres: Enter o coma agrega, click en × quita.
 * Controlado: `tags` es un array de strings, `onChange` recibe el array
 * actualizado completo — mismo contrato que IndustrySelector/CategorySelector.
 */
export function TagInput({ tags = [], onChange, max = 15, className }) {
  const [draft, setDraft] = useState('');

  function commit() {
    const value = draft.trim().replace(/^#/, '').toLowerCase();
    setDraft('');
    if (!value || tags.includes(value) || tags.length >= max) return;
    onChange([...tags, value]);
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      commit();
    } else if (e.key === 'Backspace' && !draft && tags.length > 0) {
      onChange(tags.slice(0, -1));
    }
  }

  function remove(tag) {
    onChange(tags.filter((t) => t !== tag));
  }

  return (
    <div className={cn('space-y-2', className)}>
      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {tags.map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center gap-1.5 rounded-full bg-secondary px-2.5 py-1 text-xs font-medium"
            >
              #{tag}
              <button
                type="button"
                onClick={() => remove(tag)}
                className="text-muted-foreground hover:text-foreground"
                aria-label={`Quitar hashtag ${tag}`}
              >
                <X className="size-3" />
              </button>
            </span>
          ))}
        </div>
      )}
      <Input
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={commit}
        placeholder={tags.length >= max ? `Máximo ${max} hashtags` : 'Escribe y presiona Enter…'}
        disabled={tags.length >= max}
      />
    </div>
  );
}
