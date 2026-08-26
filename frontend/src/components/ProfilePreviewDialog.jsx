import { useState } from 'react';
import { toast } from 'sonner';
import { Eye, Loader2 } from 'lucide-react';
import { getOrganizationPreviewHtml } from '@/lib/organizationsApi';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogTrigger,
} from '@/components/ui/dialog';

/** El origen real del backend — no el `BACKEND_URL` de `lib/api.js` (ese
 * queda vacío a propósito en dev para que Axios pase por el proxy de
 * craco, que solo cubre /api). Acá necesitamos el origen de verdad porque
 * /static NO está proxeado: en dev cae al mismo default que usa
 * craco.config.js para su proxy target; en producción manda
 * REACT_APP_BACKEND_URL igual que el resto de la app. */
const ASSET_ORIGIN = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';

/** Inyecta <base> antes que cualquier otro elemento del <head> para que las
 * rutas relativas de la plantilla (CSS, links) resuelvan contra el backend
 * en vez de contra el origen del iframe srcDoc ("about:srcdoc"). */
function withBase(html) {
  return html.replace('<head>', `<head><base href="${ASSET_ORIGIN}/">`);
}

export function ProfilePreviewDialog({ organizationId }) {
  const [open, setOpen] = useState(false);
  const [html, setHtml] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleOpenChange(next) {
    setOpen(next);
    if (!next) return;
    setLoading(true);
    try {
      const raw = await getOrganizationPreviewHtml(organizationId);
      setHtml(withBase(raw));
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo cargar la vista previa');
      setOpen(false);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button type="button" variant="outline">
          <Eye className="size-4" />
          Vista previa del perfil público
        </Button>
      </DialogTrigger>
      <DialogContent className="flex h-[85vh] w-[95vw] max-w-4xl flex-col p-0">
        <DialogHeader className="border-b px-6 py-4">
          <DialogTitle>Así te verán los compradores</DialogTitle>
          <DialogDescription>
            Vista previa en vivo de tu ficha pública — no se registra como visita.
          </DialogDescription>
        </DialogHeader>
        <div className="min-h-0 flex-1">
          {loading && (
            <div className="flex h-full items-center justify-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              Cargando vista previa… puede tardar unos segundos.
            </div>
          )}
          {!loading && html && (
            <iframe
              title="Vista previa del perfil público"
              srcDoc={html}
              className="size-full border-0"
              sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"
            />
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
