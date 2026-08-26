import { Loader2 } from 'lucide-react';

/** Fallback de Suspense mientras se descarga el chunk de una página lazy.
 * Dos variantes: pantalla completa para rutas sin layout persistente
 * (login, onboarding) e "inline" para el Outlet de AppLayout/AdminLayout,
 * donde el sidebar y el header no deben desmontarse durante la carga. */
export function PageFallback({ inline = false }) {
  return (
    <div
      className={
        inline
          ? 'flex min-h-[50vh] items-center justify-center text-muted-foreground'
          : 'flex min-h-dvh items-center justify-center text-muted-foreground'
      }
    >
      <Loader2 className="size-5 animate-spin" />
    </div>
  );
}
