"use client";

import { LoaderCircle, LogOut } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { NutraMoveLogo } from "@/components/nutramove-logo";
import { ApiError, apiRequest, type User } from "@/lib/api";

const roleLabels: Record<User["role"], string> = {
  MASTER: "Master",
  PROFESSIONAL: "Profissional",
  STUDENT: "Aluno",
};

export default function AccountPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState("");
  const [leaving, setLeaving] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    apiRequest<User>("/auth/me", { signal: controller.signal })
      .then((currentUser) => {
        if (!controller.signal.aborted) setUser(currentUser);
      })
      .catch((cause: unknown) => {
        if (controller.signal.aborted) return;
        if (cause instanceof ApiError && cause.status === 401) {
          router.replace("/login");
        } else {
          setError(
            cause instanceof Error
              ? cause.message
              : "Não foi possível carregar sua conta.",
          );
        }
      });
    return () => controller.abort();
  }, [router]);

  async function logout() {
    setLeaving(true);
    setError("");
    try {
      await apiRequest<void>("/auth/logout", { method: "POST" });
      setUser(null);
      router.replace("/login");
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Não foi possível sair.",
      );
      setLeaving(false);
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-6 py-5">
          <NutraMoveLogo className="h-auto w-32" priority />
          {user && (
            <button
              type="button"
              onClick={logout}
              disabled={leaving}
              className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-muted-foreground hover:bg-secondary focus-visible:outline-2 focus-visible:outline-primary disabled:opacity-60"
            >
              <LogOut className="size-4" aria-hidden="true" />{" "}
              {leaving ? "Saindo…" : "Sair"}
            </button>
          )}
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-12">
        {error && (
          <div role="alert" className="mb-6 text-sm text-destructive">
            <p>{error}</p>
            {!user && (
              <button
                type="button"
                className="mt-3 underline"
                onClick={() => {
                  setError("");
                  window.location.reload();
                }}
              >
                Tentar novamente
              </button>
            )}
          </div>
        )}
        {user ? (
          <section className="max-w-lg rounded-lg border border-border bg-white p-6 shadow-sm">
            <p className="text-xs font-medium uppercase tracking-wider text-primary">
              Minha conta
            </p>
            <h1 className="mt-3 text-2xl font-semibold">Olá, {user.name}</h1>
            <p role="status" className="mt-2 text-sm text-muted-foreground">
              Você entrou com sucesso.
            </p>
            <dl className="mt-6 space-y-4 border-t border-border pt-5 text-sm">
              <div>
                <dt className="text-muted-foreground">E-mail</dt>
                <dd className="mt-1 break-all">{user.email}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Perfil</dt>
                <dd className="mt-1">{roleLabels[user.role]}</dd>
              </div>
            </dl>
            {user.role === "PROFESSIONAL" && (
              <Link
                href="/professional/students"
                className="master-primary mt-6"
              >
                Meus alunos
              </Link>
            )}
            {user.role === "STUDENT" && (
              <Link href="/student" className="master-primary mt-6">
                Meu cadastro
              </Link>
            )}
            {user.role === "MASTER" && (
              <Link href="/master" className="master-primary mt-6">
                Abrir administração
              </Link>
            )}
          </section>
        ) : (
          !error && (
            <p
              role="status"
              className="flex items-center gap-2 text-sm text-muted-foreground"
            >
              <LoaderCircle
                className="size-4 animate-spin"
                aria-hidden="true"
              />{" "}
              Carregando sua conta…
            </p>
          )
        )}
      </main>
    </div>
  );
}
