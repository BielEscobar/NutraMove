"use client";

import { Sparkles } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { ApiError, apiRequest } from "@/lib/api";
import { useApiResource } from "@/lib/use-api-resource";

type Plan = {
  id: string;
  status: "DRAFT" | "PENDING_REVIEW" | "APPROVED" | "ARCHIVED";
  source: "MANUAL" | "AI_GENERATED";
};
type Plans = { diet: Plan | null; workout: Plan | null };
type Result = Plans & {
  diet_error: string | null;
  workout_error: string | null;
};
const kindLabels = { diet: "Dieta", workout: "Treino" } as const;

function PlanCard({
  kind,
  plan,
  error,
}: {
  kind: keyof typeof kindLabels;
  plan: Plan | null;
  error?: string | null;
}) {
  const editable = plan && ["DRAFT", "PENDING_REVIEW"].includes(plan.status);
  return (
    <div className="rounded-lg border bg-white p-4">
      <h3 className="font-semibold">{kindLabels[kind]}</h3>
      {plan ? (
        <>
          <p className="mt-2 text-sm">
            {plan.status === "PENDING_REVIEW"
              ? "Aguardando revisão"
              : plan.status === "APPROVED"
                ? "Publicado"
                : plan.status === "DRAFT"
                  ? "Rascunho existente"
                  : "Arquivado"}
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            {plan.source === "AI_GENERATED"
              ? `Gerad${kind === "diet" ? "a" : "o"} pela NutraMove AI`
              : "Criado manualmente pelo profissional"}
          </p>
          <Link
            className="master-secondary mt-4"
            href={`/professional/${kind}-versions/${plan.id}`}
          >
            {editable
              ? `Revisar ${kindLabels[kind].toLowerCase()}`
              : `Ver ${kindLabels[kind].toLowerCase()}`}
          </Link>
        </>
      ) : error ? (
        <p role="alert" className="mt-2 text-sm text-destructive">
          {error}
        </p>
      ) : (
        <p className="mt-2 text-sm text-muted-foreground">
          Ainda não preparado.
        </p>
      )}
    </div>
  );
}

export function AIPlansGenerator({ studentId }: { studentId: string }) {
  const router = useRouter();
  const dialog = useRef<HTMLDialogElement>(null);
  const guard = useRef(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const { data: config, loading: loadingConfig } = useApiResource<{
    enabled: boolean;
  }>("/professional/ai/config");
  const state = useApiResource<Plans>(
    `/professional/students/${encodeURIComponent(studentId)}/ai/plans`,
  );
  const plans = result ?? state.data;
  const hasMissing = !plans?.diet || !plans?.workout;

  async function submit() {
    if (guard.current) return;
    guard.current = true;
    setBusy(true);
    setError("");
    try {
      const next = await apiRequest<Result>(
        `/professional/students/${encodeURIComponent(studentId)}/ai/plans`,
        {
          method: "POST",
          signal: AbortSignal.timeout(130000),
          body: JSON.stringify({}),
        },
      );
      setResult(next);
      dialog.current?.close();
      await state.reload();
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401)
        router.replace("/login");
      else if (cause instanceof ApiError && cause.status === 404)
        setError("Aluno fora da carteira atual. Atualize a página.");
      else if (cause instanceof ApiError && cause.status === 429)
        setError(
          "Limite temporário de gerações atingido. Aguarde e tente novamente.",
        );
      else if (cause instanceof ApiError && cause.status === 503)
        setError("NutraMove AI não está disponível neste ambiente.");
      else
        setError(
          "Não foi possível preparar os planos. Verifique a conexão e tente novamente.",
        );
    } finally {
      guard.current = false;
      setBusy(false);
    }
  }

  return (
    <section className="my-6 rounded-lg border bg-secondary/40 p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-2xl">
          <h2 className="text-lg font-semibold">NutraMove AI</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            A NutraMove AI pode preparar sugestões iniciais de dieta e treino
            com base nas informações fornecidas pelo aluno. Revise e ajuste os
            planos antes de disponibilizá-los.
          </p>
        </div>
        {hasMissing && (
          <button
            type="button"
            className="master-primary min-h-11"
            disabled={busy || loadingConfig || !config?.enabled}
            onClick={() => dialog.current?.showModal()}
          >
            <Sparkles className="size-4" aria-hidden="true" />
            Gerar dieta e treino com IA
          </button>
        )}
      </div>
      {!loadingConfig && !config?.enabled && hasMissing && (
        <p className="mt-3 text-sm" role="status">
          NutraMove AI não está disponível neste ambiente.
        </p>
      )}
      {state.error && (
        <p className="mt-3 text-sm text-destructive" role="alert">
          Não foi possível consultar o estado dos planos.
        </p>
      )}
      {plans && (
        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          <PlanCard kind="diet" plan={plans.diet} error={result?.diet_error} />
          <PlanCard
            kind="workout"
            plan={plans.workout}
            error={result?.workout_error}
          />
        </div>
      )}
      {result && !result.diet_error && !result.workout_error && (
        <p role="status" className="mt-4 text-sm text-primary">
          Dieta e treino preparados. Revise os planos antes de disponibilizá-los
          ao aluno.
        </p>
      )}
      {result && (result.diet_error || result.workout_error) && hasMissing && (
        <button
          type="button"
          className="master-secondary mt-4"
          disabled={busy}
          onClick={() => void submit()}
        >
          {busy ? "Preparando novamente…" : "Tentar novamente"}
        </button>
      )}
      {error && (
        <p role="alert" className="mt-4 text-sm text-destructive">
          {error}
        </p>
      )}
      <dialog
        ref={dialog}
        aria-labelledby="ai-plans-title"
        className="m-auto max-h-[90vh] w-[calc(100%_-_2rem)] max-w-lg overflow-y-auto rounded-lg border bg-white p-6 shadow-lg backdrop:bg-black/35"
        onCancel={(event) => {
          if (busy) event.preventDefault();
        }}
      >
        <h2 id="ai-plans-title" className="text-xl font-semibold">
          Preparar dieta e treino com IA
        </h2>
        <p className="mt-4 text-sm">
          A NutraMove AI criará sugestões iniciais para este aluno. Os planos
          ficarão aguardando sua revisão e não serão disponibilizados ao aluno
          até que você os aprove.
        </p>
        {busy && (
          <p role="status" className="mt-4 text-sm">
            Preparando dieta e treino…
          </p>
        )}
        <div className="mt-6 flex flex-wrap justify-end gap-3">
          <button
            type="button"
            className="master-secondary min-h-11"
            disabled={busy}
            onClick={() => dialog.current?.close()}
          >
            Cancelar
          </button>
          <button
            type="button"
            className="master-primary min-h-11"
            disabled={busy}
            onClick={() => void submit()}
          >
            {busy ? "Preparando dieta e treino…" : "Gerar dieta e treino"}
          </button>
        </div>
      </dialog>
    </section>
  );
}
