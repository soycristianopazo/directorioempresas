import { useEffect, useRef, useState } from 'react';
import { Search, X } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { searchSiiEconomicActivities } from '@/lib/referenceApi';
import { cn } from '@/lib/utils';

/** Buscador de giros SII (código de actividad económica) — 674 filas, demasiadas
 * para un checkbox list como IndustrySelector, así que busca en el servidor
 * por código o texto libre. Controlado: `selected` es un array de
 * {sii_code, description}, `onSelect(activity)`/`onRemove(siiCode)`.
 */
export function SiiActivitySelector({ selected = [], onSelect, onRemove, className }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    const q = query.trim();
    if (q.length < 1) {
      setResults([]);
      return;
    }
    setLoading(true);
    const timer = setTimeout(() => {
      searchSiiEconomicActivities(q)
        .then((rows) => setResults(rows))
        .catch(() => setResults([]))
        .finally(() => setLoading(false));
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    function onClickOutside(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, []);

  const selectedCodes = new Set(selected.map((s) => s.sii_code));

  function handlePick(activity) {
    onSelect(activity);
    setQuery('');
    setResults([]);
    setOpen(false);
  }

  return (
    <div className={cn('space-y-2', className)} ref={containerRef}>
      {selected.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {selected.map((s) => (
            <span
              key={s.sii_code}
              className="inline-flex items-center gap-1.5 rounded-full bg-secondary px-2.5 py-1 text-xs font-medium"
            >
              <span className="text-muted-foreground">{s.sii_code}</span>
              {s.description}
              <button
                type="button"
                onClick={() => onRemove(s.sii_code)}
                className="text-muted-foreground hover:text-foreground"
                aria-label={`Quitar giro ${s.sii_code}`}
              >
                <X className="size-3" />
              </button>
            </span>
          ))}
        </div>
      )}

      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setOpen(true)}
          placeholder="Busca por código (ej. 620200) o texto (ej. consultoría)…"
          className="pl-9"
        />

        {open && query.trim().length > 0 && (
          <div className="absolute z-10 mt-1 max-h-72 w-full overflow-y-auto rounded-lg border bg-popover shadow-md">
            {loading ? (
              <p className="px-3 py-2 text-sm text-muted-foreground">Buscando…</p>
            ) : results.length === 0 ? (
              <p className="px-3 py-2 text-sm text-muted-foreground">Sin resultados.</p>
            ) : (
              results.map((r) => (
                <button
                  key={r.code}
                  type="button"
                  disabled={selectedCodes.has(r.code)}
                  onClick={() => handlePick({ sii_code: r.code, description: r.description })}
                  className="flex w-full flex-col items-start gap-0.5 px-3 py-2 text-left text-sm hover:bg-accent disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <span className="font-medium">
                    {r.code} · {r.description}
                  </span>
                  <span className="text-xs text-muted-foreground">{r.sector}</span>
                </button>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}
