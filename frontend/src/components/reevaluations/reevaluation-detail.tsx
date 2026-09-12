"use client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, useRef, useState } from "react";
import { ErrorState, LoadingState } from "@/components/master/resource-state";
import { ApiError, apiRequest } from "@/lib/api";
import type { Area } from "@/lib/evolution";
import {
  type Reevaluation,
  reevaluationCategories,
  reevaluationStatuses,
  requestDate,
} from "@/lib/reevaluations";
import { useApiResource } from "@/lib/use-api-resource";

export function ReevaluationDetail({ area, id }: { area: Area; id: string }) {
  const base = `/${area}/reevaluation-requests`;
  const resource = useApiResource<Reevaluation>(
    `${base}/${encodeURIComponent(id)}`,
  );
  const [response, setResponse] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const guard = useRef(false);
  const router = useRouter();
  const search = useSearchParams();
  async function act(action: "start-review" | "complete" | "cancel") {
    if (guard.current) return;
    if (
      action === "cancel" &&
      !window.confirm("Cancelar esta solicitação? Ela não poderá ser reaberta.")
    )
      return;
    guard.current = true;
    setBusy(true);
    setError("");
    setSuccess("");
    try {
      await apiRequest(`${base}/${encodeURIComponent(id)}/${action}`, {
        method: "POST",
        ...(action === "complete"
          ? { body: JSON.stringify({ professional_response: response.trim() }) }
          : {}),
      });
      setSuccess("Solicitação atualizada.");
      setResponse("");
      await resource.reload();
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
  function complete(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!response.trim()) {
      setError("Informe uma resposta para concluir.");
      return;
    }
    void act("complete");
  }
  const data = resource.data;
  return (
    <div className="space-y-6 [overflow-wrap:anywhere]">
      <Link href={base} className="text-sm text-primary underline">
        Voltar às reavaliações
      </Link>
      <h1 className="text-2xl font-semibold">Solicitação de reavaliação</h1>
      {search.get("sent") === "1" && (
        <p role="status" className="text-sm text-primary">
          Solicitação enviada.
        </p>
      )}
      {success && (
        <p role="status" className="text-sm text-primary">
          {success}
        </p>
      )}
      {error && (
        <div>
          <p
            id="review-error"
            role="alert"
            className="text-sm text-destructive"
          >
            {error}
          </p>
          <button
            type="button"
            className="master-secondary mt-3"
            onClick={() => void resource.reload()}
          >
            Atualizar solicitação
          </button>
        </div>
      )}
      {resource.loading ? (
        <LoadingState />
      ) : resource.error ? (
        <ErrorState message={resource.error} retry={resource.reload} />
      ) : (
        data && (
          <>
            <section className="space-y-4 rounded-lg border bg-white p-5">
              {data.student_name && (
                <h2 className="text-lg font-semibold">{data.student_name}</h2>
              )}
              <p className="font-medium">
                {reevaluationCategories[data.category]} ·{" "}
                {reevaluationStatuses[data.status]}
              </p>
              <dl className="grid gap-3 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-muted-foreground">Enviada</dt>
                  <dd>{requestDate(data.created_at)}</dd>
                </div>
                {data.reviewed_at && (
                  <div>
                    <dt className="text-muted-foreground">Análise iniciada</dt>
                    <dd>{requestDate(data.reviewed_at)}</dd>
                  </div>
                )}
                {data.completed_at && (
                  <div>
                    <dt className="text-muted-foreground">Concluída</dt>
                    <dd>{requestDate(data.completed_at)}</dd>
                  </div>
                )}
                {data.cancelled_at && (
                  <div>
                    <dt className="text-muted-foreground">Cancelada</dt>
                    <dd>{requestDate(data.cancelled_at)}</dd>
                  </div>
                )}
              </dl>
              <h3 className="border-t pt-4 font-semibold">Motivo</h3>
              <p className="whitespace-pre-wrap text-sm leading-6">
                {data.reason}
              </p>
              <h3 className="border-t pt-4 font-semibold">
                Resposta do profissional
              </h3>
              <p className="whitespace-pre-wrap text-sm leading-6">
                {data.professional_response ||
                  "Ainda não há resposta registrada."}
              </p>
            </section>
            {area !== "student" && data.student_id && (
              <nav
                aria-label="Acompanhamento do aluno"
                className="flex flex-wrap gap-3"
              >
                <Link
                  className="master-secondary"
                  href={`/${area}/students/${data.student_id}/diets`}
                >
                  Ver dieta
                </Link>
                <Link
                  className="master-secondary"
                  href={`/${area}/students/${data.student_id}/workouts`}
                >
                  Ver treino
                </Link>
                <Link
                  className="master-secondary"
                  href={`/${area}/students/${data.student_id}/evolution`}
                >
                  Ver evolução
                </Link>
              </nav>
            )}
            {area === "professional" && data.status === "PENDING" && (
              <button
                className="master-primary min-h-11"
                type="button"
                disabled={busy}
                onClick={() => void act("start-review")}
              >
                {busy ? "Salvando…" : "Iniciar análise"}
              </button>
            )}
            {area === "professional" && data.status === "IN_REVIEW" && (
              <form
                onSubmit={complete}
                aria-busy={busy}
                aria-describedby={error ? "review-error" : undefined}
                className="space-y-4 rounded-lg border bg-white p-5"
              >
                <label
                  htmlFor="review-response"
                  className="block text-sm font-medium"
                >
                  Resposta final
                  <textarea
                    id="review-response"
                    className="auth-input mt-2 min-h-32"
                    required
                    maxLength={2000}
                    value={response}
                    onChange={(event) => setResponse(event.target.value)}
                    disabled={busy}
                  />
                </label>
                <p className="text-xs text-muted-foreground">
                  A resposta será exibida ao aluno. Concluir a solicitação não
                  altera dieta, treino ou avaliações automaticamente.
                </p>
                <button
                  className="master-primary min-h-11"
                  type="submit"
                  disabled={busy}
                >
                  {busy ? "Salvando…" : "Concluir solicitação"}
                </button>
              </form>
            )}
            {((area === "student" && data.status === "PENDING") ||
              (area === "professional" &&
                ["PENDING", "IN_REVIEW"].includes(data.status))) && (
              <button
                className="master-secondary min-h-11"
                type="button"
                disabled={busy}
                onClick={() => void act("cancel")}
              >
                Cancelar solicitação
              </button>
            )}
          </>
        )
      )}
    </div>
  );
}
