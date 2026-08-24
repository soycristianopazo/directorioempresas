export default function Loading() {
  return (
    <div className="space-y-6" role="status" aria-label="Cargando">
      <div className="bg-ink-200 dark:bg-ink-800 h-8 w-64 animate-pulse rounded-lg" />
      <div className="bg-ink-100 dark:bg-ink-900 h-40 animate-pulse rounded-[var(--radius-card)]" />
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="bg-ink-100 dark:bg-ink-900 h-48 animate-pulse rounded-[var(--radius-card)]" />
        <div className="bg-ink-100 dark:bg-ink-900 h-48 animate-pulse rounded-[var(--radius-card)]" />
      </div>
    </div>
  )
}
