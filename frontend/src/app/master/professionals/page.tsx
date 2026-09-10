"use client";

import {
  ArrowRight,
  ChevronLeft,
  ChevronRight,
  Plus,
  Search,
  UsersRound,
} from "lucide-react";
import Link from "next/link";
import { type FormEvent, useState } from "react";
import { ErrorState, LoadingState } from "@/components/master/resource-state";
import { StatusBadge } from "@/components/master/status-badge";
import type { ProfessionalList } from "@/lib/professionals";
import { useMasterResource } from "@/lib/use-master-resource";

export default function ProfessionalsPage() {
  const [filters, setFilters] = useState({ q: "", status: "", page: 1 });
  const params = new URLSearchParams({
    q: filters.q,
    page: String(filters.page),
    page_size: "20",
  });
  if (filters.status) params.set("is_active", filters.status);
  const { data, loading, error, reload } = useMasterResource<ProfessionalList>(
    `/master/professionals?${params}`,
  );

  function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    setFilters({
      q: String(values.get("q") ?? "").trim(),
      status: String(values.get("status") ?? ""),
      page: 1,
    });
  }

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Profissionais
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Cadastros e acesso à plataforma.
          </p>
        </div>
        <Link href="/master/professionals/new" className="master-primary">
          <Plus className="size-4" aria-hidden="true" /> Novo profissional
        </Link>
      </div>
      <form
        onSubmit={search}
        className="mt-8 flex flex-wrap items-end gap-3 rounded-lg border border-border bg-white p-4"
      >
        <div className="min-w-48 flex-1">
          <label
            htmlFor="search-professional"
            className="mb-2 block text-xs font-medium"
          >
            Buscar profissional
          </label>
          <input
            id="search-professional"
            name="q"
            maxLength={120}
            className="auth-input"
            placeholder="Nome, e-mail ou especialidade"
          />
        </div>
        <div>
          <label htmlFor="status" className="mb-2 block text-xs font-medium">
            Status
          </label>
          <select id="status" name="status" className="auth-input min-w-36">
            <option value="">Todos</option>
            <option value="true">Ativos</option>
            <option value="false">Inativos</option>
          </select>
        </div>
        <button type="submit" className="master-secondary h-11">
          <Search className="size-4" aria-hidden="true" /> Buscar
        </button>
      </form>
      {loading ? (
        <LoadingState />
      ) : error ? (
        <div className="mt-6">
          <ErrorState message={error} retry={reload} />
        </div>
      ) : (
        data && (
          <section className="mt-6 overflow-hidden rounded-lg border border-border bg-white">
            {data.items.length === 0 ? (
              <div className="p-10 text-center">
                <UsersRound
                  className="mx-auto size-6 text-muted-foreground"
                  aria-hidden="true"
                />
                <h2 className="mt-3 font-medium">
                  Nenhum profissional encontrado
                </h2>
                <p className="mt-2 text-sm text-muted-foreground">
                  Ajuste os filtros ou cadastre um novo profissional.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <caption className="sr-only">
                    Profissionais cadastrados
                  </caption>
                  <thead className="border-b border-border bg-background text-xs text-muted-foreground">
                    <tr>
                      <th scope="col" className="px-5 py-3 font-medium">
                        Profissional
                      </th>
                      <th scope="col" className="px-5 py-3 font-medium">
                        Especialidade
                      </th>
                      <th scope="col" className="px-5 py-3 font-medium">
                        Status
                      </th>
                      <th scope="col" className="px-5 py-3 font-medium">
                        <span className="sr-only">Ações</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.items.map((item) => (
                      <tr
                        key={item.id}
                        className="border-b border-border last:border-0 hover:bg-background/70"
                      >
                        <td className="px-5 py-4">
                          <p className="font-medium">{item.name}</p>
                          <p className="mt-1 text-xs text-muted-foreground">
                            {item.email}
                          </p>
                        </td>
                        <td className="px-5 py-4 text-muted-foreground">
                          {item.specialty ?? "Não informada"}
                        </td>
                        <td className="px-5 py-4">
                          <StatusBadge active={item.is_active} />
                        </td>
                        <td className="px-5 py-4">
                          <Link
                            href={`/master/professionals/${item.id}`}
                            aria-label={`Ver detalhes de ${item.name}`}
                            className="inline-flex items-center gap-1 font-medium text-primary"
                          >
                            Detalhes{" "}
                            <ArrowRight className="size-4" aria-hidden="true" />
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <div className="flex items-center justify-between gap-3 border-t border-border px-5 py-4 text-xs text-muted-foreground">
              <span>
                {data.total} resultado(s) · Página {filters.page} de{" "}
                {Math.max(1, Math.ceil(data.total / data.page_size))}
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  aria-label="Página anterior"
                  disabled={filters.page <= 1}
                  onClick={() =>
                    setFilters((current) => ({
                      ...current,
                      page: current.page - 1,
                    }))
                  }
                  className="master-secondary disabled:opacity-40"
                >
                  <ChevronLeft className="size-4" aria-hidden="true" />
                </button>
                <button
                  type="button"
                  aria-label="Próxima página"
                  disabled={filters.page * data.page_size >= data.total}
                  onClick={() =>
                    setFilters((current) => ({
                      ...current,
                      page: current.page + 1,
                    }))
                  }
                  className="master-secondary disabled:opacity-40"
                >
                  <ChevronRight className="size-4" aria-hidden="true" />
                </button>
              </div>
            </div>
          </section>
        )
      )}
    </div>
  );
}
