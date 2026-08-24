import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { MapPin, Plus, Trash2, User } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { SelectNative } from '@/components/ui/select-native';
import {
  getLocations,
  createLocation,
  deactivateLocation,
  getContacts,
  createContact,
  deactivateContact,
} from '@/lib/organizationProfileApi';

const LOCATION_TYPES = ['HEADQUARTERS', 'BRANCH', 'OPERATIONAL_BASE', 'WAREHOUSE', 'PLANT', 'OFFICE'];
const LOCATION_LABELS = {
  HEADQUARTERS: 'Casa matriz', BRANCH: 'Sucursal', OPERATIONAL_BASE: 'Base operacional',
  WAREHOUSE: 'Bodega', PLANT: 'Planta', OFFICE: 'Oficina',
};
const CONTACT_TYPES = [
  'GENERAL', 'COMERCIAL', 'VENTAS', 'GERENCIA', 'OPERACIONES', 'ABASTECIMIENTO',
  'CONTRATOS', 'FINANZAS', 'RRHH', 'HSE', 'ADMINISTRADOR_CONTRATO', 'SOPORTE_TECNICO',
];

const locationSchema = z.object({
  locationType: z.enum(LOCATION_TYPES),
  addressLine: z.string().trim().min(3, 'Ingresa la dirección'),
  isHeadquarters: z.boolean().default(false),
});

const contactSchema = z
  .object({
    fullName: z.string().trim().min(2, 'Ingresa el nombre'),
    jobTitle: z.string().trim().optional(),
    contactType: z.enum(CONTACT_TYPES),
    email: z.string().trim().email('Correo inválido').optional().or(z.literal('')),
    phone: z.string().trim().optional(),
    isPublic: z.boolean().default(false),
  })
  .refine((data) => data.email || data.phone, {
    message: 'Ingresa al menos un correo o teléfono',
    path: ['email'],
  });

export default function CompanyLocationsPage() {
  const { activeOrg } = useAuth();
  const [locations, setLocations] = useState([]);
  const [contacts, setContacts] = useState([]);
  const [loading, setLoading] = useState(true);

  async function loadAll() {
    const [locs, cons] = await Promise.all([getLocations(activeOrg.id), getContacts(activeOrg.id)]);
    setLocations(locs);
    setContacts(cons);
  }

  useEffect(() => {
    if (!activeOrg) return;
    setLoading(true);
    loadAll().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrg?.id]);

  const locationForm = useForm({
    resolver: zodResolver(locationSchema),
    defaultValues: { locationType: 'OFFICE', addressLine: '', isHeadquarters: false },
  });
  const contactForm = useForm({
    resolver: zodResolver(contactSchema),
    defaultValues: { fullName: '', jobTitle: '', contactType: 'GENERAL', email: '', phone: '', isPublic: false },
  });

  async function onCreateLocation(values) {
    try {
      await createLocation(activeOrg.id, {
        location_type: values.locationType,
        address_line: values.addressLine,
        is_headquarters: values.isHeadquarters,
      });
      toast.success('Ubicación agregada');
      locationForm.reset({ locationType: 'OFFICE', addressLine: '', isHeadquarters: false });
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo agregar la ubicación');
    }
  }

  async function onRemoveLocation(id) {
    try {
      await deactivateLocation(activeOrg.id, id);
      toast.success('Ubicación eliminada');
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo eliminar');
    }
  }

  async function onCreateContact(values) {
    try {
      await createContact(activeOrg.id, {
        full_name: values.fullName,
        job_title: values.jobTitle || null,
        contact_type: values.contactType,
        email: values.email || null,
        phone: values.phone || null,
        whatsapp: null,
        linkedin_url: null,
        is_public: values.isPublic,
        is_primary: false,
      });
      toast.success('Contacto agregado');
      contactForm.reset({ fullName: '', jobTitle: '', contactType: 'GENERAL', email: '', phone: '', isPublic: false });
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo agregar el contacto');
    }
  }

  async function onRemoveContact(id) {
    try {
      await deactivateContact(activeOrg.id, id);
      toast.success('Contacto eliminado');
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo eliminar');
    }
  }

  if (!activeOrg) return null;

  return (
    <div className="space-y-8">
      <Helmet>
        <title>Ubicaciones y contactos · Directorio de Empresas</title>
      </Helmet>

      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Ubicaciones y contactos</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Dónde opera {activeOrg.trade_name ?? activeOrg.legal_name} y quién responde.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MapPin className="size-4 text-primary" />
            Ubicaciones ({locations.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {loading ? (
            <div className="h-16 animate-pulse rounded-lg bg-secondary" />
          ) : (
            <ul className="space-y-2">
              {locations.map((loc) => (
                <li key={loc.id} className="flex items-center justify-between gap-2 rounded-lg border px-3 py-2 text-sm">
                  <div>
                    <span className="font-medium">{loc.address_line}</span>
                    <span className="ml-2 text-xs text-muted-foreground">
                      {LOCATION_LABELS[loc.location_type]}
                      {loc.is_headquarters && ' · Casa matriz'}
                    </span>
                  </div>
                  <Button variant="ghost" size="sm" onClick={() => onRemoveLocation(loc.id)}>
                    <Trash2 className="size-3.5" />
                  </Button>
                </li>
              ))}
              {locations.length === 0 && (
                <p className="text-sm text-muted-foreground">Todavía no hay ubicaciones registradas.</p>
              )}
            </ul>
          )}

          <form
            onSubmit={locationForm.handleSubmit(onCreateLocation)}
            className="grid gap-3 border-t pt-4 sm:grid-cols-[1fr_180px_auto]"
            noValidate
          >
            <div className="space-y-1.5">
              <Label htmlFor="address-line">Dirección</Label>
              <Input id="address-line" placeholder="Av. Principal 123, Antofagasta" {...locationForm.register('addressLine')} />
              {locationForm.formState.errors.addressLine && (
                <p className="text-xs text-destructive">{locationForm.formState.errors.addressLine.message}</p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="location-type">Tipo</Label>
              <SelectNative id="location-type" {...locationForm.register('locationType')}>
                {LOCATION_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {LOCATION_LABELS[t]}
                  </option>
                ))}
              </SelectNative>
            </div>
            <div className="flex items-end">
              <Button type="submit" disabled={locationForm.formState.isSubmitting} className="w-full gap-1.5">
                <Plus className="size-4" />
                Agregar
              </Button>
            </div>
            <label className="flex items-center gap-2 text-sm sm:col-span-3">
              <input type="checkbox" className="size-4" {...locationForm.register('isHeadquarters')} />
              Es la casa matriz
            </label>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="size-4 text-primary" />
            Contactos ({contacts.length})
          </CardTitle>
          <CardDescription>is_public controla si aparece en el perfil público de la empresa.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {loading ? (
            <div className="h-16 animate-pulse rounded-lg bg-secondary" />
          ) : (
            <ul className="space-y-2">
              {contacts.map((contact) => (
                <li key={contact.id} className="flex items-center justify-between gap-2 rounded-lg border px-3 py-2 text-sm">
                  <div>
                    <span className="font-medium">{contact.full_name}</span>{' '}
                    <span className="text-xs text-muted-foreground">
                      {contact.job_title && `${contact.job_title} · `}
                      {contact.email || contact.phone}
                    </span>
                    {contact.is_public && <Badge variant="neutral" className="ml-2 text-[10px]">público</Badge>}
                  </div>
                  <Button variant="ghost" size="sm" onClick={() => onRemoveContact(contact.id)}>
                    <Trash2 className="size-3.5" />
                  </Button>
                </li>
              ))}
              {contacts.length === 0 && (
                <p className="text-sm text-muted-foreground">Todavía no hay contactos registrados.</p>
              )}
            </ul>
          )}

          <form
            onSubmit={contactForm.handleSubmit(onCreateContact)}
            className="grid gap-3 border-t pt-4 sm:grid-cols-2"
            noValidate
          >
            <div className="space-y-1.5">
              <Label htmlFor="contact-name">Nombre</Label>
              <Input id="contact-name" {...contactForm.register('fullName')} />
              {contactForm.formState.errors.fullName && (
                <p className="text-xs text-destructive">{contactForm.formState.errors.fullName.message}</p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="contact-title">Cargo</Label>
              <Input id="contact-title" {...contactForm.register('jobTitle')} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="contact-type">Área</Label>
              <SelectNative id="contact-type" {...contactForm.register('contactType')}>
                {CONTACT_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </SelectNative>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="contact-email">Correo</Label>
              <Input id="contact-email" type="email" {...contactForm.register('email')} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="contact-phone">Teléfono</Label>
              <Input id="contact-phone" {...contactForm.register('phone')} />
              {contactForm.formState.errors.email && (
                <p className="text-xs text-destructive">{contactForm.formState.errors.email.message}</p>
              )}
            </div>
            <label className="flex items-center gap-2 self-end text-sm">
              <input type="checkbox" className="size-4" {...contactForm.register('isPublic')} />
              Visible en el perfil público
            </label>
            <div className="sm:col-span-2">
              <Button type="submit" disabled={contactForm.formState.isSubmitting} className="gap-1.5">
                <Plus className="size-4" />
                Agregar contacto
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
