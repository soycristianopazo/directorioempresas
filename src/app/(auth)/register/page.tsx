import type { Metadata } from 'next'
import Link from 'next/link'
import { RegisterForm } from './register-form'

export const metadata: Metadata = { title: 'Crear cuenta' }

export default function RegisterPage() {
  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Crear cuenta</h1>
        <p className="text-ink-500 text-sm">
          Primero tu cuenta personal. En el siguiente paso registras tu empresa.
        </p>
      </div>

      <RegisterForm />

      <p className="text-ink-500 text-sm">
        ¿Ya tienes cuenta?{' '}
        <Link href="/login" className="text-brand-600 font-medium hover:underline">
          Iniciar sesión
        </Link>
      </p>
    </div>
  )
}
