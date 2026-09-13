"use client";
import { Bell } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";
import { useApiResource } from "@/lib/use-api-resource";

export function NotificationBell() {
  const { data, error, reload } = useApiResource<{ count: number }>(
    "/notifications/unread-count",
  );
  const pathname = usePathname();
  const previous = useRef(pathname);
  useEffect(() => {
    if (previous.current !== pathname) {
      previous.current = pathname;
      void reload();
    }
  }, [pathname, reload]);
  useEffect(() => {
    const refresh = () => {
      void reload();
    };
    window.addEventListener("focus", refresh);
    window.addEventListener("notifications-read", refresh);
    return () => {
      window.removeEventListener("focus", refresh);
      window.removeEventListener("notifications-read", refresh);
    };
  }, [reload]);
  const count = error ? 0 : (data?.count ?? 0);
  return (
    <Link
      href="/notifications"
      className="relative inline-flex min-h-11 min-w-11 shrink-0 items-center justify-center rounded-md border hover:bg-secondary"
      aria-label={
        error
          ? "Notificações, contagem indisponível"
          : `Notificações, ${count} não lidas`
      }
    >
      <Bell className="size-5" aria-hidden="true" />
      {count > 0 && (
        <span
          className="absolute -top-2 -right-2 rounded-full bg-primary px-1.5 py-0.5 text-xs font-semibold text-white"
          aria-hidden="true"
        >
          {count > 99 ? "99+" : count}
        </span>
      )}
    </Link>
  );
}
