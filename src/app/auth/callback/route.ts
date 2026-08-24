import { NextResponse, type NextRequest } from 'next/server'
import { createClient } from '@/lib/supabase/server'

/**
 * Canje del código de Supabase Auth por una sesión.
 *
 * Destino de `emailRedirectTo` en confirmación de correo, recuperación de
 * contraseña y OAuth.
 */
export async function GET(request: NextRequest) {
  const { searchParams, origin } = request.nextUrl
  const code = searchParams.get('code')
  const rawNext = searchParams.get('next')

  // Anti open-redirect: solo rutas internas de un solo slash inicial.
  const next =
    rawNext && rawNext.startsWith('/') && !rawNext.startsWith('//') ? rawNext : '/dashboard'

  if (!code) {
    return NextResponse.redirect(
      `${origin}/login?message=${encodeURIComponent('El enlace no es válido o ya fue utilizado.')}`,
    )
  }

  const supabase = await createClient()
  const { error } = await supabase.auth.exchangeCodeForSession(code)

  if (error) {
    return NextResponse.redirect(
      `${origin}/login?message=${encodeURIComponent('El enlace expiró. Solicita uno nuevo.')}`,
    )
  }

  return NextResponse.redirect(`${origin}${next}`)
}
