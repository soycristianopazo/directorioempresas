import { useEffect, useState } from 'react';
import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { SelectNative } from '@/components/ui/select-native';
import { getAdminDivisions } from '@/lib/referenceApi';

/** Selector en cascada región → provincia → comuna. La cobertura se puede
 * declarar a cualquier nivel: "Agregar" usa el nivel más específico que el
 * usuario haya llegado a seleccionar (solo región, o hasta comuna).
 */
export function AdminDivisionSelector({ onAdd, disabled }) {
  const [regions, setRegions] = useState([]);
  const [provinces, setProvinces] = useState([]);
  const [comunas, setComunas] = useState([]);
  const [regionId, setRegionId] = useState('');
  const [provinceId, setProvinceId] = useState('');
  const [comunaId, setComunaId] = useState('');

  useEffect(() => {
    getAdminDivisions({ country: 'CL' }).then(setRegions);
  }, []);

  useEffect(() => {
    setProvinceId('');
    setComunaId('');
    setProvinces([]);
    setComunas([]);
    if (regionId) getAdminDivisions({ country: 'CL', parentId: regionId }).then(setProvinces);
  }, [regionId]);

  useEffect(() => {
    setComunaId('');
    setComunas([]);
    if (provinceId) getAdminDivisions({ country: 'CL', parentId: provinceId }).then(setComunas);
  }, [provinceId]);

  function handleAdd() {
    const divisionId = comunaId || provinceId || regionId;
    if (!divisionId) return;
    onAdd(divisionId);
    setRegionId('');
  }

  return (
    <div className="flex flex-wrap items-end gap-2">
      <div className="space-y-1.5">
        <SelectNative value={regionId} onChange={(e) => setRegionId(e.target.value)} disabled={disabled}>
          <option value="">Región</option>
          {regions.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name}
            </option>
          ))}
        </SelectNative>
      </div>
      {provinces.length > 0 && (
        <div className="space-y-1.5">
          <SelectNative value={provinceId} onChange={(e) => setProvinceId(e.target.value)} disabled={disabled}>
            <option value="">Provincia (opcional)</option>
            {provinces.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </SelectNative>
        </div>
      )}
      {comunas.length > 0 && (
        <div className="space-y-1.5">
          <SelectNative value={comunaId} onChange={(e) => setComunaId(e.target.value)} disabled={disabled}>
            <option value="">Comuna (opcional)</option>
            {comunas.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </SelectNative>
        </div>
      )}
      <Button type="button" variant="outline" size="sm" disabled={!regionId || disabled} onClick={handleAdd} className="gap-1.5">
        <Plus className="size-3.5" />
        Agregar
      </Button>
    </div>
  );
}
