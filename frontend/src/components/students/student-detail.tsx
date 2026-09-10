"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useRef, useState } from "react";
import { ErrorState, LoadingState } from "@/components/master/resource-state";
import { ApiError, apiRequest } from "@/lib/api";
import { type Student, type StudentArea, statuses } from "@/lib/students";
import { useApiResource } from "@/lib/use-api-resource";
import {
  draftFromStudent,
  groups,
  type ProfileDraft,
  ProfileFields,
  ProfileSummary,
  profilePayload,
} from "./profile-fields";

const actionLabels = {
  approve: "Aprovar",
  reject: "Rejeitar",
  activate: "Reativar",
  deactivate: "Desativar",
} as const;
type Action = keyof typeof actionLabels;
function Editor({
  student,
  path,
  done,
  cancel,
}: {
  student: Student;
  path: string;
  done: () => void;
  cancel: () => void;
}) {
  const [values, setValues] = useState<ProfileDraft>(() =>
    draftFromStudent(student),
  );
  const [water, setWater] = useState(
    student.water_goal == null ? "" : String(student.water_goal),
  );
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const guard = useRef(false);
  const router = useRouter();
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (guard.current) return;
    guard.current = true;
    setBusy(true);
    setError("");
    try {
      await apiRequest(path, {
        method: "PATCH",
        body: JSON.stringify({
          ...profilePayload(values),
          water_goal: water === "" ? null : Number(water),
        }),
      });
      done();
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401)
        router.replace("/login");
      else
        setError(
          cause instanceof Error ? cause.message : "Não foi possível salvar.",
        );
    } finally {
      guard.current = false;
      setBusy(false);
    }
  }
  return (
    <form
      className="mt-6 space-y-8 rounded-lg border bg-white p-6"
      onSubmit={save}
      aria-busy={busy}
    >
      {groups.map((group, index) => (
        <fieldset key={group.title}>
          <legend className="mb-5 font-semibold">{group.title}</legend>
          <ProfileFields
            group={index}
            values={values}
            disabled={busy}
            change={(name, value) =>
              setValues((previous) => ({ ...previous, [name]: value }))
            }
          />
        </fieldset>
      ))}
      <div>
        <label className="mb-2 block text-sm font-medium" htmlFor="water-goal">
          Meta de água (litros/dia, opcional)
        </label>
        <input
          id="water-goal"
          type="number"
          step="any"
          min={0}
          className="auth-input"
          disabled={busy}
          value={water}
          onChange={(e) => setWater(e.target.value)}
        />
      </div>
      {error && (
        <p role="alert" className="text-destructive">
          {error}
        </p>
      )}
      <div className="flex gap-3">
        <button
          type="button"
          disabled={busy}
          className="master-secondary"
          onClick={cancel}
        >
          Cancelar
        </button>
        <button type="submit" disabled={busy} className="master-primary">
          {busy ? "Salvando…" : "Salvar alterações"}
        </button>
      </div>
    </form>
  );
}
export function StudentDetail({ area, id }: { area: StudentArea; id: string }) {
  const path = `/${area}/students/${encodeURIComponent(id)}`;
  const { data, loading, error, reload } = useApiResource<Student>(path);
  const [editing, setEditing] = useState(false);
  const [action, setAction] = useState<Action | null>(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState("");
  const [success, setSuccess] = useState("");
  const dialog = useRef<HTMLDialogElement>(null);
  const guard = useRef(false);
  const router = useRouter();
  async function changeStatus() {
    if (!action || guard.current) return;
    guard.current = true;
    setBusy(true);
    setActionError("");
    try {
      await apiRequest(`${path}/${action}`, { method: "POST" });
      dialog.current?.close();
      setSuccess("Situação atualizada.");
      await reload();
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401)
        router.replace("/login");
      else
        setActionError(
          cause instanceof ApiError && cause.status === 409
            ? "A situação mudou. Feche a confirmação e atualize a página."
            : cause instanceof Error
              ? cause.message
              : "Não foi possível atualizar.",
        );
    } finally {
      guard.current = false;
      setBusy(false);
    }
  }
  const actions: Action[] =
    data?.status === "PENDING_APPROVAL"
      ? ["approve", "reject"]
      : data?.status === "ACTIVE"
        ? ["deactivate"]
        : data?.status === "INACTIVE"
          ? ["activate"]
          : [];
  return (
    <div>
      <Link href={`/${area}/students`} className="text-sm text-primary">
        Voltar aos alunos
      </Link>
      {success && (
        <p role="status" className="mt-5 text-primary">
          {success}
        </p>
      )}
      {loading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState message={error} retry={reload} />
      ) : (
        data && (
          <>
            <h1 className="mt-5 text-2xl font-semibold">{data.name}</h1>
            <p className="mt-2 break-all text-muted-foreground">{data.email}</p>
            <p className="mt-3 font-medium text-primary">
              {statuses[data.status]}
            </p>
            <p className="mt-2 text-sm">
              Profissional:{" "}
              {data.professional_name || "Sem profissional atribuído"}
            </p>
            {editing ? (
              <Editor
                key={data.id}
                student={data}
                path={path}
                cancel={() => setEditing(false)}
                done={() => {
                  setEditing(false);
                  setSuccess("Dados atualizados.");
                  void reload();
                }}
              />
            ) : (
              <>
                <div className="my-6 flex flex-wrap gap-3">
                  <button
                    type="button"
                    className="master-secondary"
                    onClick={() => {
                      setSuccess("");
                      setEditing(true);
                    }}
                  >
                    Editar dados
                  </button>
                  {actions.map((item) => (
                    <button
                      type="button"
                      className="master-primary"
                      disabled={busy}
                      key={item}
                      onClick={() => {
                        setAction(item);
                        setActionError("");
                        setSuccess("");
                        dialog.current?.showModal();
                      }}
                    >
                      {actionLabels[item]}
                    </button>
                  ))}
                </div>
                <section className="rounded-lg border bg-white p-6">
                  <h2 className="mb-5 text-lg font-semibold">
                    Dados do acompanhamento
                  </h2>
                  <ProfileSummary values={draftFromStudent(data)} />
                  <p className="mt-5 text-sm">
                    Meta de água:{" "}
                    {data.water_goal == null
                      ? "Não definida"
                      : `${data.water_goal} L/dia`}
                  </p>
                </section>
              </>
            )}
            <dialog
              ref={dialog}
              aria-labelledby="student-action-title"
              className="m-auto w-[calc(100%_-_2rem)] max-w-md rounded-lg border bg-white p-6 shadow-lg backdrop:bg-black/35"
              onCancel={(event) => {
                if (busy) event.preventDefault();
              }}
            >
              <h2 id="student-action-title" className="text-xl font-semibold">
                {action ? actionLabels[action] : "Atualizar"} aluno?
              </h2>
              <p className="mt-4 text-sm">
                {action === "deactivate"
                  ? "O acesso será bloqueado e todas as sessões serão encerradas. Os dados serão preservados."
                  : action === "reject"
                    ? "O cadastro ficará rejeitado. O aluno poderá entrar apenas para consultar sua situação e seus dados."
                    : action === "activate"
                      ? "O aluno precisará entrar novamente. Nenhum plano será criado por esta ação."
                      : "O cadastro será aprovado. Nenhuma dieta ou treino será criado por esta ação."}
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
                  onClick={() => dialog.current?.close()}
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  disabled={busy}
                  className="master-primary"
                  onClick={() => void changeStatus()}
                >
                  {busy ? "Atualizando…" : "Confirmar"}
                </button>
              </div>
            </dialog>
          </>
        )
      )}
    </div>
  );
}
