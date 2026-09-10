"use client";

import { ArrowLeft, Pencil, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { ErrorState, LoadingState } from "@/components/master/resource-state";
import { StatusBadge } from "@/components/master/status-badge";
import { ApiError, apiRequest } from "@/lib/api";
import type { Professional } from "@/lib/professionals";
import { useMasterResource } from "@/lib/use-master-resource";

export function ProfessionalDetail({ id }: { id: string }) {
  const { data, loading, error, reload } = useMasterResource<Professional>(
    `/master/professionals/${encodeURIComponent(id)}`,
  );
  const dialog = useRef<HTMLDialogElement>(null);
  const submitting = useRef(false);
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState("");
  const [success, setSuccess] = useState("");

  async function changeStatus(active: boolean) {
    if (submitting.current) return;
    submitting.current = true;
    setBusy(true);
    setActionError("");
    setSuccess("");
    try {
      await apiRequest<Professional>(
        `/master/professionals/${encodeURIComponent(id)}/${active ? "activate" : "deactivate"}`,
        { method: "POST" },
      );
      dialog.current?.close();
      setSuccess(
        active
          ? "Profissional reativado. Um novo login será necessário."
          : "Profissional desativado. As sessões de acesso foram encerradas.",
      );
      await reload();
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401)
        router.replace("/login");
      else if (cause instanceof ApiError && cause.status === 403)
        router.replace("/account");
      else
        setActionError(
          cause instanceof Error
            ? cause.message
            : "Não foi possível alterar o status.",
        );
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }

  return (
    <div>
      <Link
        href="/master/professionals"
        className="mb-6 inline-flex items-center gap-2 text-sm text-muted-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden="true" /> Profissionais
      </Link>
      {success && (
        <p
          role="status"
          className="mb-5 rounded-md border border-primary/20 bg-brand-mint/20 p-4 text-sm text-brand-deep"
        >
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
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h1 className="text-2xl font-semibold tracking-tight">
                  {data.name}
                </h1>
                <div className="mt-3">
                  <StatusBadge active={data.is_active} />
                </div>
              </div>
              <Link
                href={`/master/professionals/${data.id}/edit`}
                className="master-secondary"
              >
                <Pencil className="size-4" aria-hidden="true" /> Editar cadastro
              </Link>
            </div>
            <section className="mt-8 max-w-3xl rounded-lg border border-border bg-white p-6">
              <h2 className="font-semibold">Informações do cadastro</h2>
              <p className="mt-4 text-sm">
                Código do profissional:{" "}
                <span className="break-all">{data.id}</span>
              </p>
              {data.is_active && (
                <Link
                  href={`/register?professional_id=${data.id}`}
                  className="mt-3 inline-block text-sm text-primary underline"
                >
                  Abrir link de cadastro para alunos
                </Link>
              )}
              <dl className="mt-6 grid gap-6 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-muted-foreground">E-mail</dt>
                  <dd className="mt-1 break-all">{data.email}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Especialidade</dt>
                  <dd className="mt-1">{data.specialty ?? "Não informada"}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Cadastrado em</dt>
                  <dd className="mt-1">
                    {new Date(data.created_at).toLocaleDateString("pt-BR")}
                  </dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Atualizado em</dt>
                  <dd className="mt-1">
                    {new Date(data.updated_at).toLocaleDateString("pt-BR")}
                  </dd>
                </div>
              </dl>
            </section>
            <section className="mt-6 max-w-3xl rounded-lg border border-border bg-white p-6">
              <div className="flex items-center gap-2">
                <ShieldCheck
                  className="size-5 text-primary"
                  aria-hidden="true"
                />
                <h2 className="font-semibold">Acesso à plataforma</h2>
              </div>
              <p className="mt-3 text-sm leading-6 text-muted-foreground">
                {data.is_active
                  ? "Ao desativar, o profissional perde o acesso e suas sessões são encerradas. O cadastro é preservado."
                  : "O cadastro está preservado. Reative o acesso para permitir um novo login."}
              </p>
              {actionError && (
                <p role="alert" className="mt-4 text-sm text-destructive">
                  {actionError}
                </p>
              )}
              <button
                type="button"
                disabled={busy}
                className={`mt-5 ${data.is_active ? "master-secondary text-destructive" : "master-primary"}`}
                onClick={() => {
                  if (data.is_active) {
                    setActionError("");
                    dialog.current?.showModal();
                  } else void changeStatus(true);
                }}
              >
                {busy
                  ? "Atualizando…"
                  : data.is_active
                    ? "Desativar profissional"
                    : "Reativar profissional"}
              </button>
            </section>
            <dialog
              ref={dialog}
              aria-labelledby="deactivate-title"
              onCancel={(event) => {
                if (busy) event.preventDefault();
              }}
              className="m-auto w-[calc(100%-2rem)] max-w-md rounded-lg border border-border bg-white p-6 shadow-lg backdrop:bg-black/35"
            >
              <h2 id="deactivate-title" className="text-lg font-semibold">
                Desativar profissional?
              </h2>
              <p className="mt-3 text-sm leading-6 text-muted-foreground">
                {data.name} perderá o acesso ao NUTRAMOVE. O cadastro será
                mantido e poderá ser reativado.
              </p>
              {actionError && (
                <p role="alert" className="mt-4 text-sm text-destructive">
                  {actionError}
                </p>
              )}
              <div className="mt-6 flex flex-wrap justify-end gap-3">
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
                  className="master-primary bg-destructive hover:bg-destructive/90"
                  onClick={() => void changeStatus(false)}
                >
                  {busy ? "Desativando…" : "Confirmar desativação"}
                </button>
              </div>
            </dialog>
          </>
        )
      )}
    </div>
  );
}
