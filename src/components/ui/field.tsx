import * as React from 'react'
import { cn } from '@/lib/utils'

export function Input({ className, ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        'border-ink-300 h-10 w-full rounded-lg border bg-transparent px-3 text-sm',
        'placeholder:text-ink-400 disabled:cursor-not-allowed disabled:opacity-50',
        'aria-invalid:border-[var(--color-danger)]',
        className,
      )}
      {...props}
    />
  )
}

export function Textarea({
  className,
  ...props
}: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        'border-ink-300 min-h-24 w-full rounded-lg border bg-transparent px-3 py-2 text-sm',
        'placeholder:text-ink-400 disabled:cursor-not-allowed disabled:opacity-50',
        'aria-invalid:border-[var(--color-danger)]',
        className,
      )}
      {...props}
    />
  )
}

export function Select({ className, ...props }: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        'border-ink-300 h-10 w-full rounded-lg border bg-transparent px-3 text-sm',
        'disabled:cursor-not-allowed disabled:opacity-50',
        className,
      )}
      {...props}
    />
  )
}

export function Label({ className, ...props }: React.LabelHTMLAttributes<HTMLLabelElement>) {
  return <label className={cn('text-ink-700 text-sm font-medium', className)} {...props} />
}

interface FieldProps {
  label: string
  htmlFor: string
  hint?: string
  error?: string | undefined
  required?: boolean
  children: React.ReactNode
}

/** Campo de formulario con etiqueta, ayuda y error accesibles. */
export function Field({ label, htmlFor, hint, error, required, children }: FieldProps) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={htmlFor}>
        {label}
        {required && (
          <span className="ml-0.5 text-[var(--color-danger)]" aria-hidden>
            *
          </span>
        )}
      </Label>
      {children}
      {hint && !error && <p className="text-ink-500 text-xs">{hint}</p>}
      {error && (
        <p role="alert" className="text-xs text-[var(--color-danger)]">
          {error}
        </p>
      )}
    </div>
  )
}
