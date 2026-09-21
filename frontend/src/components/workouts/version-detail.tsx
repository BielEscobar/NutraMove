"use client";

import { Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { ErrorState, LoadingState } from "@/components/master/resource-state";
import { ApiError, apiRequest } from "@/lib/api";
import { useApiResource } from "@/lib/use-api-resource";
import {
  type WorkoutArea,
  type WorkoutVersion,
  workoutStatuses,
} from "@/lib/workouts";
import { WorkoutReader } from "./workout-reader";

export function VersionDetail({ area, id }: { area: WorkoutArea; id: string }) {
  const path = `/${area}/workout-versions/${encodeURIComponent(id)}`;
  const { data, loading, error, reload } = useApiResource<WorkoutVersion>(path);
  const [busy, setBusy] = useState(false),
    [actionError, setActionError] = useState(""),
    [success, setSuccess] = useState("");
  const guard = useRef(false),
    dialog = useRef<HTMLDialogElement>(null),
    deleteDialog = useRef<HTMLDialogElement>(null);
  const router = useRouter();
  async function deleteDraft() {
    if (guard.current || !data) return;
    guard.current = true;
    setBusy(true);
    setActionError("");
    try {
      const workout = await apiRequest<{ student_id: string }>(
        `/professional/workouts/${data.workout_id}`,
      );
      await apiRequest(path, { method: "DELETE" });
      deleteDialog.current?.close();
      router.push(`/professional/students/${workout.student_id}`);
      router.refresh();
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401)
        router.replace("/login");
      else
        setActionError(
          cause instanceof Error ? cause.message : "Não foi possível excluir.",
        );
    } finally {
      guard.current = false;
      setBusy(false);
    }
  }
  async function act(action: "approve" | "duplicate") {
    if (guard.current || !data) return;
    guard.current = true;
    setBusy(true);
    setActionError("");
    setSuccess("");
    try {
      const next = await apiRequest<WorkoutVersion>(`${path}/${action}`, {
        method: "POST",
        ...(action === "approve"
          ? { body: JSON.stringify({ expected_revision: data.edit_revision }) }
          : {}),
      });
      dialog.current?.close();
      if (action === "duplicate")
        router.push(`/professional/workout-versions/${next.id}/edit`);
      else {
        setSuccess(
          "Plano publicado. A versão anteriormente publicada foi arquivada.",
        );
        await reload();
      }
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401)
        router.replace("/login");
      else
        setActionError(
          cause instanceof ApiError && cause.status === 409
            ? "A versão ou a situação do aluno mudou. Atualize a página antes de publicar."
            : cause instanceof ApiError && cause.status === 422
              ? "Adicione ao menos um dia de treino ativo com exercícios antes de publicar."
              : cause instanceof Error
                ? cause.message
                : "Não foi possível concluir.",
        );
    } finally {
      guard.current = false;
      setBusy(false);
    }
  }
  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} retry={reload} />;
  if (!data) return null;
  return (
    <div>
      <Link
        href={`/${area}/workouts/${data.workout_id}`}
        className="text-sm text-primary underline"
      >
        Histórico de versões
      </Link>
      <div className="my-5 flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm font-medium">
          Versão {data.version_number} · {workoutStatuses[data.status]} ·{" "}
          {data.source === "MANUAL"
            ? "Criado manualmente"
            : "Gerado com NutraMove AI"}
        </p>
        {data.source === "AI_GENERATED" && data.status === "PENDING_REVIEW" && (
          <p className="text-sm">
            Revisão profissional necessária antes da publicação.
          </p>
        )}
        {area === "professional" && (
          <div className="flex flex-wrap gap-3">
            {["DRAFT", "PENDING_REVIEW"].includes(data.status) && (
              <>
                <Link
                  className="master-secondary"
                  href={`/professional/workout-versions/${id}/edit`}
                >
                  Editar rascunho
                </Link>
                <button
                  type="button"
                  disabled={busy}
                  className="master-secondary text-destructive"
                  onClick={() => deleteDialog.current?.showModal()}
                >
                  <Trash2
                    aria-hidden="true"
                    className="mr-2 inline-block size-4"
                  />
                  Excluir rascunho
                </button>
                <button
                  type="button"
                  disabled={busy}
                  className="master-primary"
                  onClick={() => {
                    setActionError("");
                    dialog.current?.showModal();
                  }}
                >
                  Aprovar e publicar
                </button>
              </>
            )}
            <button
              type="button"
              disabled={busy}
              className="master-secondary"
              onClick={() => void act("duplicate")}
            >
              {busy ? "Processando…" : "Duplicar versão"}
            </button>
          </div>
        )}
      </div>
      {success && (
        <p role="status" className="mb-5 text-primary">
          {success}
        </p>
      )}
      {actionError && (
        <p role="alert" className="mb-5 text-destructive">
          {actionError}
        </p>
      )}
      <WorkoutReader key={`${data.id}-${data.edit_revision}`} workout={data} />
      <dialog
        ref={dialog}
        aria-labelledby="publish-title"
        className="m-auto w-[calc(100%_-_2rem)] max-w-md rounded-lg border bg-white p-6 shadow-lg backdrop:bg-black/35"
        onCancel={(event) => {
          if (busy) event.preventDefault();
        }}
      >
        <h2 id="publish-title" className="text-xl font-semibold">
          Publicar este plano?
        </h2>
        <p className="mt-4 text-sm leading-6">
          O aluno ativo poderá visualizar esta versão. O plano publicado
          anterior será arquivado, preservando seu conteúdo. Revise exercícios,
          cargas, prescrições e datas antes de confirmar.
        </p>
        {actionError && (
          <p role="alert" className="mt-4 text-destructive">
            {actionError}
          </p>
        )}
        <div className="mt-6 flex flex-wrap justify-end gap-3">
          <button
            className="master-secondary"
            type="button"
            disabled={busy}
            onClick={() => dialog.current?.close()}
          >
            Cancelar
          </button>
          <button
            className="master-primary"
            type="button"
            disabled={busy}
            onClick={() => void act("approve")}
          >
            {busy ? "Publicando…" : "Confirmar publicação"}
          </button>
        </div>
      </dialog>
      <dialog
        ref={deleteDialog}
        aria-labelledby="delete-workout-title"
        className="m-auto w-[calc(100%_-_2rem)] max-w-md rounded-lg border bg-white p-6 shadow-lg backdrop:bg-black/35"
        onCancel={(event) => {
          if (busy) event.preventDefault();
        }}
      >
        <h2 id="delete-workout-title" className="text-xl font-semibold">
          Excluir este rascunho?
        </h2>
        <p className="mt-4 text-sm">
          Esta ação removerá permanentemente esta versão ainda não publicada e
          não poderá ser desfeita.
        </p>
        {actionError && (
          <p role="alert" className="mt-4 text-destructive">
            {actionError}
          </p>
        )}
        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            disabled={busy}
            className="master-secondary"
            onClick={() => deleteDialog.current?.close()}
          >
            Cancelar
          </button>
          <button
            type="button"
            disabled={busy}
            className="master-primary"
            onClick={() => void deleteDraft()}
          >
            {busy ? "Excluindo…" : "Excluir rascunho"}
          </button>
        </div>
      </dialog>
    </div>
  );
}
