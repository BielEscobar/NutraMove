"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useRef, useState } from "react";
import { ErrorState } from "@/components/master/resource-state";
import { ApiError, apiRequest } from "@/lib/api";
import type { ProfessionalList } from "@/lib/professionals";
import type { Student } from "@/lib/students";
import { useApiResource } from "@/lib/use-api-resource";

export function StudentTransferPanel({
  student,
  transferred,
}: {
  student: Student;
  transferred: () => void;
}) {
  const [query, setQuery] = useState("");
  const [destination, setDestination] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const dialog = useRef<HTMLDialogElement>(null);
  const guard = useRef(false);
  const router = useRouter();
  const professionals = useApiResource<ProfessionalList>(
    `/master/professionals?is_active=true&page_size=20&q=${encodeURIComponent(query)}`,
  );
  const selected = professionals.data?.items.find(
    (item) => item.id === destination,
  );
  function close() {
    if (!busy) dialog.current?.close();
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (guard.current || !destination) return;
    guard.current = true;
    setBusy(true);
    setError("");
    try {
      await apiRequest(`/master/students/${student.id}/transfer`, {
        method: "POST",
        body: JSON.stringify({
          new_professional_id: destination,
          expected_professional_id: student.professional_id,
          reason: reason.trim(),
        }),
      });
      dialog.current?.close();
      setDestination("");
      setReason("");
      transferred();
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401)
        router.replace("/login");
      else
        setError(
          cause instanceof ApiError && cause.status === 409
            ? "Os dados mudaram ou há uma reavaliação em análise. Feche esta janela e atualize o aluno."
            : cause instanceof Error
              ? cause.message
              : "Não foi possível transferir o aluno.",
        );
    } finally {
      guard.current = false;
      setBusy(false);
    }
  }
  if (student.status === "REJECTED")
    return (
      <p className="mt-4 text-sm text-muted-foreground">
        Cadastro rejeitado não pode ser transferido.
      </p>
    );
  return (
    <section className="mt-6 rounded-lg border bg-white p-5">
      <h2 className="text-lg font-semibold">Profissional responsável</h2>
      <p className="mt-2 text-sm">
        {student.professional_name || "Sem profissional"}
      </p>
      <button
        className="master-secondary mt-4 min-h-11"
        type="button"
        onClick={() => {
          setError("");
          dialog.current?.showModal();
        }}
      >
        Transferir aluno
      </button>
      <dialog
        ref={dialog}
        aria-labelledby="transfer-title"
        onCancel={(event) => {
          if (busy) event.preventDefault();
        }}
        className="m-auto w-[calc(100%_-_2rem)] max-w-xl rounded-lg border bg-white p-5 shadow-lg backdrop:bg-black/35"
      >
        <form className="space-y-5" onSubmit={submit} aria-busy={busy}>
          <h2 id="transfer-title" className="text-xl font-semibold">
            {student.professional_id
              ? "Confirmar transferência"
              : "Atribuir profissional"}
          </h2>
          <p className="text-sm">
            De:{" "}
            <strong>{student.professional_name || "Sem profissional"}</strong>
          </p>
          <label className="block text-sm">
            Buscar profissional ativo
            <input
              className="auth-input mt-2"
              value={query}
              maxLength={120}
              onChange={(event) => {
                setQuery(event.target.value);
                setDestination("");
              }}
              placeholder="Nome ou e-mail"
            />
          </label>
          <label className="block text-sm">
            Novo profissional
            <select
              className="auth-input mt-2"
              required
              value={destination}
              onChange={(event) => setDestination(event.target.value)}
            >
              <option value="">Selecione</option>
              {professionals.data?.items
                .filter((item) => item.id !== student.professional_id)
                .map((item) => (
                  <option value={item.id} key={item.id}>
                    {item.name}
                  </option>
                ))}
            </select>
          </label>
          {professionals.error && (
            <ErrorState
              message={professionals.error}
              retry={professionals.reload}
            />
          )}
          <label className="block text-sm">
            Motivo administrativo
            <textarea
              className="auth-input mt-2 min-h-28"
              required
              minLength={5}
              maxLength={500}
              value={reason}
              onChange={(event) => setReason(event.target.value)}
            />
          </label>
          <p className="text-sm">
            Para:{" "}
            <strong>{selected?.name || "Selecione um profissional"}</strong>. O
            histórico será preservado e o acesso da carteira mudará
            imediatamente.
          </p>
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          <div className="flex flex-wrap justify-end gap-3">
            <button
              type="button"
              className="master-secondary min-h-11"
              disabled={busy}
              onClick={close}
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="master-primary min-h-11"
              disabled={busy || !selected}
            >
              {busy ? "Transferindo…" : "Confirmar transferência"}
            </button>
          </div>
        </form>
      </dialog>
    </section>
  );
}
