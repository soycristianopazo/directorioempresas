import { useEffect, useMemo, useRef, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import {
  ArrowLeft,
  Archive,
  Ban,
  FileText,
  Image as ImageIcon,
  MapPinned,
  Rocket,
  Sliders,
  Tags,
  Trash2,
  Upload,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { SelectNative } from '@/components/ui/select-native';
import { Textarea } from '@/components/ui/textarea';
import { CategorySelector } from '@/components/CategorySelector';
import { IndustrySelector } from '@/components/IndustrySelector';
import { TagInput } from '@/components/TagInput';
import { AdminDivisionSelector } from '@/components/AdminDivisionSelector';
import { OfferingCompletion } from '@/components/OfferingCompletion';
import { getNodeAttributes } from '@/lib/taxonomyApi';
import { getCurrencies, getUnitsOfMeasure } from '@/lib/referenceApi';
import {
  getOffering,
  updateOffering,
  publishOffering,
  setOfferingStatus,
  deleteOffering,
  getOfferingTaxonomyNodes,
  setOfferingTaxonomyNodes,
  getOfferingIndustries,
  setOfferingIndustries,
  getOfferingTags,
  setOfferingTags,
  getOfferingTerritories,
  addOfferingTerritory,
  removeOfferingTerritory,
  getOfferingPricing,
  setOfferingPricing,
  listOfferingMedia,
  uploadOfferingMedia,
  deleteOfferingMedia,
  listOfferingDocuments,
  uploadOfferingDocument,
  deleteOfferingDocument,
  listOfferingAttributeValues,
  setOfferingAttributeValue,
} from '@/lib/offeringsApi';

const AVAILABILITY = ['AVAILABLE', 'LIMITED', 'ON_REQUEST', 'UNAVAILABLE'];
const AVAILABILITY_LABELS = {
  AVAILABLE: 'Disponible', LIMITED: 'Disponibilidad limitada', ON_REQUEST: 'Bajo pedido', UNAVAILABLE: 'No disponible',
};
const VISIBILITY = ['PUBLIC', 'REGISTERED', 'BUYERS_ONLY', 'INVITED_ONLY', 'PRIVATE'];
const VISIBILITY_LABELS = {
  PUBLIC: 'Público', REGISTERED: 'Usuarios registrados', BUYERS_ONLY: 'Solo compradores',
  INVITED_ONLY: 'Solo invitados', PRIVATE: 'Privado',
};
const STATUS_VARIANT = { DRAFT: 'warning', ACTIVE: 'success', PAUSED: 'neutral', ARCHIVED: 'destructive' };
const STATUS_LABEL = { DRAFT: 'Borrador', ACTIVE: 'Publicado', PAUSED: 'Pausado', ARCHIVED: 'Archivado' };
const PRICE_TYPES = ['FIXED', 'FROM', 'RANGE', 'ON_REQUEST'];
const PRICE_TYPE_LABELS = { FIXED: 'Precio fijo', FROM: 'Desde', RANGE: 'Rango', ON_REQUEST: 'Bajo cotización' };
const COVERAGE_LABELS = { OPERATIONAL: 'Operacional', COMMERCIAL: 'Comercial', MOBILIZABLE: 'Movilizable' };

const basicSchema = z.object({
  name: z.string().trim().min(2, 'Mínimo 2 caracteres'),
  shortDescription: z.string().trim().max(280).optional(),
  fullDescription: z.string().trim().max(5000).optional(),
  brand: z.string().trim().optional(),
  model: z.string().trim().optional(),
  leadTimeDays: z.union([z.string().length(0), z.coerce.number().int().min(0)]).optional(),
  warrantyMonths: z.union([z.string().length(0), z.coerce.number().int().min(0)]).optional(),
  availabilityStatus: z.enum(AVAILABILITY),
  visibility: z.enum(VISIBILITY),
  hasAfterSales: z.boolean().default(false),
});

const pricingSchema = z.object({
  priceType: z.enum(PRICE_TYPES),
  amountMin: z.union([z.string().length(0), z.coerce.number()]).optional(),
  amountMax: z.union([z.string().length(0), z.coerce.number()]).optional(),
  currencyCode: z.string().optional(),
  unitCode: z.string().optional(),
  isPublic: z.boolean().default(false),
});

export default function OfferingDetailPage() {
  const { offeringId } = useParams();
  const { activeOrg } = useAuth();
  const navigate = useNavigate();

  const [offering, setOffering] = useState(null);
  const [taxonomyNodes, setTaxonomyNodes] = useState([]);
  const [industries, setIndustries] = useState([]);
  const [tags, setTags] = useState([]);
  const [territories, setTerritories] = useState([]);
  const [pricing, setPricing] = useState(null);
  const [media, setMedia] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [attributeDefs, setAttributeDefs] = useState([]);
  const [attrDraft, setAttrDraft] = useState({});
  const [currencies, setCurrencies] = useState([]);
  const [units, setUnits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [savingAttrs, setSavingAttrs] = useState(false);
  const [uploadingMedia, setUploadingMedia] = useState(false);
  const [uploadingDoc, setUploadingDoc] = useState(false);
  const mediaInputRef = useRef(null);
  const docInputRef = useRef(null);
  const docNameRef = useRef(null);

  const primaryNode = taxonomyNodes.find((n) => n.is_primary) ?? taxonomyNodes[0];

  async function loadAll() {
    const org = activeOrg.id;
    const [off, nodes, inds, offeringTags, terrs, price, mediaList, docs, attrValues, refCurrencies, refUnits] =
      await Promise.all([
        getOffering(org, offeringId),
        getOfferingTaxonomyNodes(org, offeringId),
        getOfferingIndustries(org, offeringId),
        getOfferingTags(org, offeringId),
        getOfferingTerritories(org, offeringId),
        getOfferingPricing(org, offeringId),
        listOfferingMedia(org, offeringId),
        listOfferingDocuments(org, offeringId),
        listOfferingAttributeValues(org, offeringId),
        getCurrencies(),
        getUnitsOfMeasure(),
      ]);
    setOffering(off);
    setTaxonomyNodes(nodes);
    setIndustries(inds);
    setTags(offeringTags.map((t) => t.tag));
    setTerritories(terrs);
    setPricing(price);
    setMedia(mediaList);
    setDocuments(docs);
    setCurrencies(refCurrencies);
    setUnits(refUnits);

    const primary = nodes.find((n) => n.is_primary) ?? nodes[0];
    if (primary) {
      const defs = await getNodeAttributes(primary.node_id);
      setAttributeDefs(defs);
      const draft = {};
      for (const def of defs) {
        const existing = attrValues.find((v) => v.attribute_definition_id === def.attribute_definition_id);
        if (!existing) continue;
        if (def.data_type === 'MULTISELECT') draft[def.attribute_definition_id] = existing.multiselect_option_ids ?? [];
        else if (def.data_type === 'SELECT') draft[def.attribute_definition_id] = existing.option_id ?? '';
        else if (def.data_type === 'BOOLEAN') draft[def.attribute_definition_id] = existing.value_boolean ?? false;
        else if (def.data_type === 'DATE') draft[def.attribute_definition_id] = existing.value_date ?? '';
        else if (def.data_type === 'NUMBER') draft[def.attribute_definition_id] = existing.value_number ?? '';
        else draft[def.attribute_definition_id] = existing.value_text ?? '';
      }
      setAttrDraft(draft);
    } else {
      setAttributeDefs([]);
      setAttrDraft({});
    }
  }

  useEffect(() => {
    if (!activeOrg) return;
    setLoading(true);
    loadAll().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrg?.id, offeringId]);

  const basicForm = useForm({ resolver: zodResolver(basicSchema) });
  const pricingForm = useForm({ resolver: zodResolver(pricingSchema) });

  useEffect(() => {
    if (!offering) return;
    basicForm.reset({
      name: offering.name,
      shortDescription: offering.short_description ?? '',
      fullDescription: offering.full_description ?? '',
      brand: offering.brand ?? '',
      model: offering.model ?? '',
      leadTimeDays: offering.lead_time_days ?? '',
      warrantyMonths: offering.warranty_months ?? '',
      availabilityStatus: offering.availability_status,
      visibility: offering.visibility,
      hasAfterSales: offering.has_after_sales,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [offering]);

  useEffect(() => {
    pricingForm.reset({
      priceType: pricing?.price_type ?? 'ON_REQUEST',
      amountMin: pricing?.amount_min ?? '',
      amountMax: pricing?.amount_max ?? '',
      currencyCode: pricing?.currency_code ?? '',
      unitCode: pricing?.unit_code ?? '',
      isPublic: pricing?.is_public ?? false,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pricing]);

  const selectedIndustryIds = useMemo(() => industries.map((i) => i.industry_id), [industries]);
  const selectedNodes = useMemo(
    () => taxonomyNodes.map((n) => ({ node_id: n.node_id, is_primary: n.is_primary })),
    [taxonomyNodes],
  );

  // Mismos siete puntos que pesa app.compute_offering_completion_pct (0091)
  // — el % viene del servidor, este checklist solo traduce ese número a
  // "qué falta" usando datos que la página ya tiene cargados.
  const completionItems = useMemo(
    () => [
      { label: 'Descripción completa', done: !!offering?.full_description, anchor: 'section-basicos' },
      { label: 'Categoría', done: taxonomyNodes.length > 0, anchor: 'section-categorias' },
      { label: 'Fotos', done: media.length > 0, anchor: 'section-fotos' },
      { label: 'Precio', done: !!pricing, anchor: 'section-precio' },
      { label: 'Hashtags', done: tags.length > 0, anchor: 'section-tags' },
      {
        label: 'Especificaciones, marca o modelo',
        done: !!(offering?.specifications || offering?.brand || offering?.model),
        anchor: 'section-basicos',
      },
      { label: 'Industrias', done: industries.length > 0, anchor: 'section-industrias' },
    ],
    [offering, taxonomyNodes, media, pricing, tags, industries],
  );

  async function onSaveBasic(values) {
    try {
      await updateOffering(activeOrg.id, offeringId, {
        name: values.name,
        short_description: values.shortDescription || null,
        full_description: values.fullDescription || null,
        specifications: offering.specifications,
        applications: offering.applications,
        brand: values.brand || null,
        model: values.model || null,
        lead_time_days: values.leadTimeDays === '' ? null : values.leadTimeDays,
        moq: offering.moq,
        monthly_capacity: offering.monthly_capacity,
        capacity_unit_code: offering.capacity_unit_code,
        warranty_months: values.warrantyMonths === '' ? null : values.warrantyMonths,
        has_after_sales: values.hasAfterSales,
        availability_status: values.availabilityStatus,
        visibility: values.visibility,
      });
      toast.success('Datos guardados');
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo guardar');
    }
  }

  async function onSaveCategories(nodes) {
    try {
      await setOfferingTaxonomyNodes(activeOrg.id, offeringId, nodes);
      toast.success('Categorías actualizadas');
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo guardar');
    }
  }

  async function onSaveIndustries(ids) {
    try {
      await setOfferingIndustries(activeOrg.id, offeringId, ids);
      toast.success('Industrias actualizadas');
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo guardar');
    }
  }

  async function onSaveTags(newTags) {
    setTags(newTags);
    try {
      await setOfferingTags(activeOrg.id, offeringId, newTags);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo guardar');
      await loadAll();
    }
  }

  async function onAddTerritory(divisionId) {
    try {
      await addOfferingTerritory(activeOrg.id, offeringId, { admin_division_id: divisionId, coverage_type: 'OPERATIONAL' });
      toast.success('Cobertura agregada');
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo agregar');
    }
  }

  async function onRemoveTerritory(territoryId) {
    try {
      await removeOfferingTerritory(activeOrg.id, offeringId, territoryId);
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo eliminar');
    }
  }

  async function onSavePricing(values) {
    try {
      await setOfferingPricing(activeOrg.id, offeringId, {
        price_type: values.priceType,
        amount_min: values.amountMin === '' ? null : values.amountMin,
        amount_max: values.amountMax === '' ? null : values.amountMax,
        currency_code: values.currencyCode || null,
        unit_code: values.unitCode || null,
        valid_until: null,
        is_public: values.isPublic,
      });
      toast.success('Precio actualizado');
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo guardar');
    }
  }

  async function handleMediaUpload(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploadingMedia(true);
    try {
      await uploadOfferingMedia(activeOrg.id, offeringId, file);
      toast.success('Foto agregada');
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo subir la foto');
    } finally {
      setUploadingMedia(false);
      if (mediaInputRef.current) mediaInputRef.current.value = '';
    }
  }

  async function handleDeleteMedia(mediaId) {
    try {
      await deleteOfferingMedia(activeOrg.id, offeringId, mediaId);
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo eliminar');
    }
  }

  async function handleDocUpload(event) {
    event.preventDefault();
    const file = docInputRef.current?.files?.[0];
    const name = docNameRef.current?.value?.trim();
    if (!file || !name) {
      toast.error('Indica un nombre y selecciona un archivo PDF');
      return;
    }
    setUploadingDoc(true);
    try {
      await uploadOfferingDocument(activeOrg.id, offeringId, { name, file, isPublic: true });
      toast.success('Documento agregado');
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo subir el documento');
    } finally {
      setUploadingDoc(false);
      if (docInputRef.current) docInputRef.current.value = '';
      if (docNameRef.current) docNameRef.current.value = '';
    }
  }

  async function handleDeleteDocument(documentId) {
    try {
      await deleteOfferingDocument(activeOrg.id, offeringId, documentId);
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo eliminar');
    }
  }

  function updateAttrDraft(definitionId, value) {
    setAttrDraft((prev) => ({ ...prev, [definitionId]: value }));
  }

  function toggleMultiselect(definitionId, optionId) {
    setAttrDraft((prev) => {
      const current = prev[definitionId] ?? [];
      const next = current.includes(optionId)
        ? current.filter((id) => id !== optionId)
        : [...current, optionId];
      return { ...prev, [definitionId]: next };
    });
  }

  async function onSaveAttributes() {
    setSavingAttrs(true);
    try {
      for (const def of attributeDefs) {
        const value = attrDraft[def.attribute_definition_id];
        const payload = { attribute_definition_id: def.attribute_definition_id };
        if (def.data_type === 'MULTISELECT') {
          if (!value || value.length === 0) continue;
          payload.option_ids = value;
        } else if (def.data_type === 'SELECT') {
          if (!value) continue;
          payload.option_id = value;
        } else if (def.data_type === 'BOOLEAN') {
          payload.value_boolean = Boolean(value);
        } else if (def.data_type === 'DATE') {
          if (!value) continue;
          payload.value_date = value;
        } else if (def.data_type === 'NUMBER') {
          if (value === '' || value === undefined) continue;
          payload.value_number = Number(value);
        } else {
          if (!value) continue;
          payload.value_text = value;
        }
        await setOfferingAttributeValue(activeOrg.id, offeringId, payload);
      }
      toast.success('Atributos guardados');
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo guardar los atributos');
    } finally {
      setSavingAttrs(false);
    }
  }

  async function onPublish() {
    try {
      await publishOffering(activeOrg.id, offeringId);
      toast.success('Publicado');
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo publicar');
    }
  }

  async function onSetStatus(status) {
    try {
      await setOfferingStatus(activeOrg.id, offeringId, status);
      toast.success('Estado actualizado');
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo actualizar');
    }
  }

  async function onDelete() {
    if (!window.confirm('¿Eliminar este producto o servicio? Esta acción no se puede deshacer.')) return;
    try {
      await deleteOffering(activeOrg.id, offeringId);
      toast.success('Eliminado');
      navigate('/empresa/catalogo');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo eliminar');
    }
  }

  if (!activeOrg) return null;

  if (loading || !offering) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-64 animate-pulse rounded-lg bg-secondary" />
        <div className="h-40 animate-pulse rounded-lg bg-secondary" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <Helmet>
        <title>{offering.name} · Catálogo · Directorio de Empresas</title>
      </Helmet>

      <div>
        <Link to="/empresa/catalogo" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="size-3.5" />
          Catálogo
        </Link>
      </div>

      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-semibold tracking-tight">{offering.name}</h1>
            <Badge variant={STATUS_VARIANT[offering.status] ?? 'neutral'}>
              {STATUS_LABEL[offering.status] ?? offering.status}
            </Badge>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">/proveedores/{activeOrg.slug}/{offering.slug}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {offering.status === 'DRAFT' && (
            <Button onClick={onPublish} className="gap-1.5">
              <Rocket className="size-4" />
              Publicar
            </Button>
          )}
          {offering.status === 'ACTIVE' && (
            <Button variant="outline" onClick={() => onSetStatus('PAUSED')} className="gap-1.5">
              <Ban className="size-4" />
              Pausar
            </Button>
          )}
          {offering.status === 'PAUSED' && (
            <Button onClick={onPublish} className="gap-1.5">
              <Rocket className="size-4" />
              Reactivar
            </Button>
          )}
          {offering.status !== 'ARCHIVED' && (
            <Button variant="outline" onClick={() => onSetStatus('ARCHIVED')} className="gap-1.5">
              <Archive className="size-4" />
              Archivar
            </Button>
          )}
          <Button variant="ghost" onClick={onDelete} className="gap-1.5 text-destructive hover:text-destructive">
            <Trash2 className="size-4" />
            Eliminar
          </Button>
        </div>
      </header>

      {offering.status === 'DRAFT' && (!offering.short_description || !primaryNode) && (
        <p className="rounded-lg border border-dashed px-4 py-3 text-sm text-muted-foreground">
          Para publicar necesitas una descripción corta y al menos una categoría asignada.
        </p>
      )}

      <OfferingCompletion pct={offering.completion_pct} items={completionItems} />

      <Card id="section-basicos">
        <CardHeader>
          <CardTitle>Datos básicos</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={basicForm.handleSubmit(onSaveBasic)} className="grid gap-3 sm:grid-cols-2" noValidate>
            <div className="space-y-1.5 sm:col-span-2">
              <Label htmlFor="name">Nombre</Label>
              <Input id="name" {...basicForm.register('name')} />
              {basicForm.formState.errors.name && (
                <p className="text-xs text-destructive">{basicForm.formState.errors.name.message}</p>
              )}
            </div>
            <div className="space-y-1.5 sm:col-span-2">
              <Label htmlFor="short-description">Descripción corta</Label>
              <Input id="short-description" maxLength={280} {...basicForm.register('shortDescription')} />
            </div>
            <div className="space-y-1.5 sm:col-span-2">
              <Label htmlFor="full-description">Descripción completa</Label>
              <Textarea id="full-description" maxLength={5000} {...basicForm.register('fullDescription')} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="brand">Marca</Label>
              <Input id="brand" {...basicForm.register('brand')} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="model">Modelo</Label>
              <Input id="model" {...basicForm.register('model')} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="lead-time">Plazo de entrega (días)</Label>
              <Input id="lead-time" type="number" min={0} {...basicForm.register('leadTimeDays')} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="warranty">Garantía (meses)</Label>
              <Input id="warranty" type="number" min={0} {...basicForm.register('warrantyMonths')} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="availability">Disponibilidad</Label>
              <SelectNative id="availability" {...basicForm.register('availabilityStatus')}>
                {AVAILABILITY.map((a) => (
                  <option key={a} value={a}>{AVAILABILITY_LABELS[a]}</option>
                ))}
              </SelectNative>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="visibility">Visibilidad</Label>
              <SelectNative id="visibility" {...basicForm.register('visibility')}>
                {VISIBILITY.map((v) => (
                  <option key={v} value={v}>{VISIBILITY_LABELS[v]}</option>
                ))}
              </SelectNative>
            </div>
            <label className="flex items-center gap-2 text-sm sm:col-span-2">
              <input type="checkbox" className="size-4" {...basicForm.register('hasAfterSales')} />
              Ofrece servicio postventa
            </label>
            <div className="sm:col-span-2">
              <Button type="submit" disabled={basicForm.formState.isSubmitting}>
                {basicForm.formState.isSubmitting ? 'Guardando…' : 'Guardar'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card id="section-categorias">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Tags className="size-4 text-primary" />
            Categorías
          </CardTitle>
          <CardDescription>Qué es — clasificación en la taxonomía del directorio.</CardDescription>
        </CardHeader>
        <CardContent>
          <CategorySelector selected={selectedNodes} onChange={onSaveCategories} />
        </CardContent>
      </Card>

      <Card id="section-industrias">
        <CardHeader>
          <CardTitle>Industrias</CardTitle>
          <CardDescription>A quién le sirve este producto o servicio en particular.</CardDescription>
        </CardHeader>
        <CardContent>
          <IndustrySelector selectedIds={selectedIndustryIds} onChange={onSaveIndustries} />
        </CardContent>
      </Card>

      <Card id="section-tags">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Tags className="size-4 text-primary" />
            Hashtags
          </CardTitle>
          <CardDescription>
            Palabras clave libres para búsqueda y matching fino de este producto o servicio.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <TagInput tags={tags} onChange={onSaveTags} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MapPinned className="size-4 text-primary" />
            Cobertura territorial ({territories.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {territories.map((t) => (
              <Badge key={t.id} variant="neutral" className="gap-1.5">
                {t.name} · {COVERAGE_LABELS[t.coverage_type] ?? t.coverage_type}
                <button onClick={() => onRemoveTerritory(t.id)} aria-label="Quitar">
                  <Trash2 className="size-3" />
                </button>
              </Badge>
            ))}
            {territories.length === 0 && (
              <p className="text-sm text-muted-foreground">Todavía no hay cobertura declarada para esta oferta.</p>
            )}
          </div>
          <AdminDivisionSelector onAdd={onAddTerritory} />
        </CardContent>
      </Card>

      <Card id="section-precio">
        <CardHeader>
          <CardTitle>Precio</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={pricingForm.handleSubmit(onSavePricing)} className="grid gap-3 sm:grid-cols-2" noValidate>
            <div className="space-y-1.5">
              <Label htmlFor="price-type">Tipo</Label>
              <SelectNative id="price-type" {...pricingForm.register('priceType')}>
                {PRICE_TYPES.map((p) => (
                  <option key={p} value={p}>{PRICE_TYPE_LABELS[p]}</option>
                ))}
              </SelectNative>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="unit-code">Unidad</Label>
              <SelectNative id="unit-code" {...pricingForm.register('unitCode')}>
                <option value="">Sin especificar</option>
                {units.map((u) => (
                  <option key={u.code} value={u.code}>{u.name}</option>
                ))}
              </SelectNative>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="amount-min">Monto mínimo</Label>
              <Input id="amount-min" type="number" step="0.01" {...pricingForm.register('amountMin')} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="amount-max">Monto máximo</Label>
              <Input id="amount-max" type="number" step="0.01" {...pricingForm.register('amountMax')} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="currency-code">Moneda</Label>
              <SelectNative id="currency-code" {...pricingForm.register('currencyCode')}>
                <option value="">Sin especificar</option>
                {currencies.map((c) => (
                  <option key={c.code} value={c.code}>{c.code} — {c.name}</option>
                ))}
              </SelectNative>
            </div>
            <label className="flex items-center gap-2 self-end text-sm">
              <input type="checkbox" className="size-4" {...pricingForm.register('isPublic')} />
              Mostrar precio en el perfil público
            </label>
            <div className="sm:col-span-2">
              <Button type="submit" disabled={pricingForm.formState.isSubmitting}>
                {pricingForm.formState.isSubmitting ? 'Guardando…' : 'Guardar precio'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card id="section-fotos">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ImageIcon className="size-4 text-primary" />
            Fotos ({media.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-3">
            {media.map((m) => (
              <div key={m.id} className="group relative">
                <img src={m.url} alt={m.alt_text ?? ''} className="size-24 rounded-lg border object-cover" />
                <button
                  onClick={() => handleDeleteMedia(m.id)}
                  className="absolute -right-1.5 -top-1.5 hidden size-6 items-center justify-center rounded-full border bg-background group-hover:flex"
                  aria-label="Eliminar"
                >
                  <Trash2 className="size-3" />
                </button>
              </div>
            ))}
          </div>
          <Input
            ref={mediaInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp,image/gif"
            onChange={handleMediaUpload}
            disabled={uploadingMedia}
            className="max-w-xs"
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="size-4 text-primary" />
            Documentos técnicos ({documents.length})
          </CardTitle>
          <CardDescription>Fichas técnicas u otros PDF — hasta 20 MB.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <ul className="space-y-2">
            {documents.map((doc) => (
              <li key={doc.id} className="flex items-center justify-between gap-2 rounded-lg border px-3 py-2 text-sm">
                {doc.url ? (
                  <a href={doc.url} target="_blank" rel="noreferrer" className="font-medium hover:underline">
                    {doc.name}
                  </a>
                ) : (
                  <span className="font-medium">{doc.name}</span>
                )}
                <Button variant="ghost" size="sm" onClick={() => handleDeleteDocument(doc.id)}>
                  <Trash2 className="size-3.5" />
                </Button>
              </li>
            ))}
            {documents.length === 0 && (
              <p className="text-sm text-muted-foreground">Todavía no hay documentos.</p>
            )}
          </ul>
          <form onSubmit={handleDocUpload} className="flex flex-wrap items-end gap-2 border-t pt-4">
            <div className="space-y-1.5">
              <Label htmlFor="doc-name">Nombre</Label>
              <Input id="doc-name" ref={docNameRef} placeholder="Ficha técnica" className="w-56" />
            </div>
            <Input ref={docInputRef} type="file" accept="application/pdf" className="max-w-xs" />
            <Button type="submit" disabled={uploadingDoc} variant="outline" className="gap-1.5">
              <Upload className="size-4" />
              {uploadingDoc ? 'Subiendo…' : 'Subir'}
            </Button>
          </form>
        </CardContent>
      </Card>

      {primaryNode && attributeDefs.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sliders className="size-4 text-primary" />
              Atributos de {primaryNode.name}
            </CardTitle>
            <CardDescription>Se generan solos según la categoría principal elegida arriba.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              {attributeDefs.map((def) => (
                <AttributeField
                  key={def.attribute_definition_id}
                  def={def}
                  value={attrDraft[def.attribute_definition_id]}
                  onChange={(v) => updateAttrDraft(def.attribute_definition_id, v)}
                  onToggleOption={(optionId) => toggleMultiselect(def.attribute_definition_id, optionId)}
                />
              ))}
            </div>
            <Button onClick={onSaveAttributes} disabled={savingAttrs}>
              {savingAttrs ? 'Guardando…' : 'Guardar atributos'}
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function AttributeField({ def, value, onChange, onToggleOption }) {
  const label = def.name + (def.is_required ? ' *' : '') + (def.unit_code ? ` (${def.unit_code})` : '');

  if (def.data_type === 'BOOLEAN') {
    return (
      <label className="flex items-center gap-2 self-end text-sm">
        <input type="checkbox" className="size-4" checked={Boolean(value)} onChange={(e) => onChange(e.target.checked)} />
        {label}
      </label>
    );
  }

  if (def.data_type === 'SELECT') {
    return (
      <div className="space-y-1.5">
        <Label>{label}</Label>
        <SelectNative value={value ?? ''} onChange={(e) => onChange(e.target.value)}>
          <option value="">Sin especificar</option>
          {def.options.map((opt) => (
            <option key={opt.id} value={opt.id}>{opt.label}</option>
          ))}
        </SelectNative>
      </div>
    );
  }

  if (def.data_type === 'MULTISELECT') {
    const selected = value ?? [];
    return (
      <div className="space-y-1.5">
        <Label>{label}</Label>
        <div className="flex flex-wrap gap-3">
          {def.options.map((opt) => (
            <label key={opt.id} className="flex items-center gap-1.5 text-sm">
              <input
                type="checkbox"
                className="size-4"
                checked={selected.includes(opt.id)}
                onChange={() => onToggleOption(opt.id)}
              />
              {opt.label}
            </label>
          ))}
        </div>
      </div>
    );
  }

  if (def.data_type === 'DATE') {
    return (
      <div className="space-y-1.5">
        <Label>{label}</Label>
        <Input type="date" value={value ?? ''} onChange={(e) => onChange(e.target.value)} />
      </div>
    );
  }

  if (def.data_type === 'NUMBER') {
    return (
      <div className="space-y-1.5">
        <Label>{label}</Label>
        <Input
          type="number"
          value={value ?? ''}
          min={def.min_value ?? undefined}
          max={def.max_value ?? undefined}
          onChange={(e) => onChange(e.target.value)}
        />
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <Input value={value ?? ''} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}
