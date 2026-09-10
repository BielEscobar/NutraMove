"use client";

import {
  ArrowRight,
  CheckCircle2,
  Clock3,
  UserMinus,
  UserRound,
  UsersRound,
  UserX,
} from "lucide-react";
import Link from "next/link";
import { EmptyState, MetricCard } from "@/components/dashboard/metric-card";
import { ErrorState, LoadingState } from "@/components/master/resource-state";
import type { MasterDashboard, ProfessionalDashboard } from "@/lib/dashboard";
import { statuses } from "@/lib/students";
import { useApiResource } from "@/lib/use-api-resource";

export function ManagementDashboard({
  area,
}: {
  area: "master" | "professional";
}) {
  const { data, loading, error, reload } = useApiResource<
    MasterDashboard | ProfessionalDashboard
  >(`/${area}/dashboard`);
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wider text-primary">
        {area === "master" ? "Visão da plataforma" : "Seu acompanhamento"}
      </p>
      <h1 className="mt-2 text-2xl font-semibold tracking-tight">Dashboard</h1>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">
        {area === "master"
          ? "Profissionais e alunos, em uma visão do momento atual."
          : "Uma visão dos seus alunos e dos cadastros que aguardam sua análise."}
      </p>
      {loading ? (
        <div className="mt-8">
          <LoadingState />
        </div>
      ) : error ? (
        <div className="mt-8">
          <ErrorState message={error} retry={reload} />
        </div>
      ) : (
        data && (
          <>
            <section
              aria-label="Indicadores atuais"
              className="mt-7 grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
            >
              {"professionals_total" in data && (
                <>
                  <MetricCard
                    label="Profissionais cadastrados"
                    value={data.professionals_total}
                    icon={UsersRound}
                  />
                  <MetricCard
                    label="Profissionais ativos"
                    value={data.professionals_active}
                    icon={CheckCircle2}
                  />
                </>
              )}
              <MetricCard
                label={area === "master" ? "Alunos cadastrados" : "Meus alunos"}
                value={data.students.total}
                icon={UsersRound}
              />
              <MetricCard
                label="Alunos ativos"
                value={data.students.active}
                icon={CheckCircle2}
              />
              <MetricCard
                label="Aguardando aprovação"
                value={data.students.pending}
                icon={Clock3}
              />
              <MetricCard
                label="Alunos inativos"
                value={data.students.inactive}
                icon={UserMinus}
              />
              <MetricCard
                label="Cadastros rejeitados"
                value={data.students.rejected}
                icon={UserX}
              />
              {"students_unassigned" in data && (
                <MetricCard
                  label="Sem profissional"
                  value={data.students_unassigned}
                  icon={UserRound}
                />
              )}
            </section>
            <section className="mt-7 grid gap-5 lg:grid-cols-2">
              <div className="rounded-lg border bg-white p-6">
                <h2 className="font-semibold">Para acompanhar</h2>
                <p className="mt-3 text-sm leading-6 text-muted-foreground">
                  {data.students.pending > 0
                    ? `${data.students.pending} cadastro(s) aguardam análise. Consulte os dados antes de aprovar ou rejeitar.`
                    : "Nenhum cadastro aguarda aprovação neste momento."}
                </p>
                {"students_unassigned" in data &&
                  data.students_unassigned > 0 && (
                    <p className="mt-3 text-sm leading-6 text-muted-foreground">
                      {data.students_unassigned} aluno(s) estão sem profissional
                      responsável.
                    </p>
                  )}
                <Link
                  href={`/${area}/students`}
                  className="master-secondary mt-5 min-h-11"
                >
                  Ver {area === "master" ? "alunos" : "meus alunos"}
                  <ArrowRight className="size-4" aria-hidden="true" />
                </Link>
              </div>
              {area === "master" ? (
                <div className="rounded-lg border bg-white p-6">
                  <h2 className="font-semibold">Gestão de profissionais</h2>
                  <p className="mt-3 text-sm leading-6 text-muted-foreground">
                    Consulte cadastros e gerencie o acesso dos profissionais à
                    plataforma.
                  </p>
                  <div className="mt-5 flex flex-wrap gap-3">
                    <Link
                      className="master-primary min-h-11"
                      href="/master/professionals/new"
                    >
                      Novo profissional
                    </Link>
                    <Link
                      className="master-secondary min-h-11"
                      href="/master/professionals"
                    >
                      Ver profissionais
                    </Link>
                  </div>
                </div>
              ) : (
                "recent_students" in data && (
                  <div className="rounded-lg border bg-white p-6">
                    <h2 className="font-semibold">Últimos cadastros</h2>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Até cinco alunos da sua carteira, por data de cadastro.
                    </p>
                    {data.recent_students.length === 0 ? (
                      <p className="mt-5 text-sm text-muted-foreground">
                        Sua carteira ainda não possui alunos.
                      </p>
                    ) : (
                      <ul className="mt-3 divide-y">
                        {data.recent_students.map((student) => (
                          <li key={student.id}>
                            <Link
                              href={`/professional/students/${student.id}`}
                              className="flex min-h-14 items-center justify-between gap-3 py-3 hover:text-primary"
                            >
                              <div className="min-w-0">
                                <p className="truncate text-sm font-medium">
                                  {student.name}
                                </p>
                                <p className="text-xs text-muted-foreground">
                                  {statuses[student.status]}
                                </p>
                              </div>
                              <span className="shrink-0 text-xs text-muted-foreground">
                                {new Date(
                                  student.created_at,
                                ).toLocaleDateString("pt-BR")}
                              </span>
                            </Link>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )
              )}
            </section>
            {data.students.total === 0 && (
              <div className="mt-5">
                <EmptyState
                  title="Ainda não há alunos para acompanhar"
                  description={
                    area === "master"
                      ? "Os cadastros aparecerão aqui quando forem enviados pelo onboarding."
                      : "Os alunos que se cadastrarem com seu vínculo aparecerão nesta área."
                  }
                />
              </div>
            )}
          </>
        )
      )}
    </div>
  );
}
