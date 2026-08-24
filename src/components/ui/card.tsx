import * as React from 'react'
import { cn } from '@/lib/utils'

export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        'border-ink-200 dark:border-ink-800 dark:bg-ink-900 rounded-[var(--radius-card)] border bg-white',
        className,
      )}
      {...props}
    />
  )
}

export function CardHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('border-ink-200 dark:border-ink-800 space-y-1 border-b p-5', className)}
      {...props}
    />
  )
}

export function CardTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h2 className={cn('text-base font-semibold tracking-tight', className)} {...props} />
}

export function CardDescription({
  className,
  ...props
}: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn('text-ink-500 text-sm', className)} {...props} />
}

export function CardContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('p-5', className)} {...props} />
}

export function CardFooter({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        'border-ink-200 dark:border-ink-800 flex items-center gap-2 border-t p-5',
        className,
      )}
      {...props}
    />
  )
}

const badgeTones = {
  neutral: 'bg-ink-100 text-ink-700 dark:bg-ink-800 dark:text-ink-200',
  brand: 'bg-brand-50 text-brand-700 dark:bg-brand-900 dark:text-brand-100',
  success:
    'bg-[color-mix(in_oklch,var(--color-success)_15%,transparent)] text-[var(--color-success)]',
  warning:
    'bg-[color-mix(in_oklch,var(--color-warning)_18%,transparent)] text-[var(--color-warning)]',
  danger: 'bg-[color-mix(in_oklch,var(--color-danger)_14%,transparent)] text-[var(--color-danger)]',
} as const

export function Badge({
  tone = 'neutral',
  className,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { tone?: keyof typeof badgeTones }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
        badgeTones[tone],
        className,
      )}
      {...props}
    />
  )
}

/** Estado vacío. Requisito de las quality gates (§91). */
export function EmptyState({
  title,
  description,
  action,
}: {
  title: string
  description?: string
  action?: React.ReactNode
}) {
  return (
    <div className="border-ink-300 dark:border-ink-700 flex flex-col items-center justify-center gap-2 rounded-[var(--radius-card)] border border-dashed px-6 py-12 text-center">
      <p className="font-medium">{title}</p>
      {description && <p className="text-ink-500 max-w-md text-sm">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}
