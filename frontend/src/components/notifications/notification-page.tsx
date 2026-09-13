"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { ErrorState, LoadingState } from "@/components/master/resource-state";
import { ApiError, apiRequest, type User } from "@/lib/api";
import {
  type NotificationList,
  notificationLink,
  refreshNotificationCount,
} from "@/lib/notifications";
import { useApiResource } from "@/lib/use-api-resource";

export function NotificationPage() {
  const [page, setPage] = useState(1),
    [unread, setUnread] = useState(false);
  const resource = useApiResource<NotificationList>(
    `/notifications?page=${page}&unread_only=${unread}`,
  );
  const user = useApiResource<User>("/auth/me");
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [success, setSuccess] = useState("");
  const guard = useRef(false);
  const router = useRouter();
  async function read(id?: string) {
    if (guard.current) return;
    guard.current = true;
    setBusy(true);
    setError("");
    setSuccess("");
    try {
      await apiRequest(
        id ? `/notifications/${id}/read` : "/notifications/read-all",
        { method: "POST" },
      );
      setSuccess(
        id
          ? "Notificação marcada como lida."
          : "Notificações marcadas como lidas.",
      );
      setPage(1);
      await resource.reload();
      refreshNotificationCount();
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401)
        router.replace("/login");
      else
        setError(
          cause instanceof Error
            ? cause.message
            : "Não foi possível atualizar.",
        );
    } finally {
      guard.current = false;
      setBusy(false);
    }
  }
  return (
    <div className="space-y-6 [overflow-wrap:anywhere]">
      <h1 className="text-2xl font-semibold">Notificações</h1>
      <p className="text-sm text-muted-foreground">
        Novidades do seu acompanhamento. Recursos arquivados ou sem acesso podem
        não estar mais disponíveis.
      </p>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <label className="flex min-h-11 items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={unread}
            onChange={(event) => {
              setUnread(event.target.checked);
              setPage(1);
            }}
          />
          Somente não lidas
        </label>
        <button
          type="button"
          className="master-secondary min-h-11"
          disabled={busy}
          onClick={() => void read()}
        >
          Marcar todas como lidas
        </button>
      </div>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      {success && (
        <p role="status" className="text-sm text-primary">
          {success}
        </p>
      )}
      {resource.loading ? (
        <LoadingState />
      ) : resource.error ? (
        <ErrorState message={resource.error} retry={resource.reload} />
      ) : (
        resource.data && (
          <>
            {!resource.data.total ? (
              <p className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
                Nenhuma notificação encontrada.
              </p>
            ) : (
              <ul className="space-y-3">
                {resource.data.items.map((item) => {
                  const href = user.data
                    ? notificationLink(item, user.data.role)
                    : null;
                  return (
                    <li
                      key={item.id}
                      className={`space-y-3 rounded-lg border p-5 ${item.read_at ? "bg-white" : "border-primary/30 bg-primary/5"}`}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <h2 className="font-semibold">{item.title}</h2>
                        <span className="text-xs font-medium">
                          {item.read_at ? "Lida" : "Não lida"}
                        </span>
                      </div>
                      <p className="text-sm leading-6">{item.message}</p>
                      <time
                        className="block text-xs text-muted-foreground"
                        dateTime={item.created_at}
                      >
                        {new Date(item.created_at).toLocaleString("pt-BR")}
                      </time>
                      <div className="flex flex-wrap gap-3">
                        {href && (
                          <Link
                            className="master-secondary min-h-11"
                            href={href}
                          >
                            Abrir recurso
                          </Link>
                        )}
                        {!item.read_at && (
                          <button
                            className="master-secondary min-h-11"
                            type="button"
                            disabled={busy}
                            onClick={() => void read(item.id)}
                          >
                            Marcar como lida
                          </button>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
            {resource.data.total > 20 && (
              <div className="flex flex-wrap items-center gap-3">
                <button
                  className="master-secondary"
                  type="button"
                  disabled={page === 1}
                  onClick={() => setPage(page - 1)}
                >
                  Anterior
                </button>
                <span className="text-sm">Página {page}</span>
                <button
                  className="master-secondary"
                  type="button"
                  disabled={page * 20 >= resource.data.total}
                  onClick={() => setPage(page + 1)}
                >
                  Próxima
                </button>
              </div>
            )}
          </>
        )
      )}
    </div>
  );
}
