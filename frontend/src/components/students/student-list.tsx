"use client";

import Link from "next/link";
import { type FormEvent, useState } from "react";
import { ErrorState, LoadingState } from "@/components/master/resource-state";
import {
  goals,
  type StudentList as ListData,
  type StudentArea,
  statuses,
} from "@/lib/students";
import { useApiResource } from "@/lib/use-api-resource";

export function StudentList({ area }: { area: StudentArea }) {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [professional, setProfessional] = useState("");
  const [unassigned, setUnassigned] = useState(false);
  const [filters, setFilters] = useState("");
  const [page, setPage] = useState(1);
  const { data, loading, error, reload } = useApiResource<ListData>(
    `/${area}/students?page=${page}&page_size=20&${filters}`,
  );
  function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const params = new URLSearchParams();
    if (query.trim()) params.set("q", query.trim());
    if (status) params.set("status", status);
    if (area === "master") {
      if (unassigned) params.set("unassigned", "true");
      else if (professional.trim())
        params.set("professional_id", professional.trim());
    }
    setPage(1);
    const next = params.toString();
    if (next === filters && page === 1) void reload();
    else setFilters(next);
  }
  return (
    <div>
      <h1 className="text-2xl font-semibold">
        {area === "master" ? "Alunos" : "Meus alunos"}
      </h1>
      <p className="mt-2 text-sm text-muted-foreground">
        {area === "master"
          ? "Acompanhe cadastros e situações de todos os alunos."
          : "Cadastros vinculados ao seu acompanhamento."}
      </p>
      <form
        className="my-6 grid gap-4 rounded-lg border bg-white p-5 sm:grid-cols-2"
        onSubmit={search}
      >
        <div>
          <label className="mb-2 block text-sm" htmlFor="search">
            Nome ou e-mail
          </label>
          <input
            className="auth-input"
            id="search"
            maxLength={120}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <div>
          <label className="mb-2 block text-sm" htmlFor="status">
            Situação
          </label>
          <select
            className="auth-input"
            id="status"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            <option value="">Todas</option>
            {Object.entries(statuses).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
        {area === "master" && (
          <>
            <div>
              <label
                className="mb-2 block text-sm"
                htmlFor="professional-filter"
              >
                Código do profissional
              </label>
              <input
                id="professional-filter"
                className="auth-input"
                maxLength={36}
                pattern="[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
                value={professional}
                disabled={unassigned}
                onChange={(e) => setProfessional(e.target.value)}
              />
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={unassigned}
                onChange={(e) => setUnassigned(e.target.checked)}
              />
              Somente sem profissional
            </label>
          </>
        )}
        <button className="master-primary justify-self-start" type="submit">
          Buscar
        </button>
      </form>
      {loading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState message={error} retry={reload} />
      ) : (
        data && (
          <>
            <p className="mb-3 text-sm text-muted-foreground">
              {data.total} aluno(s)
            </p>
            {data.items.length === 0 ? (
              <p className="rounded-lg border bg-white p-8">
                Nenhum aluno encontrado para estes filtros.
              </p>
            ) : (
              <div className="overflow-x-auto rounded-lg border bg-white">
                <table className="w-full text-left text-sm">
                  <thead className="bg-secondary">
                    <tr>
                      {[
                        "Nome",
                        "Objetivo",
                        "Situação",
                        ...(area === "master" ? ["Profissional"] : []),
                        "Ações",
                      ].map((label) => (
                        <th className="p-4" key={label} scope="col">
                          {label}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.items.map((student) => (
                      <tr className="border-t" key={student.id}>
                        <td className="p-4">
                          <p className="font-medium">{student.name}</p>
                          <p className="text-xs text-muted-foreground">
                            {student.email}
                          </p>
                        </td>
                        <td className="p-4">{goals[student.goal]}</td>
                        <td className="p-4">{statuses[student.status]}</td>
                        {area === "master" && (
                          <td className="p-4">
                            {student.professional_name || "Sem profissional"}
                          </td>
                        )}
                        <td className="p-4">
                          <Link
                            className="font-medium text-primary underline"
                            href={`/${area}/students/${student.id}`}
                          >
                            Detalhes
                            <span className="sr-only"> de {student.name}</span>
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
              <button
                type="button"
                className="master-secondary"
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
              >
                Anterior
              </button>
              <span className="text-sm">
                Página {page} de {Math.max(1, Math.ceil(data.total / 20))}
              </span>
              <button
                type="button"
                className="master-secondary"
                disabled={page * 20 >= data.total}
                onClick={() => setPage(page + 1)}
              >
                Próxima
              </button>
            </div>
          </>
        )
      )}
    </div>
  );
}
