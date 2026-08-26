import { useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { FileText, Plus, X } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { TagInput } from '@/components/TagInput';
import { AdminDivisionSelector } from '@/components/AdminDivisionSelector';
import { SingleTreePicker } from '@/components/SingleTreePicker';
import { getTaxonomyTree, getIndustries } from '@/lib/taxonomyApi';
import {
  createRequirement,
  addRequirementLocation,
  setRequirementTags,
  uploadRequirementDocument,
} from '@/lib/requirementsApi';
import { createEvent } from '@/lib/sourcingApi';

const MAX_DOCUMENT_BYTES = 2 * 1024 * 1024;

const schema = z.object({
  name: z.string().trim().min(2, 'Ingresa un nombre'),
  description: z.string().trim().optional(),
});

export default function SourcingEventsPage() {
  const { activeOrg } = useAuth();
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);

  const [taxonomyNodeId, setTaxonomyNodeId] = useState(null);
  const [industryId, setIndustryId] = useState(null);
  const [locations, setLocations] = useState([]); // [{ admin_division_id, name }]
  const [tags, setTags] = useState([]);
  const [files, setFiles] = useState([]); // File[]
  const [fileError, setFileError] = useState(null);

  const form = useForm({
    resolver: zodResolver(schema),
    defaultValues: { name: '', description: '' },
  });

  function resetExtras() {
    setTaxonomyNodeId(null);
    setIndustryId(null);
    setLocations([]);
    setTags([]);
    setFiles([]);
    setFileError(null);
  }

  function handleAddLocation(adminDivisionId, name) {
    if (locations.some((l) => l.admin_division_id === adminDivisionId)) return;
    setLocations([...locations, { admin_division_id: adminDivisionId, name: name || adminDivisionId }]);
  }

  function handleRemoveLocation(adminDivisionId) {
    setLocations(locations.filter((l) => l.admin_division_id !== adminDivisionId));
  }

  function handleFilesChange(e) {
    const picked = Array.from(e.target.files || []);
    e.target.value = '';
    const tooBig = picked.find((f) => f.size > MAX_DOCUMENT_BYTES);
    if (tooBig) {
      setFileError(`"${tooBig.name}" supera el máximo de 2 MB`);
      return;
    }
    setFileError(null);
    setFiles([...files, ...picked]);
  }

  function handleRemoveFile(index) {
    setFiles(files.filter((_, i) => i !== index));
  }

  async function onCreate(values) {
    setSubmitting(true);
    try {
      // Una necesidad liviana queda como registro interno (alimenta cobertura
      // territorial del matching vía requirement_id) pero el usuario nunca la
      // administra por separado — un solo formulario, un solo ID visible: el
      // de la publicación (sourcing_event) que resulta al final.
      const requirementId = await createRequirement(activeOrg.id, {
        name: values.name,
        description: values.description,
        primaryTaxonomyNodeId: taxonomyNodeId,
        industryId,
      });

      for (const location of locations) {
        await addRequirementLocation(activeOrg.id, requirementId, location.admin_division_id);
      }
      if (tags.length > 0) {
        await setRequirementTags(activeOrg.id, requirementId, tags);
      }
      for (const file of files) {
        await uploadRequirementDocument(activeOrg.id, requirementId, file);
      }

      const eventId = await createEvent(activeOrg.id, {
        name: values.name,
        description: values.description,
        requirementId,
      });

      toast.success('Publicación creada');
      form.reset({ name: '', description: '' });
      resetExtras();
      navigate(`/empresa/sourcing/${eventId}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo crear la publicación');
    } finally {
      setSubmitting(false);
    }
  }

  if (!activeOrg) return null;

  return (
    <div className="space-y-8">
      <Helmet>
        <title>Publicar · Directorio de Empresas</title>
      </Helmet>

      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Publicar</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Define qué necesitas y encuentra proveedores que califican. El seguimiento del proceso
            — match, evaluación, negociación y adjudicación — vive en Mis ofertas.
          </p>
        </div>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Nueva publicación</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={form.handleSubmit(onCreate)} className="space-y-5" noValidate>
            <div className="space-y-1.5">
              <Label htmlFor="pub-name">Nombre</Label>
              <Input id="pub-name" {...form.register('name')} />
              {form.formState.errors.name && (
                <p className="text-xs text-destructive">{form.formState.errors.name.message}</p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="pub-description">Descripción</Label>
              <Textarea id="pub-description" {...form.register('description')} />
              <p className="text-xs text-muted-foreground">
                Mientras más específica, mejores las respuestas de los proveedores.
              </p>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label>Giro / categoría (opcional, afina el matching)</Label>
                <SingleTreePicker
                  loader={getTaxonomyTree}
                  value={taxonomyNodeId}
                  onChange={setTaxonomyNodeId}
                  placeholder="Cualquiera"
                  subPlaceholder="Subcategoría (opcional)"
                />
              </div>
              <div className="space-y-1.5">
                <Label>Industria (opcional, afina el matching)</Label>
                <SingleTreePicker
                  loader={getIndustries}
                  value={industryId}
                  onChange={setIndustryId}
                  placeholder="Cualquiera"
                  subPlaceholder="Subindustria (opcional)"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label>Región (opcional, puedes agregar más de una)</Label>
              <AdminDivisionSelector onAdd={handleAddLocation} />
              <div className="flex flex-wrap gap-2 pt-1">
                {locations.map((l) => (
                  <Badge key={l.admin_division_id} variant="neutral" className="gap-1.5">
                    {l.name}
                    <button
                      type="button"
                      onClick={() => handleRemoveLocation(l.admin_division_id)}
                      aria-label={`Quitar ${l.name}`}
                    >
                      <X className="size-3" />
                    </button>
                  </Badge>
                ))}
              </div>
            </div>

            <div className="space-y-1.5">
              <Label>Hashtags / palabras clave (opcional)</Label>
              <TagInput tags={tags} onChange={setTags} />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="pub-files">Bases técnicas u otros archivos (PDF, hasta 2 MB c/u)</Label>
              <Input
                id="pub-files"
                type="file"
                accept="application/pdf"
                multiple
                onChange={handleFilesChange}
              />
              {fileError && <p className="text-xs text-destructive">{fileError}</p>}
              {files.length > 0 && (
                <ul className="space-y-1 pt-1">
                  {files.map((file, index) => (
                    <li
                      key={`${file.name}-${index}`}
                      className="flex items-center justify-between gap-2 rounded-lg border px-3 py-1.5 text-sm"
                    >
                      <span className="flex items-center gap-1.5 truncate">
                        <FileText className="size-3.5 shrink-0 text-muted-foreground" />
                        {file.name}
                      </span>
                      <button
                        type="button"
                        onClick={() => handleRemoveFile(index)}
                        aria-label={`Quitar ${file.name}`}
                      >
                        <X className="size-3.5 text-muted-foreground hover:text-foreground" />
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <Button type="submit" disabled={submitting}>
              <Plus className="size-4" />
              {submitting ? 'Publicando…' : 'Publicar'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
