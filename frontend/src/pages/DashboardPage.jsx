import { Helmet } from 'react-helmet-async';
import { useAuth } from '@/context/AuthContext';
import { useI18n } from '@/context/I18nContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export default function DashboardPage() {
  const { user, activeOrg, logout } = useAuth();
  const { t } = useI18n();

  return (
    <main className="mx-auto max-w-5xl px-6 py-10">
      <Helmet>
        <title>Panel · Directorio de Empresas</title>
      </Helmet>

      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            {activeOrg?.trade_name ?? activeOrg?.legal_name ?? `Hola, ${user?.first_name ?? ''}`}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {activeOrg ? `Rol: ${activeOrg.role_codes?.join(', ') || 'sin rol'}` : 'Aún no tienes una empresa registrada.'}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={logout}>
          {t('nav.logout')}
        </Button>
      </header>

      <Card className="mt-8">
        <CardHeader>
          <CardTitle>Panel en construcción</CardTitle>
          <CardDescription>
            El resto de la experiencia (empresa, equipo, catálogo, sourcing) llega en las
            siguientes fases del port.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Sesión autenticada contra el backend FastAPI en <code>/api/auth/me</code>.
        </CardContent>
      </Card>
    </main>
  );
}
