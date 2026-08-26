import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { ExternalLink, FileSearch, ShieldCheck } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  acceptNda,
  confirmParticipation,
  declineInvitation,
  expressInterest,
  getInvitation,
  listMyInvitations,
  listSentInvitations,
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

function StatusBadge({ status }) {
  return <Badge variant={STATUS_VARIANT[status] || 'neutral'}>{STATUS_LABELS[status] || status}</Badge>;
}

export default function SupplierInvitationsPage() {
  const { activeOrg } = useAuth();
  const [invitations, setInvitations] = useState([]);
  const [sentInvitations, setSentInvitations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedMeta, setSelectedMeta] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [busy, setBusy] = useState(false);

  async function loadList() {
    try {
      setInvitations(await listMyInvitations(activeOrg.id));
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudieron cargar las invitaciones');
    }
    try {
      setSentInvitations(await listSentInvitations(activeOrg.id));
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudieron cargar las invitaciones enviadas');
    }
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
    setDialogOpen(true);
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
        <title>Invitaciones · Directorio de Empresas</title>
      </Helmet>

      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Invitaciones</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Procesos de sourcing en los que participás — como invitado o como quien invita.
        </p>
      </header>

      <Tabs defaultValue="received">
        <TabsList>
          <TabsTrigger value="received">Recibidas ({invitations.length})</TabsTrigger>
          <TabsTrigger value="sent">Enviadas ({sentInvitations.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="received">
          {loading ? (
            <div className="h-32 animate-pulse rounded-lg bg-secondary" />
          ) : (
            <div className="overflow-x-auto rounded-lg border">
              <table className="w-full text-left text-sm">
                <thead className="bg-secondary/50 text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2 font-medium">Evento</th>
                    <th className="px-3 py-2 font-medium">Código</th>
                    <th className="px-3 py-2 font-medium">Estado</th>
                    <th className="px-3 py-2 font-medium">Invitado el</th>
                  </tr>
                </thead>
                <tbody>
                  {invitations.map((inv) => (
                    <tr
                      key={inv.id}
                      onClick={() => openDetail(inv)}
                      className="cursor-pointer border-t hover:bg-accent/50"
                    >
                      <td className="px-3 py-3 font-medium">{inv.event_name}</td>
                      <td className="px-3 py-3 text-muted-foreground">{inv.event_code}</td>
                      <td className="px-3 py-3">
                        <StatusBadge status={inv.status} />
                      </td>
                      <td className="px-3 py-3 whitespace-nowrap text-muted-foreground">
                        {formatDateTime(inv.invited_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {invitations.length === 0 && (
                <p className="px-4 py-8 text-center text-sm text-muted-foreground">
                  Todavía no recibiste invitaciones a procesos de sourcing.
                </p>
              )}
            </div>
          )}
        </TabsContent>

        <TabsContent value="sent">
          {loading ? (
            <div className="h-32 animate-pulse rounded-lg bg-secondary" />
          ) : (
            <div className="overflow-x-auto rounded-lg border">
              <table className="w-full text-left text-sm">
                <thead className="bg-secondary/50 text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2 font-medium">Proveedor</th>
                    <th className="px-3 py-2 font-medium">Evento</th>
                    <th className="px-3 py-2 font-medium">Estado</th>
                    <th className="px-3 py-2 font-medium">Invitado el</th>
                    <th className="w-10 px-3 py-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {sentInvitations.map((inv) => (
                    <tr key={inv.id} className="border-t">
                      <td className="px-3 py-3 font-medium">
                        {inv.supplier_trade_name || inv.supplier_legal_name}
                      </td>
                      <td className="px-3 py-3">
                        {inv.event_name}
                        <p className="text-xs text-muted-foreground">{inv.event_code}</p>
                      </td>
                      <td className="px-3 py-3">
                        <StatusBadge status={inv.status} />
                      </td>
                      <td className="px-3 py-3 whitespace-nowrap text-muted-foreground">
                        {formatDateTime(inv.invited_at)}
                      </td>
                      <td className="px-3 py-3">
                        <Link to={`/empresa/sourcing/${inv.sourcing_event_id}`}>
                          <Button variant="outline" size="sm" className="gap-1.5">
                            <ExternalLink className="size-3.5" />
                            Ver proceso
                          </Button>
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {sentInvitations.length === 0 && (
                <p className="px-4 py-8 text-center text-sm text-muted-foreground">
                  Todavía no invitaste proveedores a ningún proceso. Podés hacerlo desde la ficha
                  de un proceso de sourcing.
                </p>
              )}
            </div>
          )}
        </TabsContent>
      </Tabs>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>{selectedMeta?.event_name}</DialogTitle>
          </DialogHeader>

          {detailLoading && <div className="h-32 animate-pulse rounded-lg bg-secondary" />}

          {selectedMeta && detail && !detailLoading && (
            <div className="space-y-5">
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge status={detail.status} />
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
                      {h.reason && <p className="text-xs text-muted-foreground">{h.reason}</p>}
                    </li>
                  ))}
                  {detail.history.length === 0 && (
                    <li className="text-sm text-muted-foreground">Sin historial todavía.</li>
                  )}
                </ul>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
