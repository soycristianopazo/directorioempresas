import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { CreditCard } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { listPlans, getSubscription } from '@/lib/billingApi';

const STATUS_LABEL = {
  TRIAL: 'Prueba',
  ACTIVE: 'Activo',
  PAST_DUE: 'Pago pendiente',
  CANCELLED: 'Cancelado',
};

export default function SubscriptionPage() {
  const { activeOrg } = useAuth();
  const [plans, setPlans] = useState([]);
  const [subscription, setSubscription] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!activeOrg) return;
    setLoading(true);
    Promise.all([listPlans(activeOrg.id), getSubscription(activeOrg.id)])
      .then(([p, s]) => {
        setPlans(p);
        setSubscription(s);
      })
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrg?.id]);

  if (!activeOrg || loading) {
    return <div className="h-32 animate-pulse rounded-lg bg-secondary" />;
  }

  const currentPlan = plans.find((p) => p.id === subscription?.plan_id);

  return (
    <div className="space-y-6">
      <Helmet>
        <title>Plan y facturación · Directorio de Empresas</title>
      </Helmet>

      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Plan y facturación</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Contacta ventas para cambiar de plan — sin flujo de pago automático en esta versión.
        </p>
      </header>

      <Card>
        <CardHeader className="flex flex-row items-center gap-2">
          <CreditCard className="size-4 text-primary" />
          <CardTitle className="text-base">Plan actual</CardTitle>
        </CardHeader>
        <CardContent>
          {currentPlan ? (
            <div className="flex items-center gap-2">
              <span className="text-lg font-semibold">{currentPlan.name}</span>
              {subscription && (
                <Badge variant={subscription.status === 'ACTIVE' ? 'success' : 'warning'}>
                  {STATUS_LABEL[subscription.status] || subscription.status}
                </Badge>
              )}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Sin plan asignado.</p>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 sm:grid-cols-3">
        {plans.map((p) => (
          <Card key={p.id} className={p.id === subscription?.plan_id ? 'border-primary' : ''}>
            <CardHeader>
              <CardTitle className="text-base">{p.name}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-1">
              <p className="text-2xl font-semibold">
                {p.monthly_price != null ? `${p.monthly_price} ${p.currency_code}/mes` : 'A medida'}
              </p>
              {p.description && <p className="text-sm text-muted-foreground">{p.description}</p>}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
