"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { ApiError, apiRequest } from "@/lib/api";
import { useApiResource } from "@/lib/use-api-resource";

type Kind = "diet" | "workout";
type Preview = {
  fields: string[];
  has_current_plan: boolean;
  has_recent_evolution: boolean;
};
type Result = { id: string };
const labels: Record<string, string> = {
  goal: "Objetivo",
  goal_detail: "Detalhe do objetivo",
  activity_level: "Atividade",
  training_experience: "Experiência",
  training_frequency: "Frequência",
  preferred_training_time: "Horário de treino",
  meal_schedule: "Horários das refeições",
  food_preferences: "Preferências alimentares",
  food_restrictions: "Restrições alimentares",
  professional_instructions: "Orientações adicionais",
};

export function AIGenerator({
  onGenerated,
  kind,
  studentId,
}: {
  onGenerated: () => void;
  kind: Kind;
  studentId: string;
}) {
  const router = useRouter();
  const dialog = useRef<HTMLDialogElement>(null);
  const guard = useRef(false);
  const [instructions, setInstructions] = useState("");
  const [includePlan, setIncludePlan] = useState(false);
  const [includeEvolution, setIncludeEvolution] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const { data: config } = useApiResource<{ enabled: boolean }>(
    "/professional/ai/config",
  );
  const { data: preview } = useApiResource<Preview>(
    `/${"professional"}/students/${encodeURIComponent(studentId)}/ai/${kind}/context`,
  );
  if (!config?.enabled) return null;
  const title = kind === "diet" ? "dieta" : "treino";
  async function submit() {
    if (guard.current) return;
    guard.current = true;
    setBusy(true);
    setError("");
    try {
      const next = await apiRequest<Result>(
        `/professional/students/${encodeURIComponent(studentId)}/ai/${kind}`,
        {
          method: "POST",
          signal: AbortSignal.timeout(65000),
          body: JSON.stringify({
            instructions: instructions.trim(),
            include_current_plan: includePlan,
            include_recent_evolution: includeEvolution,
          }),
        },
      );
      setResult(next);
      onGenerated();
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401)
        router.replace("/login");
      else
        setError(
          cause instanceof ApiError && cause.status === 404
            ? "Aluno fora da carteira atual. Atualize a página."
            : cause instanceof ApiError && cause.status === 429
              ? "Limite temporário de gerações atingido. Aguarde e tente novamente."
              : cause instanceof ApiError && cause.status === 503
                ? "NutraMove AI está indisponível. Tente novamente mais tarde."
                : cause instanceof ApiError && cause.status === 502
                  ? "A sugestão retornou inválida. Tente novamente."
                  : "Não foi possível gerar a sugestão. Verifique a conexão e tente novamente.",
        );
    } finally {
      guard.current = false;
      setBusy(false);
    }
  }
  return (
    <>
      <button
        type="button"
        className="master-secondary min-h-11"
        onClick={() => dialog.current?.showModal()}
      >
        Gerar sugestão de {title} com IA
      </button>
      <dialog
        ref={dialog}
        aria-labelledby={`ai-title-${kind}`}
        className="m-auto w-[calc(100%_-_2rem)] max-w-xl max-h-[90vh] overflow-y-auto rounded-lg border bg-white p-6 shadow-lg backdrop:bg-black/35"
        onCancel={(event) => {
          if (busy) event.preventDefault();
        }}
      >
        <h2 id={`ai-title-${kind}`} className="text-xl font-semibold">
          NutraMove AI · {title}
        </h2>
        <p className="mt-3 text-sm">
          Use os dados do acompanhamento para criar um rascunho que você poderá
          revisar e editar antes de publicar.
        </p>
        <div className="mt-4">
          <p className="font-medium">Dados considerados</p>
          <ul className="mt-1 list-disc pl-5 text-sm">
            {preview?.fields
              .filter((field) => field !== "professional_instructions")
              .map((field) => (
                <li key={field}>{labels[field] ?? field}</li>
              ))}
          </ul>
        </div>
        <div className="mt-4 space-y-3">
          <label className="flex min-h-11 items-center gap-2">
            <input
              type="checkbox"
              checked={includePlan}
              onChange={(event) => setIncludePlan(event.target.checked)}
              disabled={busy}
            />{" "}
            Considerar plano atual
          </label>
          <label className="flex min-h-11 items-center gap-2">
            <input
              type="checkbox"
              checked={includeEvolution}
              onChange={(event) => setIncludeEvolution(event.target.checked)}
              disabled={busy}
            />{" "}
            Considerar evolução recente
          </label>
          <label
            className="block font-medium"
            htmlFor={`ai-instructions-${kind}`}
          >
            Orientações adicionais
          </label>
          <textarea
            id={`ai-instructions-${kind}`}
            className="w-full rounded-lg border p-3"
            rows={4}
            maxLength={2000}
            value={instructions}
            onChange={(event) => setInstructions(event.target.value)}
            disabled={busy}
          />
        </div>
        <p className="mt-4 text-sm">
          A sugestão será criada como rascunho para sua revisão. Nenhuma
          alteração será publicada automaticamente para o aluno.
        </p>
        {busy && (
          <p role="status" className="mt-3">
            Gerando sugestão. Isso pode levar até um minuto…
          </p>
        )}
        {error && (
          <p role="alert" className="mt-3 text-destructive">
            {error}
          </p>
        )}
        {result && (
          <p role="status" className="mt-3">
            Sugestão criada. Revise o conteúdo antes de aprovar.
          </p>
        )}
        <div className="mt-6 flex flex-wrap justify-end gap-3">
          <button
            type="button"
            className="master-secondary min-h-11"
            disabled={busy}
            onClick={() => dialog.current?.close()}
          >
            Fechar
          </button>
          {result ? (
            <Link
              className="master-primary min-h-11"
              href={`/professional/${kind === "diet" ? "diet" : "workout"}-versions/${result.id}/edit`}
            >
              Revisar {title}
            </Link>
          ) : (
            <button
              type="button"
              className="master-primary min-h-11"
              disabled={busy}
              onClick={() => void submit()}
            >
              Gerar sugestão
            </button>
          )}
        </div>
      </dialog>
    </>
  );
}
