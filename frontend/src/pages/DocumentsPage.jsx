import { useEffect, useRef, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { toast } from 'sonner';
import { FileText, ShieldCheck, Upload } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  listDocumentTypes,
  listDocuments,
  listDocumentVersions,
  uploadDocumentVersion,
} from '@/lib/documentsApi';

const CATEGORY_LABELS = {
  LEGAL: 'Legal',
  TRIBUTARIO: 'Tributario',
  LABORAL: 'Laboral',
  FINANCIERO: 'Financiero',
  SSO: 'Seguridad y salud ocupacional',
  SEGUROS: 'Seguros',
};

function statusBadge(doc) {
  if (!doc.active_version_id) {
    return <Badge variant="outline">Sin subir</Badge>;
  }
  if (doc.valid_until) {
    const expired = new Date(doc.valid_until) < new Date();
    if (expired) return <Badge variant="destructive">Vencido</Badge>;
  }
  return <Badge className="bg-emerald-600 text-white hover:bg-emerald-600">Vigente</Badge>;
}

export default function DocumentsPage() {
  const { activeOrg } = useAuth();
  const [types, setTypes] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(null);

  async function loadAll() {
    const [ts, docs] = await Promise.all([listDocumentTypes(), listDocuments(activeOrg.id)]);
    setTypes(ts);
    setDocuments(docs);
  }

  useEffect(() => {
    if (!activeOrg) return;
    setLoading(true);
    loadAll().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrg?.id]);

  if (!activeOrg) return null;

  const byCategory = types.reduce((acc, t) => {
    (acc[t.category] ??= []).push(t);
    return acc;
  }, {});
  const documentByType = new Map(documents.map((d) => [d.document_type_id, d]));

  return (
    <div className="space-y-8">
      <Helmet>
        <title>Documentos · Directorio de Empresas</title>
      </Helmet>

      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Repositorio de documentos</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Sube y mantén al día la documentación que respalda tu acreditación. Cada nueva versión
          reemplaza a la anterior sin perder el historial.
        </p>
      </header>

      {loading ? (
        <div className="h-32 animate-pulse rounded-lg bg-secondary" />
      ) : (
        Object.entries(byCategory).map(([category, catTypes]) => (
          <Card key={category}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="size-4 text-primary" />
                {CATEGORY_LABELS[category] || category}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {catTypes.map((type) => {
                const doc = documentByType.get(type.id);
                return (
                  <DocumentRow
                    key={type.id}
                    type={type}
                    doc={doc}
                    organizationId={activeOrg.id}
                    expanded={expanded === type.id}
                    onToggle={() => setExpanded(expanded === type.id ? null : type.id)}
                    onUploaded={loadAll}
                  />
                );
              })}
            </CardContent>
          </Card>
        ))
      )}
    </div>
  );
}

function DocumentRow({ type, doc, organizationId, expanded, onToggle, onUploaded }) {
  const [uploading, setUploading] = useState(false);
  const [versions, setVersions] = useState([]);
  const [issuedAt, setIssuedAt] = useState('');
  const fileInputRef = useRef(null);

  useEffect(() => {
    if (!expanded || !doc) return;
    listDocumentVersions(organizationId, doc.id).then(setVersions);
  }, [expanded, doc, organizationId]);

  async function handleUpload(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await uploadDocumentVersion(organizationId, {
        documentTypeId: type.id,
        file,
        issuedAt: issuedAt || undefined,
      });
      toast.success('Documento subido');
      await onUploaded();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo subir el documento');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }

  return (
    <div className="rounded-lg border px-3 py-2">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-between gap-2 text-left text-sm"
      >
        <div>
          <span className="font-medium">{type.name}</span>
          {type.is_sensitive && (
            <ShieldCheck className="ml-1.5 inline size-3.5 text-muted-foreground" />
          )}
          {doc?.valid_until && (
            <span className="ml-2 text-xs text-muted-foreground">vence {doc.valid_until}</span>
          )}
        </div>
        {statusBadge(doc || {})}
      </button>

      {expanded && (
        <div className="mt-3 space-y-3 border-t pt-3">
          {versions.length > 0 && (
            <ul className="space-y-1 text-xs text-muted-foreground">
              {versions.map((v) => (
                <li key={v.id} className="flex items-center gap-2">
                  <Badge variant="outline">{v.status}</Badge>
                  {v.valid_until && <span>vence {v.valid_until}</span>}
                  {v.url && (
                    <a
                      href={v.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary underline"
                    >
                      ver archivo
                    </a>
                  )}
                </li>
              ))}
            </ul>
          )}

          <div className="grid gap-2 sm:grid-cols-[1fr_auto]">
            <div className="space-y-1.5">
              <Label htmlFor={`issued-${type.id}`}>Fecha de emisión (opcional)</Label>
              <Input
                id={`issued-${type.id}`}
                type="date"
                value={issuedAt}
                onChange={(e) => setIssuedAt(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor={`file-${type.id}`}>Archivo PDF</Label>
              <Input
                id={`file-${type.id}`}
                ref={fileInputRef}
                type="file"
                accept="application/pdf"
                onChange={handleUpload}
                disabled={uploading}
              />
            </div>
          </div>
          <p className="flex items-center gap-1 text-[10px] text-muted-foreground">
            <Upload className="size-3" />
            Solo PDF, hasta 20 MB. La nueva versión reemplaza a la anterior.
          </p>
        </div>
      )}
    </div>
  );
}
