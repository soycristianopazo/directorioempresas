import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { ClipboardCheck, Plus } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { SelectNative } from '@/components/ui/select-native';
import { Textarea } from '@/components/ui/textarea';
import {
  createProgram,
  decideEnrollment,
  listReviewQueue,
  reviewFulfillment,
} from '@/lib/adminAccreditationApi';
import { getEnrollmentDetail } from '@/lib/accreditationApi';

const programSchema = z.object({
  code: z.string().trim().min(2, 'Mínimo 2 caracteres'),
  name: z.string().trim().min(2, 'Mínimo 2 caracteres'),
  description: z.string().trim().optional(),
  validityMonths: z.coerce.number().int().positive().default(12),
});

export default function AdminAccreditationPage() {
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState(null);

  async function loadQueue() {
    const rows = await listReviewQueue('UNDER_REVIEW');
    setQueue(rows);
  }

  useEffect(() => {
    setLoading(true);
    loadQueue().finally(() => setLoading(false));
  }, []);

  const programForm = useForm({
    resolver: zodResolver(programSchema),
    defaultValues: { code: '', name: '', description: '', validityMonths: 12 },
  });

  async function onCreateProgram(values) {
    try {
      await createProgram(values);
      toast.success('Programa creado');
      programForm.reset({ code: '', name: '', description: '', validityMonths: 12 });
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo crear el programa');
    }
  }

  return (
    <div className="space-y-8">
      <Helmet>
        <title>Acreditación · Backoffice</title>
      </Helmet>

      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Revisión de acreditación</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Cola de postulaciones en revisión y autoría de programas.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ClipboardCheck className="size-4 text-primary" />
            Cola de revisión ({queue.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {loading ? (
            <div className="h-16 animate-pulse rounded-lg bg-secondary" />
          ) : (
            <>
              {queue.map((item) => (
                <div
                  key={item.id}
                  className="rounded-lg border px-3 py-2 text-sm hover:bg-accent/50"
                >
                  <button
                    type="button"
                    className="flex w-full items-center justify-between gap-2 text-left"
                    onClick={() => setSelectedId(selectedId === item.id ? null : item.id)}
                  >
                    <div>
                      <span className="font-medium">{item.organization_name}</span>
                      <span className="ml-2 text-xs text-muted-foreground">{item.program_name}</span>
                    </div>
                    <Badge variant="outline">{item.completion_pct}%</Badge>
                  </button>
                  {selectedId === item.id && (
                    <EnrollmentReviewPanel
                      item={item}
                      onDecided={async () => {
                        setSelectedId(null);
                        await loadQueue();
                      }}
                    />
                  )}
                </div>
              ))}
              {queue.length === 0 && (
                <p className="text-sm text-muted-foreground">No hay postulaciones en revisión.</p>
              )}
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Plus className="size-4 text-primary" />
            Nuevo programa
          </CardTitle>
          <CardDescription>
            Después de crear el programa, agrega secciones y exigencias desde la base de datos o
            una próxima iteración de este formulario.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={programForm.handleSubmit(onCreateProgram)}
            className="grid gap-3 sm:grid-cols-2"
            noValidate
          >
            <div className="space-y-1.5">
              <Label htmlFor="program-code">Código</Label>
              <Input id="program-code" {...programForm.register('code')} />
              {programForm.formState.errors.code && (
                <p className="text-xs text-destructive">{programForm.formState.errors.code.message}</p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="program-name">Nombre</Label>
              <Input id="program-name" {...programForm.register('name')} />
              {programForm.formState.errors.name && (
                <p className="text-xs text-destructive">{programForm.formState.errors.name.message}</p>
              )}
            </div>
            <div className="space-y-1.5 sm:col-span-2">
              <Label htmlFor="program-description">Descripción</Label>
              <Textarea id="program-description" {...programForm.register('description')} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="program-validity">Vigencia (meses)</Label>
              <Input
                id="program-validity"
                type="number"
                min={1}
                {...programForm.register('validityMonths')}
              />
            </div>
            <div className="flex items-end">
              <Button type="submit">Crear programa</Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

const ENROLLMENT_DECISION_OPTIONS = [
  { value: 'ACCREDITED', label: 'Acreditar' },
  { value: 'OBSERVED', label: 'Observar' },
  { value: 'REJECTED', label: 'Rechazar' },
];

function EnrollmentReviewPanel({ item, onDecided }) {
  const [detail, setDetail] = useState(null);
  const [enrollmentDecision, setEnrollmentDecision] = useState('ACCREDITED');
  const [reason, setReason] = useState('');

  async function load() {
    const d = await getEnrollmentDetail(item.organization_id, item.id);
    setDetail(d);
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [item.id]);

  async function onReview(fulfillmentId, decision) {
    try {
      await reviewFulfillment(fulfillmentId, { decision });
      toast.success('Ítem actualizado');
      await load();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo actualizar el ítem');
    }
  }

  async function onDecide() {
    try {
      await decideEnrollment(item.id, { decision: enrollmentDecision, reason });
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
          <li key={f.id} className="flex items-center justify-between gap-2 rounded-md border px-2 py-1.5 text-xs">
            <span>
              {f.group_name} · {f.requirement_name}
              <Badge variant="outline" className="ml-2">
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
