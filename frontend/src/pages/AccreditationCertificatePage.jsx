import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { toast } from 'sonner';
import { CheckCircle2, Download, ShieldCheck, XCircle } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { getCertificate } from '@/lib/accreditationApi';
import logo from '@/assets/logo.png';

const STATUS_LABEL = {
  INCOMPLETE: 'Incompleta',
  PENDING_DOCUMENTS: 'Reuniendo documentos',
  UNDER_REVIEW: 'En revisión',
  ACCREDITED: 'Acreditado',
  OBSERVED: 'Con observaciones',
  SUSPENDED: 'Suspendido',
  REJECTED: 'No acreditado',
  EXPIRED: 'Vencido',
};

const LEGEND = [
  { status: 'ACCREDITED', label: 'ACREDITADO', description: 'Cumple con las exigencias para operar como proveedor del Directorio de Empresas.' },
  { status: 'UNDER_REVIEW', label: 'EN REVISIÓN', description: 'Postulación en proceso de validación con el equipo revisor. Su estado se actualizará al finalizar.' },
  { status: 'EXPIRED', label: 'VENCIDO', description: 'La acreditación venció (vigencia anual) y debe renovarse para volver a operar como acreditado.' },
  { status: 'REJECTED', label: 'NO ACREDITADO', description: 'No cumple, o dejó de cumplir, con las exigencias del programa de acreditación.' },
];

function formatDate(value) {
  if (!value) return '—';
  return new Date(value).toLocaleDateString('es-CL');
}

function formatDateTime(value) {
  if (!value) return '—';
  return new Date(value).toLocaleString('es-CL');
}

export default function AccreditationCertificatePage() {
  const { activeOrg } = useAuth();
  const { enrollmentId } = useParams();
  const [certificate, setCertificate] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!activeOrg) return;
    setLoading(true);
    getCertificate(activeOrg.id, enrollmentId)
      .then(setCertificate)
      .catch((error) => {
        toast.error(error.response?.data?.detail || 'No se pudo cargar el certificado');
      })
      .finally(() => setLoading(false));
  }, [activeOrg, enrollmentId]);

  if (!activeOrg) return null;

  if (loading) {
    return <div className="h-64 animate-pulse rounded-lg bg-secondary" />;
  }

  if (!certificate) {
    return <p className="text-sm text-muted-foreground">No se encontró el certificado.</p>;
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <Helmet>
        <title>Certificado de acreditación · Directorio de Empresas</title>
      </Helmet>

      <div className="flex justify-end print:hidden">
        <Button onClick={() => window.print()}>
          <Download className="size-4" />
          Descargar certificado en PDF
        </Button>
      </div>

      <Card className="print:border-none print:shadow-none">
        <CardContent className="space-y-8 p-8">
          <div className="flex flex-wrap items-start justify-between gap-4 border-b pb-6">
            <div className="flex items-center gap-3">
              <img src={logo} alt="Directorio de Empresas" className="h-10 w-auto" />
              <div>
                <p className="text-lg font-semibold leading-tight">Directorio de Empresas</p>
                <p className="text-xs text-muted-foreground">Certificado de Acreditación de Proveedor</p>
              </div>
            </div>
            <div className="text-right text-xs text-muted-foreground">
              <p>
                <span className="font-medium text-foreground">Número de Folio:</span> {certificate.folio}
              </p>
              <p className="italic">Fecha de emisión {formatDateTime(certificate.issued_at)}</p>
            </div>
          </div>

          <div className="text-center">
            <h1 className="text-xl font-semibold tracking-tight">Certificado de Acreditación de Proveedor</h1>
            <p className="mx-auto mt-2 max-w-xl text-sm text-muted-foreground">
              Se certifica que el proveedor indicado a continuación posee el siguiente estado de acreditación
              ante el Directorio de Empresas, de acuerdo con la fecha y hora especificada.
            </p>
          </div>

          <div className="overflow-x-auto rounded-lg border">
            <table className="w-full text-left text-sm">
              <thead className="bg-secondary/50 text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="px-4 py-2 font-medium">Proveedor</th>
                  <th className="px-4 py-2 font-medium">RUT</th>
                  <th className="px-4 py-2 font-medium">Programa</th>
                  <th className="px-4 py-2 font-medium">Estado</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-t">
                  <td className="px-4 py-3 font-medium">{certificate.organization_legal_name}</td>
                  <td className="px-4 py-3">{certificate.organization_rut || '—'}</td>
                  <td className="px-4 py-3">{certificate.program_name}</td>
                  <td className="px-4 py-3">
                    {certificate.is_accredited ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 dark:text-emerald-400">
                        <CheckCircle2 className="size-3.5" />
                        ACREDITADO
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 rounded-full bg-destructive/15 px-2.5 py-0.5 text-xs font-semibold text-destructive">
                        <XCircle className="size-3.5" />
                        {STATUS_LABEL[certificate.status]?.toUpperCase() || 'NO ACREDITADO'}
                      </span>
                    )}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-xs text-muted-foreground">Vigente desde</dt>
              <dd className="mt-0.5 text-sm font-medium">{formatDate(certificate.valid_from)}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Vigente hasta</dt>
              <dd className="mt-0.5 text-sm font-medium">{formatDate(certificate.valid_until)}</dd>
            </div>
          </div>

          <div className="rounded-lg bg-secondary/40 p-4">
            <p className="mb-3 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              <ShieldCheck className="size-3.5" />
              Observaciones
            </p>
            <dl className="space-y-2 text-xs">
              {LEGEND.map((item) => (
                <div key={item.status} className="flex gap-3">
                  <dt className="w-32 shrink-0 font-semibold">{item.label}</dt>
                  <dd className="text-muted-foreground">{item.description}</dd>
                </div>
              ))}
            </dl>
          </div>

          <p className="text-center text-xs italic text-muted-foreground">
            Se emite el presente certificado conforme al programa de acreditación{' '}
            <span className="font-medium">{certificate.program_name}</span> del Directorio de Empresas. La
            acreditación tiene vigencia anual y debe renovarse al vencer el período indicado.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
