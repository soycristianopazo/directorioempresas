import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

/** Combina clases resolviendo conflictos de Tailwind. Base de todo componente shadcn/ui. */
export function cn(...inputs) {
  return twMerge(clsx(inputs));
}
