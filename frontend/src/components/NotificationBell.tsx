import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  getUnreadNotificationCount, listNotifications, markAllNotificationsRead, markNotificationRead,
} from "../api/endpoints";
import type { AppNotification } from "../types";

const POLL_INTERVAL_MS = 60_000;

export function NotificationBell() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  function refreshCount() {
    getUnreadNotificationCount().then(setUnreadCount).catch(() => {});
  }

  useEffect(() => {
    refreshCount();
    const interval = setInterval(refreshCount, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function toggleOpen() {
    if (!open) {
      listNotifications().then((data) => setNotifications(data.slice(0, 20)));
    }
    setOpen((v) => !v);
  }

  async function handleClickNotification(n: AppNotification) {
    if (!n.is_read) {
      await markNotificationRead(n.id);
      setNotifications((prev) => prev.map((x) => (x.id === n.id ? { ...x, is_read: true } : x)));
      refreshCount();
    }
    setOpen(false);
    if (n.link_path) navigate(n.link_path);
  }

  async function handleMarkAllRead() {
    await markAllNotificationsRead();
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    setUnreadCount(0);
  }

  return (
    <div className="notification-bell" ref={containerRef}>
      <button className="notification-bell-btn" onClick={toggleOpen} aria-label="Notifications">
        🔔
        {unreadCount > 0 && <span className="notification-badge">{unreadCount > 9 ? "9+" : unreadCount}</span>}
      </button>

      {open && (
        <div className="notification-dropdown">
          <div className="notification-dropdown-header">
            <span>Notifications</span>
            {unreadCount > 0 && <button className="btn-link" onClick={handleMarkAllRead}>Mark all read</button>}
          </div>
          {notifications.length === 0 ? (
            <div className="notification-empty">No notifications yet.</div>
          ) : (
            notifications.map((n) => (
              <button
                key={n.id}
                className={`notification-item ${!n.is_read ? "notification-item-unread" : ""}`}
                onClick={() => handleClickNotification(n)}
              >
                {n.message}
                <span className="notification-item-time">{new Date(n.created_at).toLocaleString()}</span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
