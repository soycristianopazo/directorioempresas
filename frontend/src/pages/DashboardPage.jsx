import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { ArrowRight, Building2, ShoppingCart, Store } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

const STATUS_LABEL = { DRAFT: 'Borrador', ACTIVE: 'Publicado', SUSPENDED: 'Suspendido', ARCHIVED: 'Archivado' };
const STATUS_VARIANT = { DRAFT: 'warning', ACTIVE: 'success', SUSPENDED: 'destructive', ARCHIVED: 'neutral' };

const ROLE_LABEL = {
  ORG_OWNER: 'Dueño de la cuenta', ORG_ADMIN: 'Administrador', BUYER_MANAGER: 'Jefe de abastecimiento',
  BUYER: 'Comprador', PROCUREMENT_ANALYST: 'Analista de abastecimiento', CONTRACT_MANAGER: 'Administrador de contrato',
  EVALUATOR: 'Evaluador', SUPPLIER_ADMIN: 'Administrador proveedor', SALES: 'Ventas', VIEWER: 'Solo lectura',
};

export default function DashboardPage() {
  const { activeOrg } = useAuth();

  if (!activeOrg) return null;

  const capabilities = activeOrg.capabilities ?? [];
  const roles = activeOrg.role_codes ?? [];
  const isSupplier = capabilities.includes('SUPPLIER');
  const isBuyer = capabilities.includes('BUYER');

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

        {activeOrg.status !== 'ACTIVE' && (
          <Button asChild>
            <Link to="/empresa">
              Completar perfil
              <ArrowRight className="size-4" />
            </Link>
          </Button>
        )}
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Completitud del perfil</CardTitle>
          <CardDescription>
            Un perfil completo aparece en más búsquedas y califica para más oportunidades.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-semibold tabular-nums">{activeOrg.completion_pct}%</span>
            <span className="text-sm text-muted-foreground">completado</span>
          </div>
          <div
            className="h-2 w-full overflow-hidden rounded-full bg-secondary"
            role="progressbar"
            aria-valuenow={activeOrg.completion_pct}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div
              className="h-full rounded-full bg-primary transition-[width]"
              style={{ width: `${activeOrg.completion_pct}%` }}
            />
          </div>
          <p className="text-sm text-muted-foreground">
            El cálculo detallado por secciones —catálogo, cobertura, experiencia y acreditación—
            se activa en las próximas fases.
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
              <NextStep label="Publicar productos y servicios" phase="Próxima fase" />
              <NextStep label="Definir cobertura territorial" phase="Próxima fase" />
              <NextStep label="Iniciar acreditación" phase="Próxima fase" />
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
              <NextStep label="Buscar proveedores" phase="Próxima fase" />
              <NextStep label="Crear tu lista de proveedores" phase="Próxima fase" />
            </CardContent>
          </Card>
        )}
      </section>

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
