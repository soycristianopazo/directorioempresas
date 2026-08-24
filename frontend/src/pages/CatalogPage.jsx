import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { Package, Plus } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { SelectNative } from '@/components/ui/select-native';
import { listOfferings, createOffering } from '@/lib/offeringsApi';

const OFFERING_TYPES = ['PRODUCT', 'SERVICE', 'RENTAL', 'SOFTWARE', 'TRAINING', 'CONSULTING'];
const TYPE_LABELS = {
  PRODUCT: 'Producto', SERVICE: 'Servicio', RENTAL: 'Arriendo',
  SOFTWARE: 'Software', TRAINING: 'Capacitación', CONSULTING: 'Consultoría',
};
const STATUS_VARIANT = { DRAFT: 'warning', ACTIVE: 'success', PAUSED: 'neutral', ARCHIVED: 'destructive' };
const STATUS_LABEL = { DRAFT: 'Borrador', ACTIVE: 'Publicado', PAUSED: 'Pausado', ARCHIVED: 'Archivado' };

const schema = z.object({
  offeringType: z.enum(OFFERING_TYPES),
  name: z.string().trim().min(2, 'Mínimo 2 caracteres'),
  shortDescription: z.string().trim().max(280).optional(),
});

export default function CatalogPage() {
  const { activeOrg } = useAuth();
  const navigate = useNavigate();
  const [offerings, setOfferings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);

  async function load() {
    setOfferings(await listOfferings(activeOrg.id));
  }

  useEffect(() => {
    if (!activeOrg) return;
    setLoading(true);
    load().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrg?.id]);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues: { offeringType: 'SERVICE', name: '', shortDescription: '' },
  });

  async function onSubmit(values) {
    try {
      const id = await createOffering(activeOrg.id, {
        offering_type: values.offeringType,
        name: values.name,
        short_description: values.shortDescription || null,
      });
      toast.success('Producto o servicio creado');
      reset();
      setShowForm(false);
      navigate(`/empresa/catalogo/${id}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo crear');
    }
  }

  if (!activeOrg) return null;

  return (
    <div className="space-y-6">
      <Helmet>
        <title>Catálogo · Directorio de Empresas</title>
      </Helmet>

      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Catálogo</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Los productos y servicios que ofrece {activeOrg.trade_name ?? activeOrg.legal_name}.
          </p>
        </div>
        <Button onClick={() => setShowForm((v) => !v)} className="gap-1.5">
          <Plus className="size-4" />
          Nuevo
        </Button>
      </header>

      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Nuevo producto o servicio</CardTitle>
            <CardDescription>
              Completa categoría, atributos, precio y fotos después de crearlo.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="grid gap-3 sm:grid-cols-2" noValidate>
              <div className="space-y-1.5 sm:col-span-2">
                <Label htmlFor="offering-name">Nombre</Label>
                <Input id="offering-name" placeholder="Traslado de trabajadores a faena" {...register('name')} />
                {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="offering-type">Tipo</Label>
                <SelectNative id="offering-type" {...register('offeringType')}>
                  {OFFERING_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {TYPE_LABELS[t]}
                    </option>
                  ))}
                </SelectNative>
              </div>
              <div className="space-y-1.5 sm:col-span-2">
                <Label htmlFor="offering-short">Descripción corta</Label>
                <Input id="offering-short" maxLength={280} {...register('shortDescription')} />
              </div>
              <div className="sm:col-span-2">
                <Button type="submit" disabled={isSubmitting} className="gap-1.5">
                  <Plus className="size-4" />
                  {isSubmitting ? 'Creando…' : 'Crear'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="space-y-2 p-5">
              <div className="h-14 animate-pulse rounded-lg bg-secondary" />
              <div className="h-14 animate-pulse rounded-lg bg-secondary/60" />
            </div>
          ) : offerings.length === 0 ? (
            <div className="flex flex-col items-center gap-2 px-6 py-16 text-center">
              <Package className="size-8 text-muted-foreground" />
              <p className="font-medium">Todavía no tienes nada publicado</p>
              <p className="max-w-sm text-sm text-muted-foreground">
                Agrega tu primer producto o servicio para que los compradores puedan encontrarte.
              </p>
            </div>
          ) : (
            <ul className="divide-y">
              {offerings.map((offering) => (
                <li key={offering.id}>
                  <Link
                    to={`/empresa/catalogo/${offering.id}`}
                    className="flex items-center justify-between gap-3 px-5 py-3 hover:bg-accent"
                  >
                    <div className="min-w-0">
                      <p className="truncate font-medium">{offering.name}</p>
                      <p className="truncate text-xs text-muted-foreground">
                        {TYPE_LABELS[offering.offering_type]}
                        {offering.short_description && ` · ${offering.short_description}`}
                      </p>
                    </div>
                    <Badge variant={STATUS_VARIANT[offering.status] ?? 'neutral'}>
                      {STATUS_LABEL[offering.status] ?? offering.status}
                    </Badge>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
