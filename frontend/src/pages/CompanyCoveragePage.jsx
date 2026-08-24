import { useEffect, useRef, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { toast } from 'sonner';
import { Factory, Image as ImageIcon, MapPinned, Trash2 } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { IndustrySelector } from '@/components/IndustrySelector';
import { AdminDivisionSelector } from '@/components/AdminDivisionSelector';
import {
  getOrganizationIndustries,
  setOrganizationIndustry,
  removeOrganizationIndustry,
  getOrganizationTerritories,
  addOrganizationTerritory,
  removeOrganizationTerritory,
  getMedia,
  uploadMedia,
  deleteMedia,
} from '@/lib/organizationProfileApi';

export default function CompanyCoveragePage() {
  const { activeOrg } = useAuth();
  const [industries, setIndustries] = useState([]);
  const [territories, setTerritories] = useState([]);
  const [media, setMedia] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  async function loadAll() {
    const [inds, terrs, mediaList] = await Promise.all([
      getOrganizationIndustries(activeOrg.id),
      getOrganizationTerritories(activeOrg.id),
      getMedia(activeOrg.id),
    ]);
    setIndustries(inds);
    setTerritories(terrs);
    setMedia(mediaList);
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

  async function handleLogoUpload(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await uploadMedia(activeOrg.id, { mediaType: 'LOGO', file });
      toast.success('Logo actualizado');
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo subir el logo');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }

  async function handleDeleteMedia(mediaId) {
    try {
      await deleteMedia(activeOrg.id, mediaId);
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo eliminar');
    }
  }

  if (!activeOrg) return null;
  const logo = media.find((m) => m.media_type === 'LOGO');

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
            <ImageIcon className="size-4 text-primary" />
            Logo
          </CardTitle>
        </CardHeader>
        <CardContent className="flex items-center gap-4">
          {logo ? (
            <img src={logo.url} alt="Logo" className="size-16 rounded-lg border object-contain p-1" />
          ) : (
            <div className="flex size-16 items-center justify-center rounded-lg border border-dashed text-xs text-muted-foreground">
              Sin logo
            </div>
          )}
          <div className="flex items-center gap-2">
            <Input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp,image/gif"
              onChange={handleLogoUpload}
              disabled={uploading}
              className="max-w-xs"
            />
            {logo && (
              <Button variant="ghost" size="sm" onClick={() => handleDeleteMedia(logo.id)}>
                <Trash2 className="size-3.5" />
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

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
