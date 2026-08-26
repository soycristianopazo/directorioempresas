import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { toast } from 'sonner';
import { Factory, MapPinned, ShieldCheck, Trash2 } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { IndustrySelector } from '@/components/IndustrySelector';
import { SiiActivitySelector } from '@/components/SiiActivitySelector';
import { AdminDivisionSelector } from '@/components/AdminDivisionSelector';
import {
  getOrganizationIndustries,
  setOrganizationIndustry,
  removeOrganizationIndustry,
  getOrganizationEconomicActivities,
  setOrganizationEconomicActivity,
  removeOrganizationEconomicActivity,
  getOrganizationTerritories,
  addOrganizationTerritory,
  removeOrganizationTerritory,
} from '@/lib/organizationProfileApi';

export default function CompanyCoveragePage() {
  const { activeOrg } = useAuth();
  const [industries, setIndustries] = useState([]);
  const [economicActivities, setEconomicActivities] = useState([]);
  const [territories, setTerritories] = useState([]);
  const [loading, setLoading] = useState(true);

  async function loadAll() {
    try {
      const [inds, activities, terrs] = await Promise.all([
        getOrganizationIndustries(activeOrg.id),
        getOrganizationEconomicActivities(activeOrg.id),
        getOrganizationTerritories(activeOrg.id),
      ]);
      setIndustries(inds);
      setEconomicActivities(activities);
      setTerritories(terrs);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo cargar la cobertura');
    }
  }

  useEffect(() => {
    if (!activeOrg) return;
    setLoading(true);
    loadAll().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrg?.id]);

  const selectedIndustryIds = industries.map((i) => i.industry_id);

  async function handleIndustryChange(newIds) {
    const added = newIds.filter((id) => !selectedIndustryIds.includes(id));
    const removed = selectedIndustryIds.filter((id) => !newIds.includes(id));
    try {
      for (const id of added) {
        await setOrganizationIndustry(activeOrg.id, { industry_id: id, years_experience: null, is_primary: false });
      }
      for (const id of removed) {
        await removeOrganizationIndustry(activeOrg.id, id);
      }
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo actualizar');
    }
  }

  async function handleAddEconomicActivity(activity) {
    try {
      await setOrganizationEconomicActivity(activeOrg.id, { sii_code: activity.sii_code });
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo agregar el giro');
    }
  }

  async function handleRemoveEconomicActivity(siiCode) {
    try {
      await removeOrganizationEconomicActivity(activeOrg.id, siiCode);
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo quitar el giro');
    }
  }

  async function handleAddTerritory(divisionId) {
    try {
      await addOrganizationTerritory(activeOrg.id, divisionId);
      toast.success('Cobertura agregada');
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo agregar');
    }
  }

  async function handleRemoveTerritory(territoryId) {
    try {
      await removeOrganizationTerritory(activeOrg.id, territoryId);
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo eliminar');
    }
  }

  if (!activeOrg) return null;

  return (
    <div className="space-y-8">
      <Helmet>
        <title>Cobertura e industrias · Directorio de Empresas</title>
      </Helmet>

      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Cobertura e industrias</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          A quién le vendes y dónde puedes operar — la base del matching por dos ejes.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Factory className="size-4 text-primary" />
            Industrias que atiendes
          </CardTitle>
          <CardDescription>A quién le vendes — independiente de qué vendes.</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="h-24 animate-pulse rounded-lg bg-secondary" />
          ) : (
            <IndustrySelector selectedIds={selectedIndustryIds} onChange={handleIndustryChange} />
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShieldCheck className="size-4 text-primary" />
            Giros SII registrados
          </CardTitle>
          <CardDescription>
            Los códigos de actividad económica que tu empresa tiene registrados con el SII.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="h-24 animate-pulse rounded-lg bg-secondary" />
          ) : (
            <SiiActivitySelector
              selected={economicActivities}
              onSelect={handleAddEconomicActivity}
              onRemove={handleRemoveEconomicActivity}
            />
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MapPinned className="size-4 text-primary" />
            Cobertura territorial ({territories.length})
          </CardTitle>
          <CardDescription>Dónde puede operar tu empresa — a nivel de región, provincia o comuna.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {loading ? (
            <div className="h-16 animate-pulse rounded-lg bg-secondary" />
          ) : (
            <div className="flex flex-wrap gap-2">
              {territories.map((t) => (
                <Badge key={t.id} variant="neutral" className="gap-1.5">
                  {t.name}
                  <button onClick={() => handleRemoveTerritory(t.id)} aria-label="Quitar">
                    <Trash2 className="size-3" />
                  </button>
                </Badge>
              ))}
              {territories.length === 0 && (
                <p className="text-sm text-muted-foreground">Todavía no hay cobertura declarada.</p>
              )}
            </div>
          )}
          <AdminDivisionSelector onAdd={handleAddTerritory} />
        </CardContent>
      </Card>
    </div>
  );
}
