import { Check, Circle } from 'lucide-react';
import { cn } from '@/lib/utils';

/** Completitud de una publicación del catálogo
 * (supplier_offerings.completion_pct, calculado por
 * app.compute_offering_completion_pct — ver
 * backend/alembic/sql/0091_offering_completion_pct.sql). `pct` es el número
 * ya calculado en el servidor (fuente de verdad); `items` es la lista de
 * chequeo que arma cada página a partir de los datos que ya tiene cargados,
 * con los mismos siete puntos que pesa la función SQL — no hay endpoint
 * aparte para el desglose. Cada item pendiente es un botón que hace scroll
 * a su sección (`anchor`, el id de la Card correspondiente).
 */
export function OfferingCompletion({ pct = 0, items = [], className }) {
  const value = Math.max(0, Math.min(100, pct));
  const missing = items.filter((item) => !item.done);

  function jumpTo(anchor) {
    document.getElementById(anchor)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  return (
    <div className={cn('space-y-3 rounded-lg border bg-secondary/30 p-4', className)}>
      <div className="flex items-baseline justify-between text-sm">
        <span className="font-medium">Completitud de la publicación</span>
        <span className="text-muted-foreground">{value}%</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-secondary">
        <div
          className="h-full rounded-full bg-primary transition-all"
          style={{ width: `${value}%` }}
        />
      </div>
      {missing.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {missing.map((item) => (
            <button
              key={item.label}
              type="button"
              onClick={() => jumpTo(item.anchor)}
              className="inline-flex items-center gap-1.5 rounded-full border border-dashed px-2.5 py-1 text-xs text-muted-foreground transition-colors hover:border-primary hover:text-primary"
            >
              <Circle className="size-3" />
              {item.label}
            </button>
          ))}
        </div>
      ) : (
        <p className="flex items-center gap-1.5 text-xs font-medium text-primary">
          <Check className="size-3.5" />
          Publicación completa
        </p>
      )}
    </div>
  );
}

/** Barra compacta para filas de lista (CatalogPage) — sin checklist, solo el
 * número, con un tinte de color cuando está baja para que salte a la vista. */
export function OfferingCompletionBadge({ pct = 0, className }) {
  const value = Math.max(0, Math.min(100, pct));
  const low = value < 50;

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 text-xs font-medium',
        low ? 'text-muted-foreground' : 'text-primary',
        className,
      )}
    >
      <span className="h-1.5 w-10 overflow-hidden rounded-full bg-secondary">
        <span
          className={cn('block h-full rounded-full', low ? 'bg-muted-foreground/50' : 'bg-primary')}
          style={{ width: `${value}%` }}
        />
      </span>
      {value}%
    </span>
  );
}
