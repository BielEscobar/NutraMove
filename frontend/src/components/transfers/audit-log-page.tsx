"use client";

import Link from "next/link";
import { useState } from "react";
import { ErrorState, LoadingState } from "@/components/master/resource-state";
import { useApiResource } from "@/lib/use-api-resource";

type Audit = {
  id: string;
  actor_user_id: string;
  actor_name: string;
  action: "STUDENT_ASSIGNED" | "STUDENT_TRANSFERRED";
  resource_type: string;
  resource_id: string;
  old_professional_id: string | null;
  old_professional_name: string | null;
  new_professional_id: string;
  new_professional_name: string;
  reason: string;
  created_at: string;
};
type AuditList = {
  items: Audit[];
  total: number;
  page: number;
  page_size: number;
};

export function AuditLogPage() {
  const [action, setAction] = useState("");
  const [page, setPage] = useState(1);
  const query = new URLSearchParams({ page: String(page) });
  if (action) query.set("action", action);
  const resource = useApiResource<AuditList>(`/master/audit-logs?${query}`);
  return (
    <div className="space-y-6 [overflow-wrap:anywhere]">
      <h1 className="text-2xl font-semibold">Auditoria administrativa</h1>
      <p className="text-sm text-muted-foreground">
        Atribuições e transferências de alunos realizadas pelo MASTER.
      </p>
      <label className="block max-w-xs text-sm">
        Ação
        <select
          className="auth-input mt-2"
          value={action}
          onChange={(event) => {
            setAction(event.target.value);
            setPage(1);
          }}
        >
          <option value="">Todas</option>
          <option value="STUDENT_ASSIGNED">Aluno atribuído</option>
          <option value="STUDENT_TRANSFERRED">Aluno transferido</option>
        </select>
      </label>
      {resource.loading ? (
        <LoadingState />
      ) : resource.error ? (
        <ErrorState message={resource.error} retry={resource.reload} />
      ) : (
        resource.data && (
          <>
            {!resource.data.total ? (
              <p className="rounded-lg border border-dashed p-5 text-sm">
                Nenhum registro encontrado.
              </p>
            ) : (
              <ul className="space-y-3">
                {resource.data.items.map((item) => (
                  <li
                    key={item.id}
                    className="space-y-2 rounded-lg border bg-white p-5 text-sm"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <h2 className="font-semibold">
                        {item.action === "STUDENT_ASSIGNED"
                          ? "Aluno atribuído"
                          : "Aluno transferido"}
                      </h2>
                      <time
                        className="text-xs text-muted-foreground"
                        dateTime={item.created_at}
                      >
                        {new Date(item.created_at).toLocaleString("pt-BR")}
                      </time>
                    </div>
                    <p>
                      Aluno:{" "}
                      <Link
                        className="text-primary underline"
                        href={`/master/students/${item.resource_id}`}
                      >
                        Abrir cadastro
                      </Link>
                    </p>
                    <p>
                      De: {item.old_professional_name || "Sem profissional"}
                    </p>
                    <p>Para: {item.new_professional_name}</p>
                    <p>Motivo: {item.reason}</p>
                    <p className="text-xs text-muted-foreground">
                      Realizado por {item.actor_name}
                    </p>
                  </li>
                ))}
              </ul>
            )}
            {resource.data.total > 20 && (
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  className="master-secondary min-h-11"
                  disabled={page === 1}
                  onClick={() => setPage(page - 1)}
                >
                  Anterior
                </button>
                <span className="text-sm">Página {page}</span>
                <button
                  type="button"
                  className="master-secondary min-h-11"
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
