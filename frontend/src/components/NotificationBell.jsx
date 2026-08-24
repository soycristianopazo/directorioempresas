import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { Bell } from 'lucide-react';
import { cn } from '@/lib/utils';
import { listNotifications, markAllNotificationsRead, markNotificationRead } from '@/lib/notificationsApi';

const POLL_INTERVAL_MS = 20000;

function formatTime(value) {
  return new Intl.DateTimeFormat('es-CL', { dateStyle: 'short', timeStyle: 'short' }).format(
    new Date(value),
  );
}

/** Campanita de notificaciones in-app del header (fase 7.9). Sondea cada
 * ~20s solo las no leídas; no hay Realtime en el navegador en este proyecto.
 */
export function NotificationBell() {
  const [notifications, setNotifications] = useState([]);
  const [open, setOpen] = useState(false);
  const containerRef = useRef(null);

  async function load() {
    try {
      setNotifications(await listNotifications(true));
    } catch {
      // Silencioso: se reintenta en el próximo ciclo de polling.
    }
  }

  useEffect(() => {
    load();
    const interval = setInterval(load, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    function onClickOutside(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, []);

  async function onMarkAllRead() {
    try {
      await markAllNotificationsRead();
      await load();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo actualizar');
    }
  }

  async function onOpenNotification(n) {
    if (!n.read_at) {
      try {
        await markNotificationRead(n.id);
        await load();
      } catch {
        // No bloquea la navegación si falla marcar como leída.
      }
    }
    setOpen(false);
  }

  const unreadCount = notifications.length;

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="relative flex size-9 items-center justify-center rounded-full hover:bg-accent"
        aria-label="Notificaciones"
      >
        <Bell className="size-5" />
        {unreadCount > 0 && (
          <span className="absolute right-1 top-1 flex size-4 items-center justify-center rounded-full bg-destructive text-[10px] font-medium text-destructive-foreground">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 z-50 mt-2 w-80 rounded-lg border bg-popover text-popover-foreground shadow-md">
          <div className="flex items-center justify-between border-b px-3 py-2">
            <span className="text-sm font-medium">Notificaciones</span>
            {unreadCount > 0 && (
              <button
                type="button"
                onClick={onMarkAllRead}
                className="text-xs text-primary hover:underline"
              >
                Marcar todas como leídas
              </button>
            )}
          </div>
          <ul className="max-h-80 overflow-y-auto">
            {notifications.map((n) => (
              <li key={n.id} className="border-b last:border-b-0">
                <NotificationRow notification={n} onOpen={() => onOpenNotification(n)} />
              </li>
            ))}
            {notifications.length === 0 && (
              <li className="px-3 py-6 text-center text-sm text-muted-foreground">
                No tienes notificaciones sin leer.
              </li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}

function NotificationRow({ notification, onOpen }) {
  const content = (
    <div className="px-3 py-2 text-sm hover:bg-accent">
      <p className="font-medium">{notification.title}</p>
      {notification.body && (
        <p className="mt-0.5 text-xs text-muted-foreground">{notification.body}</p>
      )}
      <p className="mt-1 text-xs text-muted-foreground">{formatTime(notification.created_at)}</p>
    </div>
  );

  if (notification.action_url) {
    return (
      <Link to={notification.action_url} onClick={onOpen} className={cn('block')}>
        {content}
      </Link>
    );
  }

  return (
    <button type="button" onClick={onOpen} className="block w-full text-left">
      {content}
    </button>
  );
}
