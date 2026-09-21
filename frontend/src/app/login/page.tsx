"use client";

import { ArrowRight, LoaderCircle } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";
import { NutraMoveLogo } from "@/components/nutramove-logo";
import { ApiError, apiRequest, type User } from "@/lib/api";
import { homeForRole } from "@/lib/students";

export default function LoginPage() {
  const router = useRouter();
  const [checking, setChecking] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    apiRequest<User>("/auth/me", { signal: controller.signal })
      .then((user) => {
        if (!controller.signal.aborted) router.replace(homeForRole(user.role));
      })
      .catch((cause: unknown) => {
        if (controller.signal.aborted) return;
        if (!(cause instanceof ApiError) || cause.status !== 401) {
          setError(
            "Não foi possível verificar sua sessão. Você pode tentar entrar novamente.",
          );
        }
        setChecking(false);
      });
    return () => controller.abort();
  }, [router]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setError("");
    const form = new FormData(event.currentTarget);
    try {
      await apiRequest<User>("/auth/login", {
        method: "POST",
        body: JSON.stringify({
          email: String(form.get("email") ?? "").trim(),
          password: String(form.get("password") ?? ""),
        }),
      });
      const user = await apiRequest<User>("/auth/me");
      router.replace(homeForRole(user.role));
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Não foi possível entrar.",
      );
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen flex-col bg-background lg:flex-row">
      <section className="flex flex-col justify-between bg-brand-deep px-8 py-10 text-white lg:w-5/12 lg:px-14 lg:py-14">
        <NutraMoveLogo className="h-auto w-44" priority />
        <div className="my-12 max-w-sm lg:my-auto">
          <p className="mb-4 text-sm font-medium text-brand-mint">
            Cuidado em movimento
          </p>
          <h1 className="text-3xl font-semibold leading-tight lg:text-4xl">
            Um espaço para conectar saúde e evolução.
          </h1>
          <p className="mt-5 text-sm leading-7 text-white/80">
            Acesse sua conta para continuar no NUTRAMOVE.
          </p>
        </div>
        <p className="hidden text-xs text-white/60 lg:block">
          Nutrição. Movimento. Cuidado.
        </p>
      </section>
      <section className="flex flex-1 items-center justify-center px-6 py-14">
        <div className="w-full max-w-sm">
          <NutraMoveLogo className="mb-7 h-auto w-32" priority />
          <h2 className="text-2xl font-semibold tracking-tight">
            Bem-vindo de volta
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Entre com seu e-mail e senha.
          </p>
          {checking ? (
            <p
              role="status"
              className="mt-8 flex items-center gap-2 text-sm text-muted-foreground"
            >
              <LoaderCircle
                className="size-4 animate-spin"
                aria-hidden="true"
              />
              Verificando sessão…
            </p>
          ) : (
            <form
              className="mt-8 space-y-5"
              onSubmit={handleSubmit}
              aria-busy={submitting}
            >
              <div className="space-y-2">
                <label htmlFor="email" className="text-sm font-medium">
                  E-mail
                </label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="username"
                  required
                  maxLength={320}
                  disabled={submitting}
                  className="auth-input"
                  placeholder="voce@exemplo.com"
                />
              </div>
              <div className="space-y-2">
                <label htmlFor="password" className="text-sm font-medium">
                  Senha
                </label>
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  maxLength={128}
                  disabled={submitting}
                  className="auth-input"
                />
              </div>
              {error && (
                <p role="alert" className="text-sm text-destructive">
                  {error}
                </p>
              )}
              <button
                type="submit"
                disabled={submitting}
                className="flex h-11 w-full items-center justify-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-colors hover:bg-brand-deep focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:cursor-wait disabled:opacity-60"
              >
                {submitting ? (
                  <LoaderCircle
                    className="size-4 animate-spin"
                    aria-hidden="true"
                  />
                ) : null}
                {submitting ? "Entrando…" : "Entrar"}
                {!submitting && (
                  <ArrowRight className="size-4" aria-hidden="true" />
                )}
              </button>
            </form>
          )}
          <p className="mt-7 text-xs leading-5 text-muted-foreground">
            <Link className="text-primary underline" href="/register">
              Criar meu cadastro de aluno
            </Link>
          </p>
        </div>
      </section>
    </main>
  );
}
