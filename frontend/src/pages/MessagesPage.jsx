import { useEffect, useRef, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';
import { MessageSquare } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ConversationPanel } from '@/components/ConversationPanel';
import { cn } from '@/lib/utils';
import { getOrCreateConversation, listConversations } from '@/lib/messagingApi';

const LIST_POLL_INTERVAL_MS = 5000;

function participantNames(conversation) {
  return conversation.participants.map((p) => p.name).join(', ') || 'Conversación';
}

function formatRelative(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return new Intl.DateTimeFormat('es-CL', { dateStyle: 'short', timeStyle: 'short' }).format(date);
}

export default function MessagesPage() {
  const { activeOrg } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState(null);
  const openedWithOrgRef = useRef(null);

  async function loadConversations() {
    try {
      const rows = await listConversations(activeOrg.id);
      setConversations(rows);
      return rows;
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudieron cargar tus conversaciones');
      return [];
    }
  }

  useEffect(() => {
    if (!activeOrg) return;
    let cancelled = false;
    setLoading(true);
    loadConversations().finally(() => {
      if (!cancelled) setLoading(false);
    });
    const interval = setInterval(loadConversations, LIST_POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrg?.id]);

  // ?withOrg=<organizationId>: punto de entrada desde otras páginas
  // ("Mensaje" en Buscar proveedores / ficha de proveedor) — abre o crea la
  // conversación con esa organización y la selecciona.
  useEffect(() => {
    const withOrg = searchParams.get('withOrg');
    if (!activeOrg || !withOrg || openedWithOrgRef.current === withOrg) return;
    openedWithOrgRef.current = withOrg;
    getOrCreateConversation(activeOrg.id, 'ORGANIZATION', withOrg, [withOrg])
      .then(async (id) => {
        setSelectedId(id);
        await loadConversations();
        setSearchParams((prev) => {
          const next = new URLSearchParams(prev);
          next.delete('withOrg');
          return next;
        });
      })
      .catch((error) => {
        toast.error(error.response?.data?.detail || 'No se pudo abrir la conversación');
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrg?.id, searchParams]);

  // ?conversationId=<id>: punto de entrada desde la notificación "Nuevo
  // mensaje" (NotificationBell → messaging.py::send_message's action_url) —
  // selecciona directamente esa conversación, ya existente.
  useEffect(() => {
    const conversationId = searchParams.get('conversationId');
    if (!conversationId) return;
    setSelectedId(conversationId);
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.delete('conversationId');
      return next;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  if (!activeOrg) return null;

  return (
    <div className="space-y-6">
      <Helmet>
        <title>Chat · Directorio de Empresas</title>
      </Helmet>

      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Chat</h1>
        <p className="mt-1 text-sm text-muted-foreground">Mensajes entre tu empresa y otras.</p>
      </header>

      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MessageSquare className="size-4 text-primary" />
              Conversaciones ({conversations.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1.5">
            {loading ? (
              <div className="h-16 animate-pulse rounded-lg bg-secondary" />
            ) : (
              <>
                {conversations.map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => setSelectedId(c.id)}
                    className={cn(
                      'block w-full rounded-lg border px-3 py-2 text-left text-sm hover:bg-accent/50',
                      selectedId === c.id && 'border-primary',
                    )}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium">{participantNames(c)}</span>
                      {c.unread_count > 0 && (
                        <Badge variant="brand">{c.unread_count}</Badge>
                      )}
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {formatRelative(c.updated_at)}
                    </p>
                  </button>
                ))}
                {conversations.length === 0 && (
                  <p className="text-sm text-muted-foreground">
                    Todavía no tienes conversaciones. Escríbele a un proveedor desde su ficha o
                    desde los resultados de búsqueda.
                  </p>
                )}
              </>
            )}
          </CardContent>
        </Card>

        {selectedId ? (
          <ConversationPanel organizationId={activeOrg.id} conversationId={selectedId} />
        ) : (
          <Card>
            <CardContent className="flex h-full min-h-40 items-center justify-center pt-6 text-sm text-muted-foreground">
              Selecciona una conversación para ver los mensajes.
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
