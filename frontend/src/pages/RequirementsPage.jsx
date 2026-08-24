import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { ClipboardList, Plus } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { createRequirement, listRequirements } from '@/lib/requirementsApi';
import { createEvent } from '@/lib/sourcingApi';

const STATUS_LABELS = {
  DRAFT: 'Borrador',
  CONVERTED: 'Convertida a proceso',
  ARCHIVED: 'Archivada',
};

const schema = z.object({
  name: z.string().trim().min(2, 'Ingresa un nombre'),
  description: z.string().trim().optional(),
});

export default function RequirementsPage() {
  const { activeOrg } = useAuth();
  const navigate = useNavigate();
  const [requirements, setRequirements] = useState([]);
  const [loading, setLoading] = useState(true);

  async function loadAll() {
    setRequirements(await listRequirements(activeOrg.id));
  }

  useEffect(() => {
    if (!activeOrg) return;
    setLoading(true);
    loadAll().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrg?.id]);

  const form = useForm({
    resolver: zodResolver(schema),
    defaultValues: { name: '', description: '' },
  });

  async function onCreate(values) {
    try {
      await createRequirement(activeOrg.id, values);
      toast.success('Necesidad creada');
      form.reset({ name: '', description: '' });
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo crear la necesidad');
    }
  }

  async function onCreateEvent(requirementId) {
    try {
      const eventId = await createEvent(activeOrg.id, {
        name: 'Proceso de sourcing',
        requirementId,
      });
      toast.success('Proceso de sourcing creado');
      navigate(`/empresa/sourcing/${eventId}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo crear el proceso');
    }
  }

  if (!activeOrg) return null;

  return (
    <div className="space-y-8">
      <Helmet>
        <title>Necesidades de compra · Directorio de Empresas</title>
      </Helmet>

      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Necesidades de compra</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Registra lo que necesitas y conviértelo en un proceso de sourcing cuando esté listo.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ClipboardList className="size-4 text-primary" />
            Mis necesidades ({requirements.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {loading ? (
            <div className="h-16 animate-pulse rounded-lg bg-secondary" />
          ) : (
            <>
              {requirements.map((r) => (
                <div
                  key={r.id}
                  className="flex items-center justify-between gap-2 rounded-lg border px-3 py-2 text-sm"
                >
                  <div>
                    <span className="font-medium">{r.name}</span>
                    <Badge variant="outline" className="ml-2">
                      {STATUS_LABELS[r.status] || r.status}
                    </Badge>
                  </div>
                  {r.status === 'DRAFT' && (
                    <Button size="sm" variant="outline" onClick={() => onCreateEvent(r.id)}>
                      Crear proceso de sourcing
                    </Button>
                  )}
                </div>
              ))}
              {requirements.length === 0 && (
                <p className="text-sm text-muted-foreground">Aún no registras necesidades.</p>
              )}
            </>
          )}

          <form onSubmit={form.handleSubmit(onCreate)} className="space-y-3 border-t pt-4" noValidate>
            <div className="space-y-1.5">
              <Label htmlFor="req-name">Nombre de la necesidad</Label>
              <Input id="req-name" {...form.register('name')} />
              {form.formState.errors.name && (
                <p className="text-xs text-destructive">{form.formState.errors.name.message}</p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="req-description">Descripción</Label>
              <Textarea id="req-description" {...form.register('description')} />
            </div>
            <Button type="submit">
              <Plus className="size-4" />
              Registrar necesidad
            </Button>
          </form>
        </CardContent>
      </Card>

      <p className="text-sm text-muted-foreground">
        ¿Ya tienes procesos de sourcing?{' '}
        <Link to="/empresa/sourcing" className="font-medium text-primary hover:underline">
          Ver todos
        </Link>
      </p>
    </div>
  );
}
