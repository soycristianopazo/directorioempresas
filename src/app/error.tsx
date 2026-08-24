'use client'

import { useEffect } from 'react'
import { Button } from '@/components/ui/button'

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error('[app] error no controlado', error)
  }, [error])

  return (
    <div className="flex min-h-[60dvh] flex-col items-center justify-center gap-4 px-6 text-center">
      <h1 className="text-xl font-semibold">Algo salió mal</h1>
      <p className="text-ink-500 max-w-md text-sm">
        Ocurrió un error inesperado. Puedes reintentar; si persiste, contáctanos indicando el código{' '}
        {error.digest ? <code className="font-mono">{error.digest}</code> : 'del error'}.
      </p>
      <Button onClick={reset}>Reintentar</Button>
    </div>
  )
}
