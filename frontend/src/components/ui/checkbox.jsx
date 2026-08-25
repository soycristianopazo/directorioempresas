import * as React from 'react';
import { Check } from 'lucide-react';
import { cn } from '@/lib/utils';

/** Checkbox nativo estilizado (sin @radix-ui/react-checkbox, no está entre
 * las dependencias del proyecto) — misma API que el resto de los primitives
 * shadcn-style usados acá: `checked`/`onCheckedChange`/`disabled`. */
const Checkbox = React.forwardRef(({ className, checked, onCheckedChange, disabled, ...props }, ref) => (
  <span className="relative inline-flex">
    <input
      ref={ref}
      type="checkbox"
      checked={!!checked}
      disabled={disabled}
      onChange={(e) => onCheckedChange?.(e.target.checked)}
      className={cn(
        'peer size-4 shrink-0 cursor-pointer appearance-none rounded-sm border border-primary shadow',
        'checked:bg-primary disabled:cursor-not-allowed disabled:opacity-50',
        'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring',
        className,
      )}
      {...props}
    />
    <Check className="pointer-events-none absolute left-0 top-0 size-4 scale-0 text-primary-foreground peer-checked:scale-100" />
  </span>
));
Checkbox.displayName = 'Checkbox';

export { Checkbox };
