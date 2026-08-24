import type { Metadata } from 'next'
import Link from 'next/link'
import { ForgotPasswordForm } from './forgot-password-form'

export const metadata: Metadata = { title: 'Recuperar contraseña' }

export default function ForgotPasswordPage() {
  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Recuperar contraseña</h1>
        <p className="text-ink-500 text-sm">
          Te enviaremos un enlace para definir una contraseña nueva.
        </p>
      </div>

      <ForgotPasswordForm />

      <p className="text-ink-500 text-sm">
        <Link href="/login" className="hover:underline">
          Volver a iniciar sesión
        </Link>
      </p>
    </div>
  )
}
