import Link from 'next/link'
import { Button } from '@/components/ui/button'

export default function NotFound() {
  return (
    <div className="flex min-h-[60dvh] flex-col items-center justify-center gap-4 px-6 text-center">
      <p className="text-brand-600 text-sm font-medium">404</p>
      <h1 className="text-xl font-semibold">No encontramos esta página</h1>
      <p className="text-ink-500 max-w-md text-sm">
        Puede que el enlace esté desactualizado o que no tengas acceso a este recurso.
      </p>
      <Button asChild>
        <Link href="/dashboard">Ir al panel</Link>
      </Button>
    </div>
  )
}
