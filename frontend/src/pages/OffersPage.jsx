import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { Ban, Flame, Minus, Plus, X } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { SelectNative } from '@/components/ui/select-native';
import { getCurrencies, getUnitsOfMeasure } from '@/lib/referenceApi';
import {
  listOfferings,
  listOrgDeals,
  createDeal,
  updateDealStock,
  cancelDeal,
} from '@/lib/offeringsApi';

function formatDateTime(value) {
  if (!value) return '—';
  return new Intl.DateTimeFormat('es-CL', { dateStyle: 'medium', timeStyle: 'short' }).format(
    new Date(value),
  );
}

function timeLeft(expiresAt) {
  const ms = new Date(expiresAt).getTime() - Date.now();
  if (ms <= 0) return 'Terminada';
  const days = Math.floor(ms / 86400000);
  const hours = Math.floor((ms % 86400000) / 3600000);
  const mins = Math.floor((ms % 3600000) / 60000);
  if (days > 0) return `${days}d ${hours}h restantes`;
  if (hours > 0) return `${hours}h ${mins}m restantes`;
  return `${mins}m restantes`;
}

/** Estado de una oferta — is_active ya viene calculado del servidor (sin
 * columna de estado persistida, ver 0092_offering_deals.sql); acá solo se
 * distingue POR QUÉ terminó, para mostrarlo. */
function dealStatus(deal) {
  if (deal.is_active) return { label: 'Vigente', variant: 'success' };
  if (deal.cancelled_at) return { label: 'Cancelada', variant: 'neutral' };
  if (deal.stock_quantity != null && deal.stock_remaining <= 0) {
    return { label: 'Agotada', variant: 'warning' };
  }
  return { label: 'Terminada', variant: 'neutral' };
}

export default function OffersPage() {
  const { activeOrg } = useAuth();
  const [deals, setDeals] = useState([]);
  const [offerings, setOfferings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);

  async function load() {
    try {
      const [dealRows, offeringRows] = await Promise.all([
        listOrgDeals(activeOrg.id),
        listOfferings(activeOrg.id),
      ]);
      setDeals(dealRows);
      setOfferings(offeringRows);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudieron cargar las ofertas');
    }
  }

  useEffect(() => {
    if (!activeOrg) return;
    setLoading(true);
    load().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrg?.id]);

  async function handleDecrement(deal) {
    const next = Math.max(0, deal.stock_remaining - 1);
    try {
      await updateDealStock(activeOrg.id, deal.offering_id, deal.id, next);
      await load();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo actualizar el stock');
    }
  }

  async function handleCancel(deal) {
    if (!window.confirm('¿Terminar esta oferta ahora?')) return;
    try {
      await cancelDeal(activeOrg.id, deal.offering_id, deal.id);
      toast.success('Oferta terminada');
      await load();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo terminar la oferta');
    }
  }

  const eligibleOfferings = offerings.filter(
    (o) => !deals.some((d) => d.offering_id === o.id && d.is_active),
  );

  if (!activeOrg) return null;

  return (
    <div className="space-y-6">
      <Helmet>
        <title>Ofertas · Directorio de Empresas</title>
      </Helmet>

      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
            <Flame className="size-6 text-destructive" />
            Ofertas
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Publica un producto o servicio de tu catálogo con precio rebajado, hasta agotar
            stock o con cuenta regresiva. Se muestra con un destacado en el buscador público.
          </p>
        </div>
        <Button onClick={() => setShowForm((v) => !v)} className="gap-1.5">
          {showForm ? <X className="size-4" /> : <Plus className="size-4" />}
          {showForm ? 'Cancelar' : 'Nueva oferta'}
        </Button>
      </header>

      {showForm && (
        <NewDealForm
          organizationId={activeOrg.id}
          offerings={eligibleOfferings}
          onCreated={() => {
            setShowForm(false);
            load();
          }}
        />
      )}

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="space-y-2 p-5">
              <div className="h-16 animate-pulse rounded-lg bg-secondary" />
              <div className="h-16 animate-pulse rounded-lg bg-secondary/60" />
            </div>
          ) : deals.length === 0 ? (
            <div className="flex flex-col items-center gap-2 px-6 py-16 text-center">
              <Flame className="size-8 text-muted-foreground" />
              <p className="font-medium">Todavía no tienes ofertas</p>
              <p className="max-w-sm text-sm text-muted-foreground">
                Elige un producto o servicio ya publicado en tu Catálogo y ofrécelo con un
                precio especial por tiempo o stock limitado.
              </p>
            </div>
          ) : (
            <ul className="divide-y">
              {deals.map((deal) => {
                const st = dealStatus(deal);
                return (
                  <li key={deal.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-4">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <Link
                          to={`/empresa/catalogo/${deal.offering_id}`}
                          className="font-medium hover:underline"
                        >
                          {deal.offering_name}
                        </Link>
                        <Badge variant={st.variant}>{st.label}</Badge>
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {deal.original_price && (
                          <span className="mr-1.5 line-through">
                            {deal.original_price} {deal.currency_code}
                          </span>
                        )}
                        <span className="font-medium text-foreground">
                          {deal.deal_price} {deal.currency_code}
                        </span>
                        {deal.unit_code && ` / ${deal.unit_code}`}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {deal.stock_quantity != null
                          ? `Stock: quedan ${deal.stock_remaining} de ${deal.stock_quantity}`
                          : `Vence: ${formatDateTime(deal.expires_at)}${
                              deal.is_active ? ` · ${timeLeft(deal.expires_at)}` : ''
                            }`}
                      </p>
                    </div>
                    {deal.is_active && (
                      <div className="flex shrink-0 items-center gap-1.5">
                        {deal.stock_quantity != null && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleDecrement(deal)}
                            className="gap-1"
                          >
                            <Minus className="size-3.5" />
                            Vendida 1
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleCancel(deal)}
                          className="gap-1.5 text-destructive hover:text-destructive"
                        >
                          <Ban className="size-3.5" />
                          Terminar
                        </Button>
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

const LIMIT_STOCK = 'STOCK';
const LIMIT_COUNTDOWN = 'COUNTDOWN';

function NewDealForm({ organizationId, offerings, onCreated }) {
  const [offeringId, setOfferingId] = useState('');
  const [dealPrice, setDealPrice] = useState('');
  const [originalPrice, setOriginalPrice] = useState('');
  const [currencyCode, setCurrencyCode] = useState('');
  const [unitCode, setUnitCode] = useState('');
  const [limitMode, setLimitMode] = useState(LIMIT_STOCK);
  const [stockQuantity, setStockQuantity] = useState('');
  const [expiresAt, setExpiresAt] = useState('');
  const [currencies, setCurrencies] = useState([]);
  const [units, setUnits] = useState([]);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    getCurrencies().then(setCurrencies).catch(() => {});
    getUnitsOfMeasure().then(setUnits).catch(() => {});
  }, []);

  async function onSubmit(e) {
    e.preventDefault();
    if (!offeringId || !dealPrice || !currencyCode) {
      toast.error('Completa producto/servicio, precio y moneda');
      return;
    }
    if (limitMode === LIMIT_STOCK && !stockQuantity) {
      toast.error('Indica el stock disponible');
      return;
    }
    if (limitMode === LIMIT_COUNTDOWN && !expiresAt) {
      toast.error('Indica cuándo termina la oferta');
      return;
    }
    setSubmitting(true);
    try {
      await createDeal(organizationId, offeringId, {
        dealPrice: Number(dealPrice),
        originalPrice: originalPrice ? Number(originalPrice) : null,
        currencyCode,
        unitCode: unitCode || null,
        stockQuantity: limitMode === LIMIT_STOCK ? Number(stockQuantity) : null,
        expiresAt: limitMode === LIMIT_COUNTDOWN ? new Date(expiresAt).toISOString() : null,
      });
      toast.success('Oferta publicada');
      onCreated();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo publicar la oferta');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Nueva oferta</CardTitle>
        <CardDescription>
          {offerings.length === 0
            ? 'Todos tus productos/servicios ya tienen una oferta vigente, o aún no tienes catálogo.'
            : 'Se basa en un producto o servicio que ya tienes en el Catálogo.'}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="grid gap-3 sm:grid-cols-2" noValidate>
          <div className="space-y-1.5 sm:col-span-2">
            <Label>Producto o servicio</Label>
            <SelectNative value={offeringId} onChange={(e) => setOfferingId(e.target.value)}>
              <option value="">Elige uno de tu catálogo…</option>
              {offerings.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.name}
                </option>
              ))}
            </SelectNative>
          </div>

          <div className="space-y-1.5">
            <Label>Precio de oferta</Label>
            <Input type="number" step="0.01" min="0" value={dealPrice} onChange={(e) => setDealPrice(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label>Precio original (opcional, se muestra tachado)</Label>
            <Input type="number" step="0.01" min="0" value={originalPrice} onChange={(e) => setOriginalPrice(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label>Moneda</Label>
            <SelectNative value={currencyCode} onChange={(e) => setCurrencyCode(e.target.value)}>
              <option value="">Elige…</option>
              {currencies.map((c) => (
                <option key={c.code} value={c.code}>
                  {c.code} — {c.name}
                </option>
              ))}
            </SelectNative>
          </div>
          <div className="space-y-1.5">
            <Label>Unidad (opcional)</Label>
            <SelectNative value={unitCode} onChange={(e) => setUnitCode(e.target.value)}>
              <option value="">Sin especificar</option>
              {units.map((u) => (
                <option key={u.code} value={u.code}>
                  {u.name}
                </option>
              ))}
            </SelectNative>
          </div>

          <div className="space-y-1.5 sm:col-span-2 border-t pt-3">
            <Label>Límite de la oferta</Label>
            <div className="flex gap-2">
              <Button
                type="button"
                size="sm"
                variant={limitMode === LIMIT_STOCK ? 'default' : 'outline'}
                onClick={() => setLimitMode(LIMIT_STOCK)}
              >
                Hasta agotar stock
              </Button>
              <Button
                type="button"
                size="sm"
                variant={limitMode === LIMIT_COUNTDOWN ? 'default' : 'outline'}
                onClick={() => setLimitMode(LIMIT_COUNTDOWN)}
              >
                Cuenta regresiva
              </Button>
            </div>
          </div>

          {limitMode === LIMIT_STOCK ? (
            <div className="space-y-1.5">
              <Label>Unidades disponibles</Label>
              <Input type="number" min="1" step="1" value={stockQuantity} onChange={(e) => setStockQuantity(e.target.value)} />
            </div>
          ) : (
            <div className="space-y-1.5">
              <Label>Termina el</Label>
              <Input type="datetime-local" value={expiresAt} onChange={(e) => setExpiresAt(e.target.value)} />
            </div>
          )}

          <div className="sm:col-span-2">
            <Button type="submit" disabled={submitting || offerings.length === 0} className="gap-1.5">
              <Flame className="size-4" />
              {submitting ? 'Publicando…' : 'Publicar oferta'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
