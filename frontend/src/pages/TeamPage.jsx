import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { useAuth } from '@/context/AuthContext';
import {
  inviteMember,
  listAssignableRoles,
  listPendingInvitations,
  listTeam,
  removeMember,
  revokeInvitation,
} from '@/lib/organizationsApi';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { SelectNative } from '@/components/ui/select-native';

const schema = z.object({
  email: z.string().trim().toLowerCase().email('Correo inválido'),
  roleCode: z.string().min(1, 'Selecciona un rol'),
});

function initials(name) {
  if (!name) return '?';
  return name.trim().split(/\s+/).slice(0, 2).map((p) => p[0]?.toUpperCase()).join('');
}

function formatDate(value) {
  if (!value) return '—';
  return new Intl.DateTimeFormat('es-CL', { dateStyle: 'medium' }).format(new Date(value));
}

export default function TeamPage() {
  const { activeOrg, user } = useAuth();
  const [team, setTeam] = useState([]);
  const [roles, setRoles] = useState([]);
  const [invitations, setInvitations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [acceptUrl, setAcceptUrl] = useState(null);
  // Se infiere del propio 403, no de una lista de roles hardcodeada en el
  // frontend: la autoridad sobre quién puede administrar el equipo es el
  // backend (member.manage), y duplicar esa regla aquí solo crea una segunda
  // fuente de verdad que puede desalinearse.
  const [canManage, setCanManage] = useState(true);

  async function loadAll() {
    try {
      // listTeam y listAssignableRoles solo exigen member.read (VIEWER lo
      // tiene); listPendingInvitations exige member.manage y por eso se aísla:
      // un 403 ahí no debe tumbar el resto de la página, solo ocultar la
      // sección de invitaciones.
      const [team, roles] = await Promise.all([listTeam(activeOrg.id), listAssignableRoles(activeOrg.id)]);
      setTeam(team);
      setRoles(roles);

      try {
        setInvitations(await listPendingInvitations(activeOrg.id));
        setCanManage(true);
      } catch (error) {
        if (error.response?.status === 403) {
          setCanManage(false);
          setInvitations([]);
        } else {
          throw error;
        }
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo cargar el equipo');
    }
  }

  useEffect(() => {
    if (!activeOrg) return;
    setLoading(true);
    loadAll().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrg?.id]);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm({ resolver: zodResolver(schema), defaultValues: { email: '', roleCode: '' } });

  async function onInvite(values) {
    try {
      const result = await inviteMember({ organizationId: activeOrg.id, email: values.email, roleCode: values.roleCode });
      setAcceptUrl(result.accept_url);
      toast.success('Invitación creada');
      reset({ email: '', roleCode: values.roleCode });
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo crear la invitación');
    }
  }

  async function handleRemove(member) {
    const label = member.full_name ?? 'este miembro';
    if (!window.confirm(`¿Quitar a ${label} de la organización?`)) return;
    try {
      await removeMember(activeOrg.id, member.member_id);
      toast.success('Miembro removido');
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo remover');
    }
  }

  async function handleRevoke(invitationId) {
    try {
      await revokeInvitation(activeOrg.id, invitationId);
      toast.success('Invitación revocada');
      await loadAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo revocar');
    }
  }

  if (!activeOrg) return null;

  return (
    <div className="space-y-8">
      <Helmet>
        <title>Equipo · Directorio de Empresas</title>
      </Helmet>

      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Equipo</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Personas con acceso a {activeOrg.trade_name ?? activeOrg.legal_name}.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Miembros ({team.length})</CardTitle>
          <CardDescription>
            Cada persona puede tener varios roles. Los permisos son la suma de todos ellos.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="space-y-2 p-5">
              <div className="h-12 animate-pulse rounded-lg bg-secondary" />
              <div className="h-12 animate-pulse rounded-lg bg-secondary/60" />
            </div>
          ) : team.length === 0 ? (
            <div className="p-5">
              <EmptyState title="Todavía no hay nadie más" description="Invita a las personas de tu equipo que necesitan acceso." />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <caption className="sr-only">Miembros de la organización</caption>
                <thead className="border-b text-left text-xs text-muted-foreground">
                  <tr>
                    <th scope="col" className="px-5 py-2 font-medium">Persona</th>
                    <th scope="col" className="px-5 py-2 font-medium">Roles</th>
                    <th scope="col" className="px-5 py-2 font-medium">Desde</th>
                    <th scope="col" className="px-5 py-2" />
                  </tr>
                </thead>
                <tbody>
                  {team.map((m) => (
                    <tr key={m.member_id} className="border-b last:border-0">
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-3">
                          <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-secondary text-xs font-medium">
                            {initials(m.full_name ?? m.email)}
                          </span>
                          <span className="min-w-0">
                            <span className="block truncate font-medium">
                              {m.full_name ?? 'Sin nombre'}
                              {m.user_id === user?.id && <span className="ml-2 text-xs font-normal text-muted-foreground">(tú)</span>}
                            </span>
                            {m.email && <span className="block truncate text-xs text-muted-foreground">{m.email}</span>}
                          </span>
                        </div>
                      </td>
                      <td className="px-5 py-3">
                        <div className="flex flex-wrap gap-1">
                          {m.roles.length > 0 ? (
                            m.roles.map((r) => <Badge key={r.id}>{r.name}</Badge>)
                          ) : (
                            <span className="text-xs text-muted-foreground">Sin rol</span>
                          )}
                        </div>
                      </td>
                      <td className="px-5 py-3 text-muted-foreground">{formatDate(m.joined_at)}</td>
                      <td className="px-5 py-3 text-right">
                        {canManage && m.user_id !== user?.id && (
                          <Button variant="ghost" size="sm" onClick={() => handleRemove(m)}>
                            Quitar
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {canManage && (
        <Card>
          <CardHeader>
            <CardTitle>Invitar a alguien</CardTitle>
            <CardDescription>La invitación vence en 7 días y solo puede aceptarla el correo indicado.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <form onSubmit={handleSubmit(onInvite)} className="grid gap-3 sm:grid-cols-[1fr_200px_auto]" noValidate>
              <div className="space-y-1.5">
                <Label htmlFor="invite-email">Correo</Label>
                <Input id="invite-email" type="email" placeholder="persona@empresa.cl" {...register('email')} />
                {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="invite-role">Rol</Label>
                <SelectNative id="invite-role" {...register('roleCode')}>
                  <option value="">Selecciona un rol</option>
                  {roles.map((r) => (
                    <option key={r.code} value={r.code}>
                      {r.name}
                    </option>
                  ))}
                </SelectNative>
                {errors.roleCode && <p className="text-xs text-destructive">{errors.roleCode.message}</p>}
              </div>
              <div className="flex items-end">
                <Button type="submit" disabled={isSubmitting} className="w-full sm:w-auto">
                  {isSubmitting ? 'Creando…' : 'Invitar'}
                </Button>
              </div>
            </form>

            {acceptUrl && (
              <div className="rounded-lg border bg-secondary/40 p-3 text-sm">
                <p className="font-medium">Enlace de invitación</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  El envío automático por correo llega en una fase posterior. Por ahora, comparte este enlace:
                </p>
                <code className="mt-2 block overflow-x-auto rounded bg-background px-2 py-1.5 text-xs">{acceptUrl}</code>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {invitations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Invitaciones pendientes ({invitations.length})</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {invitations.map((inv) => (
              <div key={inv.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border px-3 py-2 text-sm">
                <span>{inv.email}</span>
                <span className="flex items-center gap-3 text-xs text-muted-foreground">
                  {inv.role?.name ?? '—'} · vence {formatDate(inv.expires_at)}
                  <Button variant="ghost" size="sm" onClick={() => handleRevoke(inv.id)}>
                    Revocar
                  </Button>
                </span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function EmptyState({ title, description }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed px-6 py-12 text-center">
      <p className="font-medium">{title}</p>
      {description && <p className="max-w-md text-sm text-muted-foreground">{description}</p>}
    </div>
  );
}
