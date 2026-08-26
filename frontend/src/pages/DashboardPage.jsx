import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { ArrowRight, BadgeCheck, BarChart3, Building2, ClipboardCheck, ShoppingCart, Store } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ProfileCompletion } from '@/components/ProfileCompletion';
import { cn } from '@/lib/utils';
import { getBuyerSummary, getSupplierSummary } from '@/lib/analyticsApi';
import { listMyPendingApprovals } from '@/lib/awardsApi';
import { listEnrollments } from '@/lib/accreditationApi';
import { ROLE_LABEL } from '@/lib/roleLabels';

const STATUS_LABEL = { DRAFT: 'Borrador', ACTIVE: 'Publicado', SUSPENDED: 'Suspendido', ARCHIVED: 'Archivado' };
const STATUS_VARIANT = { DRAFT: 'warning', ACTIVE: 'success', SUSPENDED: 'destructive', ARCHIVED: 'neutral' };

export default function DashboardPage() {
  const { activeOrg } = useAuth();
  const [analytics, setAnalytics] = useState(null);
  const [pendingApprovals, setPendingApprovals] = useState(0);
  const [platformAccreditation, setPlatformAccreditation] = useState(null);

  const capabilities = activeOrg?.capabilities ?? [];
  const isSupplier = capabilities.includes('SUPPLIER');
  const isBuyer = capabilities.includes('BUYER');

  useEffect(() => {
    if (!activeOrg) return;
    // Las tres llamadas son independientes entre sí (analítica, aprobaciones
    // pendientes, acreditación) — antes se esperaban una tras otra con
    // `await` secuencial, así que el panel tardaba la suma de las tres
    // latencias en vez de la mayor. Se disparan todas de una y cada una
    // resuelve su propio estado sin bloquear a las demás.
    let cancelled = false;

    const analyticsPromise = isBuyer
      ? getBuyerSummary(activeOrg.id)
      : isSupplier
        ? getSupplierSummary(activeOrg.id)
        : Promise.resolve(null);
    const approvalsPromise = isBuyer ? listMyPendingApprovals(activeOrg.id) : Promise.resolve(null);
    const enrollmentsPromise = isSupplier ? listEnrollments(activeOrg.id) : Promise.resolve(null);

    analyticsPromise
      .then((data) => {
        if (!cancelled) setAnalytics(data);
      })
      .catch(() => {
        if (!cancelled) setAnalytics(null);
      });

    approvalsPromise
      .then((approvals) => {
        if (cancelled || approvals == null) return;
        setPendingApprovals(approvals.filter((a) => a.status === 'PENDING').length);
      })
      .catch(() => {
        if (!cancelled) setPendingApprovals(0);
      });

    enrollmentsPromise
      .then((enrollments) => {
        if (cancelled || enrollments == null) return;
        setPlatformAccreditation(
          enrollments.find((e) => e.program_owner_scope === 'PLATFORM' && e.status === 'ACCREDITED') ?? null,
        );
      })
      .catch(() => {
        if (!cancelled) setPlatformAccreditation(null);
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrg?.id, isBuyer, isSupplier]);

  if (!activeOrg) return null;

  const roles = activeOrg.role_codes ?? [];

  return (
    <div className="space-y-8">
      <Helmet>
        <title>Panel · Directorio de Empresas</title>
      </Helmet>

      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            {activeOrg.trade_name ?? activeOrg.legal_name}
          </h1>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <Badge variant={STATUS_VARIANT[activeOrg.status] ?? 'neutral'}>
              {STATUS_LABEL[activeOrg.status] ?? activeOrg.status}
            </Badge>
            {capabilities.map((c) => (
              <Badge key={c} variant="brand">
                <span className="flex items-center gap-1">
                  {c === 'BUYER' ? <ShoppingCart className="size-3" /> : <Store className="size-3" />}
                  {c === 'BUYER' ? 'Comprador' : 'Proveedor'}
                </span>
              </Badge>
            ))}
            <span className="text-xs text-muted-foreground">
              Tu rol: {roles.map((r) => ROLE_LABEL[r] ?? r).join(', ') || 'sin rol asignado'}
            </span>
          </div>
        </div>

        {activeOrg.completion_pct < 100 && (
          <Button asChild>
            <Link to={isSupplier ? '/onboarding/2' : '/empresa'}>
              Continuar completando el perfil
              <ArrowRight className="size-4" />
            </Link>
          </Button>
        )}
      </header>

      {platformAccreditation && (
        <Card className="border-emerald-300 bg-emerald-50 dark:border-emerald-900 dark:bg-emerald-950/20">
          <CardContent className="flex flex-wrap items-center justify-between gap-3 pt-6">
            <p className="flex items-center gap-2 text-sm font-medium text-emerald-700 dark:text-emerald-400">
              <BadgeCheck className="size-4" />
              Acreditado como proveedor del Directorio de Empresas
              {platformAccreditation.valid_until && (
                <span className="font-normal text-emerald-700/80 dark:text-emerald-400/80">
                  · vigente hasta {new Date(platformAccreditation.valid_until).toLocaleDateString('es-CL')}
                </span>
              )}
            </p>
            <Link to={`/empresa/acreditacion/${platformAccreditation.id}/certificado`}>
              <Button size="sm" variant="outline">
                Ver certificado
              </Button>
            </Link>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Completitud del perfil</CardTitle>
          <CardDescription>
            Un perfil completo aparece en más búsquedas y califica para más oportunidades.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <ProfileCompletion pct={activeOrg.completion_pct} />
          <p className="text-sm text-muted-foreground">
            Suma ubicaciones, cobertura, catálogo publicado y credenciales para subir el porcentaje.
          </p>
        </CardContent>
      </Card>

      <section className="grid gap-4 sm:grid-cols-2">
        {isSupplier && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Store className="size-4 text-primary" />
                Como proveedor
              </CardTitle>
              <CardDescription>Haz que te encuentren.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-1 text-sm">
              <NextStep label="Completar datos de la empresa" to="/empresa" />
              <NextStep label="Publicar productos y servicios" to="/empresa/catalogo" />
              <NextStep label="Definir cobertura territorial" to="/empresa/cobertura" />
              <NextStep label="Certificaciones y casos de éxito" to="/empresa/credenciales" />
              <NextStep label="Iniciar acreditación" to="/empresa/acreditacion" />
            </CardContent>
          </Card>
        )}

        {isBuyer && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ShoppingCart className="size-4 text-primary" />
                Como comprador
              </CardTitle>
              <CardDescription>Encuentra y compara proveedores.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-1 text-sm">
              <NextStep label="Invitar a tu equipo" to="/empresa/equipo" />
              <NextStep label="Buscar proveedores" to="/buscar" />
              <NextStep label="Crear tu lista de proveedores" to="/empresa/listas" />
              <NextStep label="Publicar una necesidad de compra" to="/empresa/sourcing" />
            </CardContent>
          </Card>
        )}
      </section>

      {isBuyer && pendingApprovals > 0 && (
        <Card className="border-amber-300 bg-amber-50 dark:bg-amber-950/20">
          <CardContent className="flex items-center justify-between pt-6">
            <p className="flex items-center gap-2 text-sm font-medium">
              <ClipboardCheck className="size-4" />
              Aprobaciones pendientes: {pendingApprovals}
            </p>
            <Link to="/empresa/aprobaciones">
              <Button size="sm" variant="outline">
                Ver
              </Button>
            </Link>
          </CardContent>
        </Card>
      )}

      {analytics && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="size-4 text-primary" />
              Actividad de hoy
            </CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2">
            {Object.entries(analytics.today).map(([key, value]) => (
              <div key={key}>
                <dt className="text-xs text-muted-foreground">{key.replaceAll('_', ' ')}</dt>
                <dd className="mt-0.5 text-2xl font-semibold">{value}</dd>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building2 className="size-4 text-primary" />
            Identificación
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-3">
          <div>
            <dt className="text-xs text-muted-foreground">Razón social</dt>
            <dd className="mt-0.5 text-sm font-medium">{activeOrg.legal_name}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">URL del perfil</dt>
            <dd className="mt-0.5 text-sm font-medium">/proveedores/{activeOrg.slug}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Visibilidad</dt>
            <dd className="mt-0.5 text-sm font-medium">{activeOrg.visibility}</dd>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function NextStep({ label, to, phase }) {
  const bullet = <span aria-hidden className="size-4 shrink-0 rounded-full border-2 border-muted-foreground/40" />;

  if (!to) {
    return (
      <div className="flex items-center gap-2 px-2 py-1.5 text-muted-foreground">
        {bullet}
        <span>{label}</span>
        {phase && <Badge className="ml-auto">{phase}</Badge>}
      </div>
    );
  }

  return (
    <Link to={to} className={cn('flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-accent')}>
      {bullet}
      <span>{label}</span>
    </Link>
  );
}
