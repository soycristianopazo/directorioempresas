import { useEffect, useRef, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { ArrowRight, Check, ImagePlus, Package, Plus, SkipForward, X } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { SelectNative } from '@/components/ui/select-native';
import { cn } from '@/lib/utils';
import { CategorySelector } from '@/components/CategorySelector';
import { OfferingCompletionBadge } from '@/components/OfferingCompletion';
import { getCurrencies, getUnitsOfMeasure } from '@/lib/referenceApi';
import {
  listOfferings,
  createOffering,
  setOfferingTaxonomyNodes,
  setOfferingPricing,
  uploadOfferingMedia,
} from '@/lib/offeringsApi';

const OFFERING_TYPES = ['PRODUCT', 'SERVICE', 'RENTAL', 'SOFTWARE', 'TRAINING', 'CONSULTING'];
const TYPE_LABELS = {
  PRODUCT: 'Producto', SERVICE: 'Servicio', RENTAL: 'Arriendo',
  SOFTWARE: 'Software', TRAINING: 'Capacitación', CONSULTING: 'Consultoría',
};
const STATUS_VARIANT = { DRAFT: 'warning', ACTIVE: 'success', PAUSED: 'neutral', ARCHIVED: 'destructive' };
const STATUS_LABEL = { DRAFT: 'Borrador', ACTIVE: 'Publicado', PAUSED: 'Pausado', ARCHIVED: 'Archivado' };
const PRICE_TYPES = ['ON_REQUEST', 'FIXED', 'FROM', 'RANGE'];
const PRICE_TYPE_LABELS = { FIXED: 'Precio fijo', FROM: 'Desde', RANGE: 'Rango', ON_REQUEST: 'Bajo cotización' };

const WIZARD_STEPS = ['Básico', 'Categoría', 'Precio', 'Fotos'];

const basicSchema = z.object({
  offeringType: z.enum(OFFERING_TYPES),
  name: z.string().trim().min(2, 'Mínimo 2 caracteres'),
  shortDescription: z.string().trim().max(280).optional(),
});

export default function CatalogPage() {
  const { activeOrg } = useAuth();
  const navigate = useNavigate();
  const [offerings, setOfferings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showWizard, setShowWizard] = useState(false);

  async function load() {
    try {
      setOfferings(await listOfferings(activeOrg.id));
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo cargar el catálogo');
    }
  }

  useEffect(() => {
    if (!activeOrg) return;
    setLoading(true);
    load().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrg?.id]);

  function handleFinishWizard(offeringId) {
    setShowWizard(false);
    navigate(`/empresa/catalogo/${offeringId}`);
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
        <Button onClick={() => setShowWizard((v) => !v)} className="gap-1.5">
          {showWizard ? <X className="size-4" /> : <Plus className="size-4" />}
          {showWizard ? 'Cancelar' : 'Nuevo'}
        </Button>
      </header>

      {showWizard && (
        <NewOfferingWizard organizationId={activeOrg.id} onFinish={handleFinishWizard} />
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
                    <div className="flex shrink-0 items-center gap-3">
                      <OfferingCompletionBadge pct={offering.completion_pct} />
                      <Badge variant={STATUS_VARIANT[offering.status] ?? 'neutral'}>
                        {STATUS_LABEL[offering.status] ?? offering.status}
                      </Badge>
                    </div>
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

/** Antes "Nuevo" creaba el registro con 3 campos y mandaba al usuario a
 * "completar después" en la ficha — en la práctica casi nadie volvía, así
 * que la mayoría del catálogo quedaba a medio llenar (sin foto, sin precio,
 * sin categoría). Este wizard pide lo mismo que antes en el paso 1, pero
 * seguido — sin soltar al usuario — de categoría/precio/fotos, cada uno
 * saltable con "Omitir" para no forzar nada, antes de aterrizar en la ficha
 * completa. */
function NewOfferingWizard({ organizationId, onFinish }) {
  const [step, setStep] = useState(0);
  const [offeringId, setOfferingId] = useState(null);

  function handleCreated(id) {
    setOfferingId(id);
    setStep(1);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Nuevo producto o servicio</CardTitle>
        <CardDescription>
          Paso {step + 1} de {WIZARD_STEPS.length} — {WIZARD_STEPS[step]}
        </CardDescription>
        <div className="flex gap-1 pt-1">
          {WIZARD_STEPS.map((label, i) => (
            <div
              key={label}
              className={cn('h-1 flex-1 rounded-full', i <= step ? 'bg-primary' : 'bg-secondary')}
            />
          ))}
        </div>
      </CardHeader>
      <CardContent>
        {step === 0 && <BasicStep organizationId={organizationId} onCreated={handleCreated} />}
        {step === 1 && (
          <CategoryStep
            organizationId={organizationId}
            offeringId={offeringId}
            onNext={() => setStep(2)}
          />
        )}
        {step === 2 && (
          <PricingStep
            organizationId={organizationId}
            offeringId={offeringId}
            onNext={() => setStep(3)}
          />
        )}
        {step === 3 && (
          <PhotosStep
            organizationId={organizationId}
            offeringId={offeringId}
            onFinish={() => onFinish(offeringId)}
          />
        )}
      </CardContent>
    </Card>
  );
}

function BasicStep({ organizationId, onCreated }) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(basicSchema),
    defaultValues: { offeringType: 'SERVICE', name: '', shortDescription: '' },
  });

  async function onSubmit(values) {
    try {
      const id = await createOffering(organizationId, {
        offering_type: values.offeringType,
        name: values.name,
        short_description: values.shortDescription || null,
      });
      toast.success('Producto o servicio creado');
      onCreated(id);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo crear');
    }
  }

  return (
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
          {isSubmitting ? 'Creando…' : 'Siguiente'}
          <ArrowRight className="size-4" />
        </Button>
      </div>
    </form>
  );
}

function CategoryStep({ organizationId, offeringId, onNext }) {
  const [nodes, setNodes] = useState([]);
  const [saving, setSaving] = useState(false);

  async function onContinue() {
    if (nodes.length === 0) {
      onNext();
      return;
    }
    setSaving(true);
    try {
      await setOfferingTaxonomyNodes(organizationId, offeringId, nodes);
      onNext();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo guardar la categoría');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Elige al menos una categoría — es lo que más ayuda a que los compradores te encuentren.
      </p>
      <CategorySelector selected={nodes} onChange={setNodes} />
      <div className="flex gap-2">
        <Button onClick={onContinue} disabled={saving} className="gap-1.5">
          {saving ? 'Guardando…' : 'Siguiente'}
          <ArrowRight className="size-4" />
        </Button>
        <Button type="button" variant="ghost" onClick={onNext} className="gap-1.5 text-muted-foreground">
          <SkipForward className="size-4" />
          Omitir por ahora
        </Button>
      </div>
    </div>
  );
}

function PricingStep({ organizationId, offeringId, onNext }) {
  const [priceType, setPriceType] = useState('ON_REQUEST');
  const [amountMin, setAmountMin] = useState('');
  const [currencyCode, setCurrencyCode] = useState('');
  const [unitCode, setUnitCode] = useState('');
  const [currencies, setCurrencies] = useState([]);
  const [units, setUnits] = useState([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getCurrencies().then(setCurrencies).catch(() => {});
    getUnitsOfMeasure().then(setUnits).catch(() => {});
  }, []);

  async function onContinue() {
    setSaving(true);
    try {
      await setOfferingPricing(organizationId, offeringId, {
        price_type: priceType,
        amount_min: amountMin === '' ? null : Number(amountMin),
        amount_max: null,
        currency_code: currencyCode || null,
        unit_code: unitCode || null,
        valid_until: null,
        is_public: false,
      });
      onNext();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo guardar el precio');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Declarar el precio (aunque sea &quot;bajo cotización&quot;) hace tu ficha más confiable.
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label>Tipo</Label>
          <SelectNative value={priceType} onChange={(e) => setPriceType(e.target.value)}>
            {PRICE_TYPES.map((p) => (
              <option key={p} value={p}>
                {PRICE_TYPE_LABELS[p]}
              </option>
            ))}
          </SelectNative>
        </div>
        {priceType !== 'ON_REQUEST' && (
          <>
            <div className="space-y-1.5">
              <Label>Monto</Label>
              <Input
                type="number"
                step="0.01"
                value={amountMin}
                onChange={(e) => setAmountMin(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Moneda</Label>
              <SelectNative value={currencyCode} onChange={(e) => setCurrencyCode(e.target.value)}>
                <option value="">Sin especificar</option>
                {currencies.map((c) => (
                  <option key={c.code} value={c.code}>
                    {c.code} — {c.name}
                  </option>
                ))}
              </SelectNative>
            </div>
            <div className="space-y-1.5">
              <Label>Unidad</Label>
              <SelectNative value={unitCode} onChange={(e) => setUnitCode(e.target.value)}>
                <option value="">Sin especificar</option>
                {units.map((u) => (
                  <option key={u.code} value={u.code}>
                    {u.name}
                  </option>
                ))}
              </SelectNative>
            </div>
          </>
        )}
      </div>
      <div className="flex gap-2">
        <Button onClick={onContinue} disabled={saving} className="gap-1.5">
          {saving ? 'Guardando…' : 'Siguiente'}
          <ArrowRight className="size-4" />
        </Button>
        <Button type="button" variant="ghost" onClick={onNext} className="gap-1.5 text-muted-foreground">
          <SkipForward className="size-4" />
          Omitir por ahora
        </Button>
      </div>
    </div>
  );
}

function PhotosStep({ organizationId, offeringId, onFinish }) {
  const [photos, setPhotos] = useState([]);
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef(null);

  async function handleUpload(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const result = await uploadOfferingMedia(organizationId, offeringId, file);
      setPhotos((prev) => [...prev, result]);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo subir la foto');
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Las fichas con fotos generan mucha más confianza. Puedes agregar más después.
      </p>
      <div className="flex flex-wrap gap-3">
        {photos.map((p) => (
          <img key={p.id} src={p.url} alt="" className="size-20 rounded-lg border object-cover" />
        ))}
        {photos.length === 0 && (
          <div className="flex size-20 items-center justify-center rounded-lg border border-dashed text-muted-foreground">
            <ImagePlus className="size-5" />
          </div>
        )}
      </div>
      <Input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/gif"
        onChange={handleUpload}
        disabled={uploading}
        className="max-w-xs"
      />
      <div className="flex gap-2">
        <Button onClick={onFinish} className="gap-1.5">
          <Check className="size-4" />
          Finalizar
        </Button>
        {photos.length === 0 && (
          <Button type="button" variant="ghost" onClick={onFinish} className="gap-1.5 text-muted-foreground">
            <SkipForward className="size-4" />
            Omitir por ahora
          </Button>
        )}
      </div>
    </div>
  );
}
