import { cn } from '@/lib/utils';

/** Barra de completitud de perfil (organizations.completion_pct, calculado
 * por app.compute_completion_pct — ver backend/alembic/sql/0027_completion_pct.sql).
 */
export function ProfileCompletion({ pct = 0, className }) {
  const value = Math.max(0, Math.min(100, pct));

  return (
    <div className={cn('space-y-1.5', className)}>
      <div className="flex items-baseline justify-between text-sm">
        <span className="font-medium">Completitud del perfil</span>
        <span className="text-muted-foreground">{value}%</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-secondary">
        <div
          className="h-full rounded-full bg-primary transition-all"
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
}
