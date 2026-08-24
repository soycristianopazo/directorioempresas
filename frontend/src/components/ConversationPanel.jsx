import { useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { MessageSquare, Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { getOrCreateConversation, listMessages, markConversationRead, sendMessage } from '@/lib/messagingApi';

const POLL_INTERVAL_MS = 5000;

function formatTime(value) {
  return new Intl.DateTimeFormat('es-CL', { dateStyle: 'short', timeStyle: 'short' }).format(
    new Date(value),
  );
}

/** Panel de mensajería compacto para una conversación atada a un contexto
 * (evento de sourcing, oferta, etc). Actualiza por polling — el proyecto no
 * tiene Realtime en el navegador (ver lib/messagingApi.js).
 */
export function ConversationPanel({ organizationId, contextType, contextId, participantOrganizationIds }) {
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [draft, setDraft] = useState('');
  const [sending, setSending] = useState(false);
  const listRef = useRef(null);
  const afterRef = useRef(null);

  useEffect(() => {
    if (!organizationId || !contextId) return;
    let cancelled = false;
    setLoading(true);
    setConversationId(null);
    setMessages([]);
    afterRef.current = null;

    getOrCreateConversation(organizationId, contextType, contextId, participantOrganizationIds || [])
      .then(async (id) => {
        if (cancelled) return;
        setConversationId(id);
        await markConversationRead(organizationId, id).catch(() => {});
      })
      .catch(() => {
        if (!cancelled) toast.error('No se pudo abrir la conversación');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [organizationId, contextType, contextId]);

  useEffect(() => {
    if (!organizationId || !conversationId) return;
    let cancelled = false;

    async function poll() {
      try {
        const rows = await listMessages(organizationId, conversationId, afterRef.current);
        if (cancelled || rows.length === 0) return;
        afterRef.current = rows[rows.length - 1].created_at;
        setMessages((prev) => [...prev, ...rows]);
      } catch {
        // Silencioso: se reintenta en el próximo ciclo de polling.
      }
    }

    poll();
    const interval = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [organizationId, conversationId]);

  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [messages]);

  async function onSend() {
    const body = draft.trim();
    if (!body || !conversationId) return;
    setSending(true);
    try {
      const msg = await sendMessage(organizationId, conversationId, body);
      setMessages((prev) => [...prev, msg]);
      afterRef.current = msg.created_at;
      setDraft('');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo enviar el mensaje');
    } finally {
      setSending(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MessageSquare className="size-4 text-primary" />
          Mensajes
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div ref={listRef} className="max-h-72 space-y-2 overflow-y-auto rounded-lg border p-3">
          {loading && <div className="h-16 animate-pulse rounded-lg bg-secondary" />}
          {!loading && messages.length === 0 && (
            <p className="text-sm text-muted-foreground">Sin mensajes todavía.</p>
          )}
          {messages.map((m) => (
            <div key={m.id} className="rounded-lg bg-secondary/60 px-3 py-2 text-sm">
              <p className="whitespace-pre-wrap">{m.body}</p>
              <p className="mt-1 text-xs text-muted-foreground">{formatTime(m.created_at)}</p>
            </div>
          ))}
        </div>
        <div className="flex gap-2">
          <Textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Escribe un mensaje…"
            className="min-h-10"
            rows={2}
            disabled={!conversationId}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                onSend();
              }
            }}
          />
          <Button size="sm" onClick={onSend} disabled={sending || !draft.trim() || !conversationId}>
            <Send className="size-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
