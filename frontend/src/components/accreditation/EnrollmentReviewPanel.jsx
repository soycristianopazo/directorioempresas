import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { SelectNative } from '@/components/ui/select-native';

const ENROLLMENT_DECISION_OPTIONS = [
  { value: 'ACCREDITED', label: 'Acreditar' },
  { value: 'OBSERVED', label: 'Observar' },
  { value: 'REJECTED', label: 'Rechazar' },
];

/** Panel de aprobar/observar/rechazar ítems y decidir una postulación —
 * compartido entre el revisor de plataforma (AdminAccreditationPage) y el
 * revisor de programa propio (OrganizationAccreditationReviewPage, fase 9).
 * Desacoplado de cuál API llamar: recibe las tres funciones ya resueltas
 * (loadDetail/reviewFulfillment/decideEnrollment) en vez de organizationId,
 * porque el lado plataforma no tiene una organización a la que atarse. */
export function EnrollmentReviewPanel({
  item,
  loadDetail,
  reviewFulfillment,
  decideEnrollment,
  onDecided,
}) {
  const [detail, setDetail] = useState(null);
  const [enrollmentDecision, setEnrollmentDecision] = useState('ACCREDITED');
  const [reason, setReason] = useState('');

  async function load() {
    setDetail(await loadDetail(item));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [item.id]);

  async function onReview(fulfillmentId, decision) {
    try {
      await reviewFulfillment(fulfillmentId, decision);
      toast.success('Ítem actualizado');
      await load();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo actualizar el ítem');
    }
  }

  async function onDecide() {
    try {
      await decideEnrollment(enrollmentDecision, reason);
      toast.success('Decisión registrada');
      await onDecided();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo registrar la decisión');
    }
  }

  if (!detail) return <div className="mt-2 h-12 animate-pulse rounded-lg bg-secondary" />;

  return (
    <div className="mt-3 space-y-3 border-t pt-3">
      <ul className="space-y-2">
        {detail.fulfillments.map((f) => (
          <li
            key={f.id}
            className="flex items-center justify-between gap-2 rounded-md border px-2 py-1.5 text-xs"
          >
            <span>
              {f.group_name} · {f.requirement_name}
              <Badge variant="neutral" className="ml-2">
                {f.status}
              </Badge>
            </span>
            <div className="flex gap-1">
              <Button size="sm" variant="outline" onClick={() => onReview(f.id, 'APPROVED')}>
                Aprobar
              </Button>
              <Button size="sm" variant="outline" onClick={() => onReview(f.id, 'OBSERVED')}>
                Observar
              </Button>
              <Button size="sm" variant="outline" onClick={() => onReview(f.id, 'REJECTED')}>
                Rechazar
              </Button>
            </div>
          </li>
        ))}
      </ul>

      <div className="flex flex-wrap items-end gap-2 border-t pt-3">
        <div className="space-y-1.5">
          <Label htmlFor={`decision-${item.id}`}>Decisión final</Label>
          <SelectNative
            id={`decision-${item.id}`}
            value={enrollmentDecision}
            onChange={(e) => setEnrollmentDecision(e.target.value)}
          >
            {ENROLLMENT_DECISION_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </SelectNative>
        </div>
        <div className="flex-1 space-y-1.5">
          <Label htmlFor={`reason-${item.id}`}>Motivo (opcional)</Label>
          <Input id={`reason-${item.id}`} value={reason} onChange={(e) => setReason(e.target.value)} />
        </div>
        <Button onClick={onDecide}>Registrar decisión</Button>
      </div>
    </div>
  );
}
