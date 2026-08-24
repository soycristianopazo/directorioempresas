import * as React from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * <select> nativo estilizado, no Radix Select.
 *
 * Para formularios simples (elegir un rol, un tamaño de empresa) el <select>
 * nativo da autocompletado del navegador, funciona sin JS extra y es más
 * accesible por defecto. Radix Select se reserva para combos que necesiten
 * búsqueda o contenido enriquecido, que este proyecto todavía no tiene.
 */
const SelectNative = React.forwardRef(({ className, children, ...props }, ref) => (
  <div className="relative">
    <select
      ref={ref}
      className={cn(
        'flex h-10 w-full appearance-none rounded-lg border border-input bg-transparent px-3 pr-8 text-sm',
        'disabled:cursor-not-allowed disabled:opacity-50',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        className,
      )}
      {...props}
    >
      {children}
    </select>
    <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 size-4 -translate-y-1/2 opacity-50" />
  </div>
));
SelectNative.displayName = 'SelectNative';

export { SelectNative };
