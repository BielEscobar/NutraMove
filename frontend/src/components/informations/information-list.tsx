"use client";
import Link from "next/link";
import { useState } from "react";
import { ErrorState, LoadingState } from "@/components/master/resource-state";
import {
  type InformationList,
  informationCategories,
  informationStatuses,
} from "@/lib/informations";
import { useApiResource } from "@/lib/use-api-resource";

export function InformationListPage({
  area,
}: {
  area: "professional" | "student" | "master";
}) {
  const [status, setStatus] = useState("");
  const [category, setCategory] = useState("");
  const [general, setGeneral] = useState(false);
  const [page, setPage] = useState(1);
  const query = new URLSearchParams({ page: String(page) });
  if (status && area !== "student") query.set("status", status);
  if (category) query.set("category", category);
  if (general && area !== "student") query.set("general_only", "true");
  const resource = useApiResource<InformationList>(
    `/${area}/informations?${query}`,
  );
  return (
    <div className="space-y-6 [overflow-wrap:anywhere]">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Informativos</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            {area === "student"
              ? "Orientações e avisos publicados pelo seu profissional."
              : area === "master"
                ? "Consulta administrativa dos informativos."
                : "Publique orientações para os alunos da sua carteira."}
          </p>
        </div>
        {area === "professional" && (
          <Link
            className="master-primary min-h-11"
            href="/professional/informations/new"
          >
            Novo informativo
          </Link>
        )}
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        {area !== "student" && (
          <label className="text-sm">
            Status
            <select
              className="auth-input mt-2"
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setPage(1);
              }}
            >
              <option value="">Todos</option>
              {Object.entries(informationStatuses).map(([key, label]) => (
                <option value={key} key={key}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        )}
        <label className="text-sm">
          Categoria
          <select
            className="auth-input mt-2"
            value={category}
            onChange={(e) => {
              setCategory(e.target.value);
              setPage(1);
            }}
          >
            <option value="">Todas</option>
            {Object.entries(informationCategories).map(([key, label]) => (
              <option value={key} key={key}>
                {label}
              </option>
            ))}
          </select>
        </label>
        {area !== "student" && (
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={general}
              onChange={(e) => {
                setGeneral(e.target.checked);
                setPage(1);
              }}
            />
            Somente para toda a carteira
          </label>
        )}
      </div>
      {resource.loading ? (
        <LoadingState />
      ) : resource.error ? (
        <ErrorState message={resource.error} retry={resource.reload} />
      ) : (
        resource.data && (
          <>
            {!resource.data.total ? (
              <p className="rounded-lg border border-dashed p-6 text-sm">
                Nenhum informativo encontrado.
              </p>
            ) : (
              <ul className="grid gap-3 sm:grid-cols-2">
                {resource.data.items.map((item) => (
                  <li key={item.id}>
                    <Link
                      href={`/${area}/informations/${item.id}`}
                      className="block h-full space-y-3 rounded-lg border bg-white p-5 hover:border-primary"
                    >
                      <div className="flex flex-wrap gap-2 text-xs font-medium">
                        <span className="rounded-full bg-secondary px-3 py-1">
                          {informationCategories[item.category]}
                        </span>
                        {item.status && (
                          <span className="rounded-full bg-secondary px-3 py-1">
                            {informationStatuses[item.status]}
                          </span>
                        )}
                        {area !== "student" && (
                          <span className="rounded-full bg-secondary px-3 py-1">
                            {item.student_id
                              ? "Aluno específico"
                              : "Toda a carteira"}
                          </span>
                        )}
                      </div>
                      <h2 className="font-semibold">{item.title}</h2>
                      <p className="text-sm text-muted-foreground">
                        {item.summary}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {item.published_at
                          ? new Date(item.published_at).toLocaleDateString(
                              "pt-BR",
                            )
                          : "Ainda não publicado"}
                      </p>
                      <span className="block text-sm text-primary">
                        Abrir informativo
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
            {resource.data.total > 20 && (
              <div className="flex items-center gap-3">
                <button
                  className="master-secondary"
                  type="button"
                  disabled={page === 1}
                  onClick={() => setPage(page - 1)}
                >
                  Anterior
                </button>
                <span>Página {page}</span>
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
