"use client";

import {
  LayoutDashboard,
  Leaf,
  LogOut,
  UserRound,
  UsersRound,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { type ReactNode, useEffect, useRef, useState } from "react";
import { ErrorState, LoadingState } from "@/components/master/resource-state";
import { apiRequest, type User } from "@/lib/api";
import { homeForRole } from "@/lib/students";
import { useApiResource } from "@/lib/use-api-resource";

const navigation = {
  MASTER: [
    { href: "/master", label: "Dashboard", icon: LayoutDashboard },
    { href: "/master/professionals", label: "Profissionais", icon: UsersRound },
    { href: "/master/students", label: "Alunos", icon: UserRound },
  ],
  PROFESSIONAL: [
    { href: "/professional", label: "Dashboard", icon: LayoutDashboard },
    { href: "/professional/students", label: "Meus alunos", icon: UsersRound },
  ],
  STUDENT: [
    { href: "/student", label: "Início", icon: LayoutDashboard },
    { href: "/student/profile", label: "Meu perfil", icon: UserRound },
    { href: "/student/diet", label: "Minha dieta", icon: Leaf },
  ],
};
const labels = {
  MASTER: "Administração",
  PROFESSIONAL: "Área profissional",
  STUDENT: "Meu acompanhamento",
};

export function AppShell({
  allowedRole,
  children,
}: {
  allowedRole: User["role"];
  children: ReactNode;
}) {
  const {
    data: user,
    loading,
    error,
    reload,
  } = useApiResource<User>("/auth/me");
  const router = useRouter();
  const pathname = usePathname();
  const guard = useRef(false);
  const [leaving, setLeaving] = useState(false);
  const [logoutError, setLogoutError] = useState("");
  useEffect(() => {
    if (user && user.role !== allowedRole)
      router.replace(homeForRole(user.role));
  }, [user, allowedRole, router]);
  async function logout() {
    if (guard.current) return;
    guard.current = true;
    setLeaving(true);
    setLogoutError("");
    try {
      await apiRequest<void>("/auth/logout", { method: "POST" });
      router.replace("/login");
    } catch (cause) {
      setLogoutError(
        cause instanceof Error ? cause.message : "Não foi possível sair.",
      );
      guard.current = false;
      setLeaving(false);
    }
  }
  if (loading)
    return (
      <main className="p-8">
        <LoadingState />
      </main>
    );
  if (error)
    return (
      <main className="p-8">
        <ErrorState message={error} retry={reload} />
      </main>
    );
  if (user?.role !== allowedRole)
    return (
      <main className="p-8">
        <LoadingState />
      </main>
    );
  const home = homeForRole(user.role);
  return (
    <div className="min-h-screen bg-background md:grid md:grid-cols-[180px_minmax(0,1fr)] xl:grid-cols-[230px_minmax(0,1fr)]">
      <a
        href="#app-content"
        className="sr-only focus:not-sr-only focus:fixed focus:z-50 focus:bg-white focus:p-3"
      >
        Ir para o conteúdo
      </a>
      <aside className="border-b border-border bg-white md:sticky md:top-0 md:h-screen md:border-r md:border-b-0">
        <Link
          href={home}
          className="flex min-h-20 items-center gap-2 px-5 py-5 text-lg font-semibold tracking-tight"
        >
          <Leaf className="size-6 shrink-0 text-primary" aria-hidden="true" />
          NUTRAMOVE
        </Link>
        <p className="px-5 text-xs font-medium uppercase tracking-wider text-muted-foreground">
          {labels[user.role]}
        </p>
        <nav
          aria-label={labels[user.role]}
          className="grid grid-cols-2 gap-1 p-3 sm:grid-cols-3 md:grid-cols-1"
        >
          {navigation[user.role].map(({ href, label, icon: Icon }) => {
            const selected =
              href === home ? pathname === href : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                aria-current={selected ? "page" : undefined}
                className={`flex min-h-11 items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors ${selected ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-secondary hover:text-foreground"}`}
              >
                <Icon className="size-4 shrink-0" aria-hidden="true" />
                {label}
              </Link>
            );
          })}
        </nav>
        <p className="absolute bottom-6 hidden px-5 text-xs text-muted-foreground md:block">
          Nutrição. Movimento. Cuidado.
        </p>
      </aside>
      <div className="min-w-0">
        <header className="flex min-h-20 items-center justify-between gap-3 border-b bg-white px-5 py-3 lg:px-8">
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold">{user.name}</p>
            <Link
              href="/account"
              className="inline-flex min-h-11 items-center text-xs text-muted-foreground underline-offset-4 hover:underline"
            >
              Minha conta
            </Link>
          </div>
          <button
            type="button"
            disabled={leaving}
            onClick={() => void logout()}
            className="master-secondary min-h-11 shrink-0"
          >
            <LogOut className="size-4" aria-hidden="true" />
            {leaving ? "Saindo…" : "Sair"}
          </button>
        </header>
        <main id="app-content" className="mx-auto max-w-7xl p-5 lg:p-8">
          {logoutError && (
            <p role="alert" className="mb-5 text-sm text-destructive">
              {logoutError}
            </p>
          )}
          {children}
        </main>
      </div>
    </div>
  );
}
