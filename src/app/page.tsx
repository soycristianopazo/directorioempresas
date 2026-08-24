import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { getSessionContext } from '@/server/auth/context'

export default async function HomePage() {
  const session = await getSessionContext()

  return (
    <main className="mx-auto flex min-h-dvh max-w-5xl flex-col px-6">
      <header className="flex items-center justify-between py-6">
        <span className="font-semibold tracking-tight">Directorio de Empresas</span>
        <nav className="flex items-center gap-2">
          {session ? (
            <Button asChild size="sm">
              <Link href="/dashboard">Ir al panel</Link>
            </Button>
          ) : (
            <>
              <Button asChild variant="ghost" size="sm">
                <Link href="/login">Iniciar sesión</Link>
              </Button>
              <Button asChild size="sm">
                <Link href="/register">Crear cuenta</Link>
              </Button>
            </>
          )}
        </nav>
      </header>

      <section className="flex flex-1 flex-col justify-center py-16">
        <p className="text-brand-600 text-sm font-medium">Abastecimiento B2B</p>
        <h1 className="mt-3 max-w-3xl text-4xl font-semibold tracking-tight text-balance sm:text-5xl">
          Encuentra proveedores confiables. Cotiza, compara y adjudica en un solo lugar.
        </h1>
        <p className="text-ink-500 mt-5 max-w-2xl text-lg">
          Un ecosistema de empresas verificadas donde el proveedor gana visibilidad y el comprador
          gana tiempo.
        </p>

        <div className="mt-8 flex flex-wrap gap-3">
          <Button asChild size="lg">
            <Link href="/register">Registrar mi empresa</Link>
          </Button>
          <Button asChild size="lg" variant="outline">
            <Link href="/login">Ya tengo cuenta</Link>
          </Button>
        </div>

        <dl className="border-ink-200 dark:border-ink-800 mt-16 grid gap-8 border-t pt-8 sm:grid-cols-2">
          <div>
            <dt className="font-medium">Para el proveedor</dt>
            <dd className="text-ink-500 mt-1 text-sm">
              Publica tu catálogo una vez y aparece cuando alguien busca exactamente lo que vendes.
              Tu documentación vive en un solo lugar y sirve para todos los compradores.
            </dd>
          </div>
          <div>
            <dt className="font-medium">Para el comprador</dt>
            <dd className="text-ink-500 mt-1 text-sm">
              Filtra por categoría, territorio, certificaciones y capacidad real. Invita, recibe
              cotizaciones estructuradas y compáralas con criterios ponderados.
            </dd>
          </div>
        </dl>
      </section>

      <footer className="border-ink-200 text-ink-500 dark:border-ink-800 border-t py-6 text-sm">
        © {new Date().getFullYear()} Directorio de Empresas
      </footer>
    </main>
  )
}
