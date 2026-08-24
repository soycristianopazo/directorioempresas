import * as React from 'react';
import { cn } from '@/lib/utils';

const Input = React.forwardRef(({ className, type = 'text', ...props }, ref) => (
  <input
    ref={ref}
    type={type}
    className={cn(
      'flex h-10 w-full rounded-lg border border-input bg-transparent px-3 py-2 text-sm',
      'placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50',
      'aria-[invalid=true]:border-destructive',
      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
      className,
    )}
    {...props}
  />
));
Input.displayName = 'Input';

export { Input };
