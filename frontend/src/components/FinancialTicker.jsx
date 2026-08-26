import { useEffect, useState } from 'react';
import { getIndicators } from '@/lib/indicatorsApi';

// Los tres valores se actualizan una vez al día en la fuente — sondear cada
// pocos segundos no aportaría nada, cada 30 min alcanza de sobra y evita
// pegarle a mindicador.cl más de lo necesario.
const REFRESH_MS = 30 * 60 * 1000;

const CLP_FORMAT = new Intl.NumberFormat('es-CL', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function FinancialTicker() {
  const [indicators, setIndicators] = useState(null);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        setIndicators(await getIndicators({ signal: controller.signal }));
      } catch {
        // Silencioso: es un dato decorativo del header, no bloquea nada de
        // la app si mindicador.cl no responde — se reintenta en el próximo
        // ciclo.
      }
    }
    load();
    const interval = setInterval(load, REFRESH_MS);
    return () => {
      controller.abort();
      clearInterval(interval);
    };
  }, []);

  if (!indicators) return null;

  return (
    <div className="hidden items-center divide-x divide-border rounded-lg border bg-secondary/40 text-xs text-muted-foreground lg:flex">
      <Indicator label="UF" value={indicators.uf != null ? CLP_FORMAT.format(indicators.uf) : '—'} />
      <Indicator
        label="USD"
        value={indicators.dolar != null ? `$${CLP_FORMAT.format(indicators.dolar)}` : '—'}
      />
      <Indicator
        label="EUR"
        value={indicators.euro != null ? `$${CLP_FORMAT.format(indicators.euro)}` : '—'}
      />
    </div>
  );
}

function Indicator({ label, value }) {
  return (
    <span className="flex items-center gap-1 px-3 py-1.5">
      <span className="font-semibold text-foreground/70">{label}</span>
      <span className="tabular-nums">{value}</span>
    </span>
  );
}
