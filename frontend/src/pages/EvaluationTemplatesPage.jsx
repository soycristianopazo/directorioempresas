import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { toast } from 'sonner';
import { ClipboardList, Plus, Trash2 } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { SelectNative } from '@/components/ui/select-native';
import { listTemplates, createTemplate } from '@/lib/evaluationsApi';

const DIMENSIONS = [
  { value: 'TECHNICAL', label: 'Técnica' },
  { value: 'COMMERCIAL', label: 'Comercial' },
  { value: 'HSE', label: 'HSE' },
  { value: 'LEGAL', label: 'Legal' },
  { value: 'FINANCIAL', label: 'Financiera' },
];

function emptyCriterion() {
  return { dimension: 'TECHNICAL', name: '', weight: 20 };
}

export default function EvaluationTemplatesPage() {
  const { activeOrg } = useAuth();
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState('');
  const [criteria, setCriteria] = useState([emptyCriterion()]);

  async function load() {
    try {
      setTemplates(await listTemplates(activeOrg.id));
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudieron cargar las plantillas de evaluación');
    }
  }

  useEffect(() => {
    if (!activeOrg) return;
    setLoading(true);
    load().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrg?.id]);

  function updateCriterion(index, field, value) {
    setCriteria((prev) => prev.map((c, i) => (i === index ? { ...c, [field]: value } : c)));
  }

  async function handleCreate(e) {
    e.preventDefault();
    if (!name.trim()) return;
    const valid = criteria.filter((c) => c.name.trim());
    if (valid.length === 0) {
      toast.error('Agrega al menos un criterio');
      return;
    }
    try {
      await createTemplate(activeOrg.id, { name: name.trim(), criteria: valid });
      setName('');
      setCriteria([emptyCriterion()]);
      toast.success('Plantilla creada');
      await load();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo crear la plantilla');
    }
  }

  if (!activeOrg) return null;

  const totalWeight = criteria.reduce((sum, c) => sum + Number(c.weight || 0), 0);

  return (
    <div className="space-y-6">
      <Helmet>
        <title>Plantillas de evaluación · Directorio de Empresas</title>
      </Helmet>

      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Plantillas de evaluación</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Define los criterios y pesos con los que tu comité evalúa las ofertas recibidas.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Nueva plantilla</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleCreate} className="space-y-4">
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Ej. Transporte de personal — estándar"
              className="max-w-md"
            />

            <div className="space-y-2">
              {criteria.map((c, i) => (
                <div key={i} className="flex flex-wrap items-center gap-2">
                  <SelectNative
                    value={c.dimension}
                    onChange={(e) => updateCriterion(i, 'dimension', e.target.value)}
                    className="w-40"
                  >
                    {DIMENSIONS.map((d) => (
                      <option key={d.value} value={d.value}>
                        {d.label}
                      </option>
                    ))}
                  </SelectNative>
                  <Input
                    value={c.name}
                    onChange={(e) => updateCriterion(i, 'name', e.target.value)}
                    placeholder="Nombre del criterio"
                    className="max-w-xs"
                  />
                  <Input
                    type="number"
                    min="0"
                    value={c.weight}
                    onChange={(e) => updateCriterion(i, 'weight', e.target.value)}
                    className="w-24"
                  />
                  <span className="text-sm text-muted-foreground">peso</span>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setCriteria((prev) => prev.filter((_, idx) => idx !== i))}
                  >
                    <Trash2 className="size-3.5" />
                  </Button>
                </div>
              ))}
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="gap-1.5"
                onClick={() => setCriteria((prev) => [...prev, emptyCriterion()])}
              >
                <Plus className="size-4" />
                Agregar criterio
              </Button>
              <p className="text-xs text-muted-foreground">Suma de pesos: {totalWeight}</p>
            </div>

            <Button type="submit" className="gap-1.5">
              <Plus className="size-4" />
              Crear plantilla
            </Button>
          </form>
        </CardContent>
      </Card>

      {loading ? (
        <div className="h-24 animate-pulse rounded-lg bg-secondary" />
      ) : templates.length === 0 ? (
        <p className="rounded-lg border border-dashed px-4 py-8 text-center text-sm text-muted-foreground">
          Todavía no tienes plantillas de evaluación.
        </p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {templates.map((t) => (
            <Card key={t.id}>
              <CardHeader className="flex flex-row items-center gap-2">
                <ClipboardList className="size-4 text-primary" />
                <CardTitle className="text-base">{t.name}</CardTitle>
              </CardHeader>
              {t.description && (
                <CardContent>
                  <p className="text-sm text-muted-foreground">{t.description}</p>
                </CardContent>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
