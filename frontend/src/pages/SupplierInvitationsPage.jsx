import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { FileSearch, Inbox, ShieldCheck } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  acceptNda,
  confirmParticipation,
  declineInvitation,
  expressInterest,
  getInvitation,
  listMyInvitations,
  withdrawInvitation,
} from '@/lib/invitationsApi';

const STATUS_LABELS = {
  INVITED: 'Invitado',
  VIEWED: 'Vista',
  NDA_ACCEPTED: 'NDA aceptado',
  INTERESTED: 'Interesado',
  PARTICIPATING: 'Participando',
  QUOTED: 'Cotización enviada',
  DECLINED: 'Declinado',
  NO_RESPONSE: 'Sin respuesta',
  WITHDRAWN: 'Retirado',
  DISQUALIFIED: 'Descalificado',
  EXPIRED: 'Expirado',
};

const STATUS_VARIANT = {
  INVITED: 'neutral',
  VIEWED: 'neutral',
  NDA_ACCEPTED: 'brand',
  INTERESTED: 'brand',
  PARTICIPATING: 'success',
  QUOTED: 'success',
  DECLINED: 'destructive',
  WITHDRAWN: 'destructive',
  DISQUALIFIED: 'destructive',
  NO_RESPONSE: 'warning',
  EXPIRED: 'warning',
};

// Refleja public.sourcing_event_invitation_transitions (alembic/sql/0044) —
// solo para decidir qué botones mostrar. La validación real la hace el
// backend; si el estado cambió entre medio, el toast del error manda.
function actionsForStatus(status, requiresNda) {
  if (status === 'VIEWED') {
    return requiresNda ? ['ACCEPT_NDA', 'DECLINE'] : ['EXPRESS_INTEREST', 'DECLINE'];
  }
  if (status === 'NDA_ACCEPTED') return ['EXPRESS_INTEREST', 'DECLINE'];
  if (status === 'INTERESTED') return ['CONFIRM_PARTICIPATION', 'DECLINE'];
  if (status === 'PARTICIPATING' || status === 'QUOTED') return ['WITHDRAW'];
  return [];
}

function formatDateTime(value) {
  if (!value) return '—';
  return new Intl.DateTimeFormat('es-CL', { dateStyle: 'medium', timeStyle: 'short' }).format(
    new Date(value),
  );
}

export default function SupplierInvitationsPage() {
  const { activeOrg } = useAuth();
  const [invitations, setInvitations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedMeta, setSelectedMeta] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [busy, setBusy] = useState(false);

  async function loadList() {
    setInvitations(await listMyInvitations(activeOrg.id));
  }

  useEffect(() => {
    if (!activeOrg) return;
    setLoading(true);
    loadList().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrg?.id]);

  async function openDetail(row) {
    setSelectedMeta(row);
    setDetail(null);
    setDetailLoading(true);
    try {
      const d = await getInvitation(activeOrg.id, row.id);
      setDetail(d);
      // getInvitation() puede haber transicionado INVITED -> VIEWED en el
      // servidor: refresca la lista para que el badge no quede desfasado.
      await loadList();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo abrir la invitación');
    } finally {
      setDetailLoading(false);
    }
  }

  async function runAction(actionFn, successMsg) {
    setBusy(true);
    try {
      await actionFn();
      toast.success(successMsg);
      const d = await getInvitation(activeOrg.id, selectedMeta.id);
      setDetail(d);
      await loadList();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo completar la acción');
    } finally {
      setBusy(false);
    }
  }

  function onAcceptNda() {
    runAction(() => acceptNda(activeOrg.id, selectedMeta.id), 'NDA aceptado');
  }
  function onExpressInterest() {
    runAction(() => expressInterest(activeOrg.id, selectedMeta.id), 'Interés confirmado');
  }
  function onConfirmParticipation() {
    runAction(
      () => confirmParticipation(activeOrg.id, selectedMeta.id),
      'Participación confirmada',
    );
  }
  function onDecline() {
    const reasonCode = window.prompt('Motivo de rechazo (opcional)');
    if (reasonCode === null) return;
    runAction(
      () => declineInvitation(activeOrg.id, selectedMeta.id, reasonCode || null),
      'Invitación declinada',
    );
  }
  function onWithdraw() {
    if (!window.confirm('¿Retirarte de este proceso?')) return;
    runAction(() => withdrawInvitation(activeOrg.id, selectedMeta.id), 'Te retiraste del proceso');
  }

  const ACTION_CONFIG = {
    ACCEPT_NDA: { label: 'Aceptar NDA', onClick: onAcceptNda },
    EXPRESS_INTEREST: { label: 'Confirmar interés', onClick: onExpressInterest },
    CONFIRM_PARTICIPATION: { label: 'Confirmar participación', onClick: onConfirmParticipation },
    DECLINE: { label: 'Declinar', onClick: onDecline, variant: 'outline' },
    WITHDRAW: { label: 'Retirarme', onClick: onWithdraw, variant: 'outline' },
  };

  if (!activeOrg) return null;

  const canQuote = detail && (detail.status === 'PARTICIPATING' || detail.status === 'QUOTED');

  return (
    <div className="space-y-8">
      <Helmet>
        <title>Mis invitaciones · Directorio de Empresas</title>
      </Helmet>

      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Mis invitaciones</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Procesos de sourcing a los que fuiste invitado como proveedor.
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-[380px_1fr]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Inbox className="size-4 text-primary" />
              Invitaciones ({invitations.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {loading ? (
              <div className="h-16 animate-pulse rounded-lg bg-secondary" />
            ) : (
              <>
                {invitations.map((inv) => (
                  <button
                    key={inv.id}
                    type="button"
                    onClick={() => openDetail(inv)}
                    className={cn(
                      'block w-full rounded-lg border px-3 py-2 text-left text-sm hover:bg-accent/50',
                      selectedMeta?.id === inv.id && 'border-primary',
                    )}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium">{inv.event_name}</span>
                      <Badge variant={STATUS_VARIANT[inv.status] || 'neutral'}>
                        {STATUS_LABELS[inv.status] || inv.status}
                      </Badge>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {inv.event_code} · invitado {formatDateTime(inv.invited_at)}
                    </p>
                  </button>
                ))}
                {invitations.length === 0 && (
                  <p className="text-sm text-muted-foreground">
                    Todavía no recibiste invitaciones a procesos de sourcing.
                  </p>
                )}
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{selectedMeta ? selectedMeta.event_name : 'Detalle'}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            {!selectedMeta && (
              <p className="text-sm text-muted-foreground">
                Selecciona una invitación de la lista para ver su detalle.
              </p>
            )}

            {selectedMeta && detailLoading && (
              <div className="h-32 animate-pulse rounded-lg bg-secondary" />
            )}

            {selectedMeta && detail && !detailLoading && (
              <>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={STATUS_VARIANT[detail.status] || 'neutral'}>
                    {STATUS_LABELS[detail.status] || detail.status}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {selectedMeta.event_code} · {selectedMeta.event_type} ·{' '}
                    {selectedMeta.bid_mode === 'SEALED' ? 'Ofertas selladas' : 'Ofertas abiertas'}
                  </span>
                </div>

                {selectedMeta.requires_nda && (
                  <div className="flex items-center gap-2 rounded-lg border border-dashed px-3 py-2 text-sm">
                    <ShieldCheck className="size-4 shrink-0 text-primary" />
                    Este proceso exige aceptar un NDA antes de participar.
                  </div>
                )}

                <div className="flex flex-wrap gap-2">
                  {actionsForStatus(detail.status, selectedMeta.requires_nda).map((code) => {
                    const cfg = ACTION_CONFIG[code];
                    return (
                      <Button
                        key={code}
                        size="sm"
                        variant={cfg.variant || 'primary'}
                        disabled={busy}
                        onClick={cfg.onClick}
                      >
                        {cfg.label}
                      </Button>
                    );
                  })}
                  {canQuote && (
                    <Link to={`/empresa/sourcing/${detail.sourcing_event_id}/mi-cotizacion`}>
                      <Button size="sm" variant="outline" className="gap-1.5">
                        <FileSearch className="size-4" />
                        Mi cotización
                      </Button>
                    </Link>
                  )}
                </div>

                {detail.decline_reason_code && (
                  <p className="text-sm text-muted-foreground">
                    Motivo de rechazo: {detail.decline_reason_code}
                  </p>
                )}

                <div>
                  <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    Historial
                  </h3>
                  <ul className="space-y-1.5 border-l pl-4">
                    {detail.history.map((h, i) => (
                      <li key={i} className="text-sm">
                        <span className="font-medium">
                          {h.from_status ? `${h.from_status} → ${h.to_status}` : h.to_status}
                        </span>
                        <span className="ml-2 text-xs text-muted-foreground">
                          {formatDateTime(h.created_at)}
                        </span>
                        {h.reason && (
                          <p className="text-xs text-muted-foreground">{h.reason}</p>
                        )}
                      </li>
                    ))}
                    {detail.history.length === 0 && (
                      <li className="text-sm text-muted-foreground">Sin historial todavía.</li>
                    )}
                  </ul>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
