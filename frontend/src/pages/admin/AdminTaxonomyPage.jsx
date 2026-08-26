import { useCallback, useEffect, useMemo, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { useForm, useFieldArray, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { ChevronRight, Plus, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { SelectNative } from '@/components/ui/select-native';
import { cn } from '@/lib/utils';
import {
  getTaxonomyTree,
  getIndustries,
  getNodeAttributes,
  createTaxonomyNode,
  createIndustry,
  createAttributeDefinition,
  linkAttributeToNode,
} from '@/lib/taxonomyApi';

const NODE_TYPES = ['CATEGORY', 'SUBCATEGORY', 'SPECIALTY', 'SERVICE', 'PRODUCT'];
const RISK_LEVELS = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];
const DATA_TYPES = ['TEXT', 'NUMBER', 'BOOLEAN', 'DATE', 'SELECT', 'MULTISELECT', 'RANGE'];
const SELECT_LIKE = new Set(['SELECT', 'MULTISELECT']);

const nodeSchema = z.object({
  name: z.string().trim().min(2, 'Mínimo 2 caracteres'),
  nodeType: z.enum(NODE_TYPES),
  riskLevel: z.string().optional(),
  description: z.string().trim().optional(),
});

const industrySchema = z.object({
  name: z.string().trim().min(2, 'Mínimo 2 caracteres'),
});

const attributeSchema = z
  .object({
    code: z
      .string()
      .trim()
      .min(2, 'Mínimo 2 caracteres')
      .regex(/^[a-z][a-z0-9_]*$/, 'minúsculas, números y guion bajo, empieza con letra'),
    name: z.string().trim().min(2, 'Mínimo 2 caracteres'),
    dataType: z.enum(DATA_TYPES),
    unitCode: z.string().trim().optional(),
    helpText: z.string().trim().optional(),
    isRequired: z.boolean().default(false),
    options: z.array(z.object({ value: z.string().trim(), label: z.string().trim() })),
  })
  .refine(
    (data) => !SELECT_LIKE.has(data.dataType) || data.options.some((o) => o.value && o.label),
    { message: 'Agrega al menos una opción', path: ['options'] },
  );

export default function AdminTaxonomyPage() {
  const [tab, setTab] = useState('categories');
  const [taxonomyTree, setTaxonomyTree] = useState([]);
  const [industryTree, setIndustryTree] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState(null);

  const isTaxonomy = tab === 'categories';
  const tree = isTaxonomy ? taxonomyTree : industryTree;

  const loadTaxonomy = useCallback(async () => {
    setTaxonomyTree(await getTaxonomyTree());
  }, []);

  const loadIndustries = useCallback(async () => {
    setIndustryTree(await getIndustries());
  }, []);

  useEffect(() => {
    setLoading(true);
    Promise.all([loadTaxonomy(), loadIndustries()])
      .catch(() => toast.error('No se pudo cargar la taxonomía'))
      .finally(() => setLoading(false));
  }, [loadTaxonomy, loadIndustries]);

  useEffect(() => {
    setSelectedId(null);
  }, [tab]);

  const flatNodes = useMemo(() => flatten(tree), [tree]);
  const selectedNode = flatNodes.find((n) => n.id === selectedId) ?? null;

  async function handleReload() {
    if (isTaxonomy) await loadTaxonomy();
    else await loadIndustries();
  }

  return (
    <div className="space-y-6">
      <Helmet>
        <title>Backoffice · Taxonomía</title>
      </Helmet>

      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Taxonomía e industrias</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Qué se vende (categorías) y a quién se le vende (industrias) — dos árboles
          independientes. Ver docs/01-ARQUITECTURA.md §D.2.
        </p>
      </header>

      <div className="flex gap-1 border-b">
        <TabButton active={isTaxonomy} onClick={() => setTab('categories')}>
          Categorías
        </TabButton>
        <TabButton active={!isTaxonomy} onClick={() => setTab('industries')}>
          Industrias
        </TabButton>
      </div>

      {loading ? (
        <div className="h-64 animate-pulse rounded-xl bg-secondary" />
      ) : (
        <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                {isTaxonomy ? 'Árbol de categorías' : 'Árbol de industrias'}
              </CardTitle>
              <CardDescription>{flatNodes.length} nodos activos</CardDescription>
            </CardHeader>
            <CardContent className="max-h-[32rem] overflow-y-auto p-2">
              {tree.length === 0 ? (
                <p className="px-3 py-6 text-center text-sm text-muted-foreground">
                  Todavía no hay nodos raíz.
                </p>
              ) : (
                <TreeList nodes={tree} selectedId={selectedId} onSelect={setSelectedId} />
              )}
            </CardContent>
          </Card>

          <div className="space-y-6">
            <NewNodeCard
              isTaxonomy={isTaxonomy}
              parentNode={selectedNode}
              onCreated={async (id) => {
                await handleReload();
                setSelectedId(id);
              }}
            />

            {selectedNode && (
              <NodeDetailCard
                key={selectedNode.id}
                node={selectedNode}
                isTaxonomy={isTaxonomy}
                onReload={handleReload}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function TabButton({ active, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'border-b-2 px-4 py-2 text-sm font-medium transition-colors',
        active
          ? 'border-primary text-foreground'
          : 'border-transparent text-muted-foreground hover:text-foreground',
      )}
    >
      {children}
    </button>
  );
}

function flatten(nodes, acc = []) {
  for (const node of nodes) {
    acc.push(node);
    if (node.children?.length) flatten(node.children, acc);
  }
  return acc;
}

function TreeList({ nodes, selectedId, onSelect, depth = 0 }) {
  return (
    <ul className={depth === 0 ? 'space-y-0.5' : 'ml-4 space-y-0.5 border-l pl-2'}>
      {nodes.map((node) => (
        <li key={node.id}>
          <button
            type="button"
            onClick={() => onSelect(node.id)}
            className={cn(
              'flex w-full items-center gap-1.5 rounded-lg px-2 py-1.5 text-left text-sm hover:bg-accent',
              selectedId === node.id && 'bg-accent font-medium',
            )}
          >
            {node.children?.length > 0 && (
              <ChevronRight className="size-3.5 shrink-0 text-muted-foreground" />
            )}
            <span className="truncate">{node.name}</span>
            {node.node_type && (
              <Badge variant="neutral" className="ml-auto shrink-0 text-[10px]">
                {node.node_type}
              </Badge>
            )}
          </button>
          {node.children?.length > 0 && (
            <TreeList
              nodes={node.children}
              selectedId={selectedId}
              onSelect={onSelect}
              depth={depth + 1}
            />
          )}
        </li>
      ))}
    </ul>
  );
}

function NewNodeCard({ isTaxonomy, parentNode, onCreated }) {
  const schema = isTaxonomy ? nodeSchema : industrySchema;
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues: isTaxonomy
      ? { name: '', nodeType: 'SUBCATEGORY', riskLevel: '', description: '' }
      : { name: '' },
  });

  async function onSubmit(values) {
    try {
      let id;
      if (isTaxonomy) {
        id = await createTaxonomyNode({
          parent_id: parentNode?.id ?? null,
          name: values.name,
          node_type: values.nodeType,
          risk_level: values.riskLevel || null,
          description: values.description || null,
        });
      } else {
        id = await createIndustry({ parent_id: parentNode?.id ?? null, name: values.name });
      }
      toast.success(parentNode ? 'Subcategoría creada' : 'Categoría raíz creada');
      reset();
      await onCreated(id);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo crear');
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">
          {parentNode ? `Agregar bajo "${parentNode.name}"` : 'Agregar categoría raíz'}
        </CardTitle>
        <CardDescription>
          {parentNode
            ? 'Selecciona otro nodo en el árbol, o ninguno, para crear en otro nivel.'
            : 'Sin nodo seleccionado en el árbol: esto crea un nuevo nodo raíz.'}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="grid gap-3 sm:grid-cols-2" noValidate>
          <div className="space-y-1.5 sm:col-span-2">
            <Label htmlFor="node-name">Nombre</Label>
            <Input id="node-name" {...register('name')} />
            {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
          </div>

          {isTaxonomy && (
            <>
              <div className="space-y-1.5">
                <Label htmlFor="node-type">Tipo</Label>
                <SelectNative id="node-type" {...register('nodeType')}>
                  {NODE_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </SelectNative>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="node-risk">Nivel de riesgo</Label>
                <SelectNative id="node-risk" {...register('riskLevel')}>
                  <option value="">Sin definir</option>
                  {RISK_LEVELS.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </SelectNative>
              </div>
              <div className="space-y-1.5 sm:col-span-2">
                <Label htmlFor="node-description">Descripción</Label>
                <Textarea id="node-description" rows={2} {...register('description')} />
              </div>
            </>
          )}

          <div className="sm:col-span-2">
            <Button type="submit" disabled={isSubmitting} className="gap-1.5">
              <Plus className="size-4" />
              {isSubmitting ? 'Creando…' : 'Crear'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

function NodeDetailCard({ node, isTaxonomy, onReload }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2">
          <CardTitle className="text-base">{node.name}</CardTitle>
          {node.node_type && <Badge variant="brand">{node.node_type}</Badge>}
          {node.risk_level && <Badge variant="warning">{node.risk_level}</Badge>}
        </div>
        <CardDescription>
          slug: <code>{node.slug}</code> · path: <code>{node.path}</code>
        </CardDescription>
      </CardHeader>
      {isTaxonomy && (
        <CardContent>
          <AttributesSection node={node} onReload={onReload} />
        </CardContent>
      )}
    </Card>
  );
}

function AttributesSection({ node, onReload }) {
  const [attributes, setAttributes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setAttributes(await getNodeAttributes(node.id));
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudieron cargar los atributos');
    } finally {
      setLoading(false);
    }
  }, [node.id]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Atributos efectivos</h3>
        <Button variant="outline" size="sm" onClick={() => setShowForm((v) => !v)} className="gap-1.5">
          <Plus className="size-3.5" />
          Agregar atributo
        </Button>
      </div>

      {loading ? (
        <div className="h-10 animate-pulse rounded-lg bg-secondary" />
      ) : attributes.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Ninguno todavía — ni propio ni heredado de un ancestro.
        </p>
      ) : (
        <ul className="space-y-1.5">
          {attributes.map((attr) => (
            <li
              key={attr.attribute_definition_id}
              className="flex items-center justify-between rounded-lg border px-3 py-2 text-sm"
            >
              <div className="min-w-0">
                <span className="font-medium">{attr.name}</span>{' '}
                <code className="text-xs text-muted-foreground">{attr.code}</code>
                {attr.is_required && (
                  <Badge variant="destructive" className="ml-2 text-[10px]">
                    requerido
                  </Badge>
                )}
                {!attr.is_direct && (
                  <Badge variant="neutral" className="ml-2 text-[10px]">
                    heredado
                  </Badge>
                )}
              </div>
              <Badge variant="neutral">{attr.data_type}</Badge>
            </li>
          ))}
        </ul>
      )}

      {showForm && (
        <NewAttributeForm
          node={node}
          onDone={async () => {
            setShowForm(false);
            await load();
            await onReload();
          }}
        />
      )}
    </div>
  );
}

function NewAttributeForm({ node, onDone }) {
  const {
    register,
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(attributeSchema),
    defaultValues: {
      code: '',
      name: '',
      dataType: 'TEXT',
      unitCode: '',
      helpText: '',
      isRequired: false,
      options: [],
    },
  });
  const { fields, append, remove } = useFieldArray({ control, name: 'options' });
  const dataType = useWatch({ control, name: 'dataType' });
  const needsOptions = SELECT_LIKE.has(dataType);

  async function onSubmit(values) {
    try {
      const definitionId = await createAttributeDefinition({
        code: values.code,
        name: values.name,
        data_type: values.dataType,
        unit_code: values.unitCode || null,
        help_text: values.helpText || null,
        options: needsOptions ? values.options.filter((o) => o.value && o.label) : [],
      });
      await linkAttributeToNode(node.id, {
        attribute_definition_id: definitionId,
        applies_to: 'OFFERING',
        is_required: values.isRequired,
        is_inherited: true,
      });
      toast.success('Atributo creado y vinculado');
      await onDone();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo crear el atributo');
    }
  }

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      className="grid gap-3 rounded-lg border bg-secondary/30 p-3 sm:grid-cols-2"
      noValidate
    >
      <div className="space-y-1.5">
        <Label htmlFor="attr-code">Código</Label>
        <Input id="attr-code" placeholder="vehicle_year" {...register('code')} />
        {errors.code && <p className="text-xs text-destructive">{errors.code.message}</p>}
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="attr-name">Nombre</Label>
        <Input id="attr-name" placeholder="Año del vehículo" {...register('name')} />
        {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="attr-type">Tipo de dato</Label>
        <SelectNative id="attr-type" {...register('dataType')}>
          {DATA_TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </SelectNative>
      </div>
      <div className="flex items-end gap-2">
        <input id="attr-required" type="checkbox" className="size-4" {...register('isRequired')} />
        <Label htmlFor="attr-required" className="mb-0">
          Obligatorio
        </Label>
      </div>

      {needsOptions && (
        <div className="space-y-2 sm:col-span-2">
          <Label>Opciones</Label>
          {fields.map((field, index) => (
            <div key={field.id} className="flex gap-2">
              <Input placeholder="valor" {...register(`options.${index}.value`)} />
              <Input placeholder="etiqueta" {...register(`options.${index}.label`)} />
              <Button type="button" variant="ghost" size="icon" onClick={() => remove(index)}>
                <Trash2 className="size-4" />
              </Button>
            </div>
          ))}
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => append({ value: '', label: '' })}
          >
            Agregar opción
          </Button>
          {errors.options && (
            <p className="text-xs text-destructive">{errors.options.message}</p>
          )}
        </div>
      )}

      <div className="sm:col-span-2">
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Guardando…' : 'Guardar atributo'}
        </Button>
      </div>
    </form>
  );
}
