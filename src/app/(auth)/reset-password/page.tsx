import type { Metadata } from 'next'
import { ResetPasswordForm } from './reset-password-form'

export const metadata: Metadata = { title: 'Nueva contraseña' }

export default function ResetPasswordPage() {
  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Nueva contraseña</h1>
        <p className="text-ink-500 text-sm">Define la contraseña con la que ingresarás.</p>
      </div>

      <ResetPasswordForm />
    </div>
  )
}
