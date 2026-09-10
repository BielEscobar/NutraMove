"use client";

import { CheckCircle2, LoaderCircle } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useRef, useState } from "react";
import { ApiError, apiRequest } from "@/lib/api";
import type { Professional } from "@/lib/professionals";

export function ProfessionalForm({
  professional,
}: {
  professional?: Professional;
}) {
  const router = useRouter();
  const submitting = useRef(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState<Professional | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting.current) return;
    const form = new FormData(event.currentTarget);
    const password = String(form.get("password") ?? "");
    if (!professional && password !== String(form.get("confirmation") ?? "")) {
      setError("As senhas não coincidem.");
      return;
    }
    submitting.current = true;
    setBusy(true);
    setError("");
    const body = {
      name: String(form.get("name") ?? "").trim(),
      email: String(form.get("email") ?? "").trim(),
      specialty: String(form.get("specialty") ?? "").trim() || null,
      ...(!professional ? { password } : {}),
    };
    try {
      const result = await apiRequest<Professional>(
        professional
          ? `/master/professionals/${professional.id}`
          : "/master/professionals",
        { method: professional ? "PATCH" : "POST", body: JSON.stringify(body) },
      );
      setSaved(result);
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401)
        router.replace("/login");
      else if (cause instanceof ApiError && cause.status === 403)
        router.replace("/account");
      else
        setError(
          cause instanceof Error
            ? cause.message
            : "Não foi possível salvar o profissional.",
        );
    } finally {
      setBusy(false);
      submitting.current = false;
    }
  }

  if (saved)
    return (
      <section className="max-w-2xl rounded-lg border border-border bg-white p-6">
        <div role="status" className="flex items-start gap-3">
          <CheckCircle2
            className="mt-0.5 size-5 text-primary"
            aria-hidden="true"
          />
          <div>
            <h2 className="font-semibold">
              {professional ? "Cadastro atualizado" : "Profissional cadastrado"}
            </h2>
            <p className="mt-2 text-sm text-muted-foreground">
              As informações de {saved.name} foram salvas com sucesso.
            </p>
          </div>
        </div>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link
            href={`/master/professionals/${saved.id}`}
            className="master-primary"
          >
            Ver profissional
          </Link>
          <Link href="/master/professionals" className="master-secondary">
            Voltar à lista
          </Link>
        </div>
      </section>
    );

  return (
    <form
      onSubmit={submit}
      className="max-w-2xl rounded-lg border border-border bg-white p-6 shadow-sm"
      aria-busy={busy}
    >
      <h2 className="font-semibold">Dados do profissional</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        Nome e e-mail identificam a conta de acesso.
      </p>
      <fieldset disabled={busy} className="mt-6 grid gap-5">
        <div>
          <label htmlFor="name" className="mb-2 block text-sm font-medium">
            Nome completo *
          </label>
          <input
            className="auth-input"
            id="name"
            name="name"
            autoComplete="name"
            defaultValue={professional?.name}
            required
            minLength={1}
            maxLength={120}
          />
        </div>
        <div>
          <label htmlFor="email" className="mb-2 block text-sm font-medium">
            E-mail *
          </label>
          <input
            className="auth-input"
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            defaultValue={professional?.email}
            required
            maxLength={320}
          />
        </div>
        <div>
          <label htmlFor="specialty" className="mb-2 block text-sm font-medium">
            Especialidade{" "}
            <span className="font-normal text-muted-foreground">
              (opcional)
            </span>
          </label>
          <input
            className="auth-input"
            id="specialty"
            name="specialty"
            defaultValue={professional?.specialty ?? ""}
            maxLength={120}
            placeholder="Ex.: Nutrição esportiva"
          />
        </div>
        {!professional && (
          <div className="grid gap-5 border-t border-border pt-5 sm:grid-cols-2">
            <div>
              <label
                htmlFor="password"
                className="mb-2 block text-sm font-medium"
              >
                Senha de acesso *
              </label>
              <input
                className="auth-input"
                id="password"
                name="password"
                type="password"
                autoComplete="new-password"
                required
                minLength={12}
                maxLength={128}
                aria-describedby="password-hint"
              />
              <p
                id="password-hint"
                className="mt-2 text-xs text-muted-foreground"
              >
                De 12 a 128 caracteres.
              </p>
            </div>
            <div>
              <label
                htmlFor="confirmation"
                className="mb-2 block text-sm font-medium"
              >
                Confirme a senha *
              </label>
              <input
                className="auth-input"
                id="confirmation"
                name="confirmation"
                type="password"
                autoComplete="new-password"
                required
                minLength={12}
                maxLength={128}
              />
            </div>
          </div>
        )}
      </fieldset>
      {error && (
        <p role="alert" className="mt-5 text-sm text-destructive">
          {error}
        </p>
      )}
      <div className="mt-7 flex flex-wrap gap-3 border-t border-border pt-5">
        <button
          type="submit"
          disabled={busy}
          className="master-primary disabled:opacity-60"
        >
          {busy && (
            <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />
          )}
          {busy
            ? "Salvando…"
            : professional
              ? "Salvar alterações"
              : "Cadastrar profissional"}
        </button>
        {!busy && (
          <Link
            href={
              professional
                ? `/master/professionals/${professional.id}`
                : "/master/professionals"
            }
            className="master-secondary"
          >
            Cancelar
          </Link>
        )}
      </div>
    </form>
  );
}
