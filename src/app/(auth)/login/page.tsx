import type { Metadata } from 'next'
import Link from 'next/link'
import { LoginForm } from './login-form'

export const metadata: Metadata = { title: 'Iniciar sesión' }

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string; message?: string }>
}) {
  const params = await searchParams

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Iniciar sesión</h1>
        <p className="text-ink-500 text-sm">Accede a tu cuenta para continuar.</p>
      </div>

      {params.message && (
        <p
          role="status"
          className="border-ink-200 bg-ink-50 dark:border-ink-800 dark:bg-ink-900 rounded-lg border px-3 py-2 text-sm"
        >
          {params.message}
        </p>
      )}

      <LoginForm nextPath={params.next ?? '/dashboard'} />

      <div className="text-ink-500 space-y-2 text-sm">
        <p>
          ¿No tienes cuenta?{' '}
          <Link href="/register" className="text-brand-600 font-medium hover:underline">
            Crear cuenta
          </Link>
        </p>
        <p>
          <Link href="/forgot-password" className="hover:underline">
            Olvidé mi contraseña
          </Link>
        </p>
      </div>
    </div>
  )
}
