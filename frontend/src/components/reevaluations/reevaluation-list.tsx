"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useRef, useState } from "react";
import { ErrorState, LoadingState } from "@/components/master/resource-state";
import { ApiError, apiRequest } from "@/lib/api";
import type { Area } from "@/lib/evolution";
import {
  type Reevaluation,
  type ReevaluationCategory,
  type ReevaluationList,
  reevaluationCategories,
  reevaluationStatuses,
  requestDate,
} from "@/lib/reevaluations";
import type { Student } from "@/lib/students";
import { useApiResource } from "@/lib/use-api-resource";

function NewRequest() {
  const profile = useApiResource<Student>("/students/me");
  const [category, setCategory] = useState<ReevaluationCategory>("WORKOUT");
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const guard = useRef(false);
  const router = useRouter();
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (guard.current) return;
    if (reason.trim().length < 10) {
      setError("Descreva o motivo com pelo menos 10 caracteres.");
      return;
    }
    guard.current = true;
    setBusy(true);
    setError("");
    try {
      const result = await apiRequest<Reevaluation>(
        "/student/reevaluation-requests",
        {
          method: "POST",
          body: JSON.stringify({ category, reason: reason.trim() }),
        },
      );
      router.push(`/student/reevaluation-requests/${result.id}?sent=1`);
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401)
        router.replace("/login");
      else
        setError(
          cause instanceof Error ? cause.message : "Não foi possível enviar.",
        );
      guard.current = false;
      setBusy(false);
    }
  }
  if (profile.loading) return <LoadingState />;
  if (profile.error)
    return <ErrorState message={profile.error} retry={profile.reload} />;
  if (profile.data?.status !== "ACTIVE" || !profile.data.professional_id)
    return (
      <p className="rounded-lg border bg-white p-5 text-sm text-muted-foreground">
        Para solicitar reavaliação, seu cadastro precisa estar ativo e vinculado
        a um profissional.
      </p>
    );
  return (
    <form
      onSubmit={submit}
      aria-busy={busy}
      aria-describedby={error ? "request-error" : undefined}
      className="space-y-5 rounded-lg border bg-white p-5"
    >
      <h2 className="text-lg font-semibold">Solicitar reavaliação</h2>
      <p className="text-sm text-muted-foreground">
        Conte o que gostaria de revisar. É possível manter uma solicitação em
        andamento por vez.
      </p>
      <label htmlFor="request-category" className="block text-sm">
        Categoria
        <select
          id="request-category"
          className="auth-input mt-2"
          value={category}
          disabled={busy}
          onChange={(event) =>
            setCategory(event.target.value as ReevaluationCategory)
          }
        >
          {Object.entries(reevaluationCategories).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <label htmlFor="request-reason" className="block text-sm">
        Motivo
        <textarea
          id="request-reason"
          className="auth-input mt-2 min-h-32"
          required
          minLength={10}
          maxLength={2000}
          value={reason}
          disabled={busy}
          onChange={(event) => setReason(event.target.value)}
          aria-describedby="reason-help"
        />
      </label>
      <p id="reason-help" className="text-xs text-muted-foreground">
        De 10 a 2000 caracteres. {reason.length}/2000
      </p>
      {error && (
        <p id="request-error" role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      <button type="submit" className="master-primary min-h-11" disabled={busy}>
        {busy ? "Enviando…" : "Enviar solicitação"}
      </button>
    </form>
  );
}

export function ReevaluationListPage({ area }: { area: Area }) {
  const [status, setStatus] = useState("");
  const [category, setCategory] = useState("");
  const [page, setPage] = useState(1);
  const query = new URLSearchParams({ page: String(page) });
  if (status) query.set("status", status);
  if (category) query.set("category", category);
  const resource = useApiResource<ReevaluationList>(
    `/${area}/reevaluation-requests?${query}`,
  );
  return (
    <div className="space-y-6 [overflow-wrap:anywhere]">
      <h1 className="text-2xl font-semibold">
        {area === "student" ? "Minhas reavaliações" : "Reavaliações"}
      </h1>
      <p className="text-sm text-muted-foreground">
        {area === "master"
          ? "Consulta administrativa das solicitações e respostas."
          : area === "professional"
            ? "Acompanhe as solicitações dos alunos da sua carteira."
            : "Solicite uma revisão e acompanhe a resposta do seu profissional."}
      </p>
      {area === "student" && <NewRequest />}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">
          {area === "student" ? "Histórico de solicitações" : "Solicitações"}
        </h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <label htmlFor="request-status-filter" className="text-sm">
            Status
            <select
              id="request-status-filter"
              className="auth-input mt-2"
              value={status}
              onChange={(event) => {
                setStatus(event.target.value);
                setPage(1);
              }}
            >
              <option value="">Todos</option>
              {Object.entries(reevaluationStatuses).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label htmlFor="request-category-filter" className="text-sm">
            Categoria
            <select
              id="request-category-filter"
              className="auth-input mt-2"
              value={category}
              onChange={(event) => {
                setCategory(event.target.value);
                setPage(1);
              }}
            >
              <option value="">Todas</option>
              {Object.entries(reevaluationCategories).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        </div>
        {resource.loading ? (
          <LoadingState />
        ) : resource.error ? (
          <ErrorState message={resource.error} retry={resource.reload} />
        ) : (
          resource.data && (
            <>
              {!resource.data.total ? (
                <p className="rounded-lg border border-dashed p-5 text-sm text-muted-foreground">
                  Nenhuma solicitação encontrada.
                </p>
              ) : (
                <ul className="space-y-3">
                  {resource.data.items.map((item) => (
                    <li key={item.id}>
                      <Link
                        href={`/${area}/reevaluation-requests/${item.id}`}
                        className="block space-y-3 rounded-lg border bg-white p-5 hover:border-primary"
                      >
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <h3 className="font-semibold">
                            {item.student_name ? `${item.student_name} · ` : ""}
                            {reevaluationCategories[item.category]}
                          </h3>
                          <span className="rounded-full bg-secondary px-3 py-1 text-xs font-medium">
                            {reevaluationStatuses[item.status]}
                          </span>
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {item.reason_summary}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {requestDate(item.created_at)}
                        </p>
                        <span className="block text-sm text-primary">
                          Ver solicitação
                        </span>
                      </Link>
                    </li>
                  ))}
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
      </section>
    </div>
  );
}
