"use client";

import {
  Clock3,
  Dumbbell,
  Leaf,
  Ruler,
  Scale,
  Target,
  TrendingUp,
} from "lucide-react";
import Link from "next/link";
import { EmptyState, MetricCard } from "@/components/dashboard/metric-card";
import { ErrorState, LoadingState } from "@/components/master/resource-state";
import type { StudentDashboard } from "@/lib/dashboard";
import { goals, statuses } from "@/lib/students";
import { useApiResource } from "@/lib/use-api-resource";

export default function StudentPage() {
  const { data, loading, error, reload } =
    useApiResource<StudentDashboard>("/student/dashboard");
  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} retry={reload} />;
  if (!data)
    return (
      <EmptyState
        title="Cadastro indisponível"
        description="Não foi possível encontrar seu cadastro."
      />
    );
  const messages = {
    PENDING_APPROVAL: [
      "Seu cadastro está em análise.",
      "Assim que seu acompanhamento for preparado, você terá acesso aos seus planos.",
    ],
    ACTIVE: [
      "Seu cadastro foi aprovado.",
      "Acompanhe suas informações e converse com seu profissional sobre os próximos passos.",
    ],
    REJECTED: [
      "Seu cadastro não foi aprovado.",
      "Entre em contato com o responsável pelo cadastro para esclarecer sua situação.",
    ],
    INACTIVE: [
      "Seu acompanhamento está inativo.",
      "Entre em contato com o responsável pelo acompanhamento.",
    ],
  }[data.status];
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wider text-primary">
        Meu acompanhamento
      </p>
      <h1 className="mt-2 break-words text-2xl font-semibold">
        Olá, {data.name}
      </h1>
      <p className="mt-2 text-sm text-muted-foreground">
        Seu espaço de cuidado e movimento.
      </p>
      <section className="mt-7 rounded-lg border border-primary/20 bg-primary/5 p-5">
        <div className="flex items-start gap-3">
          <Clock3
            className="mt-0.5 size-5 shrink-0 text-primary"
            aria-hidden="true"
          />
          <div>
            <h2 className="font-semibold text-brand-deep">{messages[0]}</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              {messages[1]}
            </p>
          </div>
        </div>
      </section>
      <section
        aria-label="Meu cadastro"
        className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
      >
        <MetricCard label="Objetivo" value={goals[data.goal]} icon={Target} />
        <MetricCard
          label="Peso informado"
          value={`${data.weight.toLocaleString("pt-BR")} kg`}
          icon={Scale}
        />
        <MetricCard
          label="Altura informada"
          value={`${data.height.toLocaleString("pt-BR")} cm`}
          icon={Ruler}
        />
        <MetricCard
          label="Situação"
          value={statuses[data.status]}
          icon={Clock3}
        />
      </section>
      <section className="mt-5 rounded-lg border bg-white p-6">
        <h2 className="font-semibold">Profissional responsável</h2>
        <p className="mt-2 break-words text-sm text-muted-foreground">
          {data.professional_name ||
            "Ainda não há profissional atribuído ao seu cadastro."}
        </p>
        {data.goal_detail && (
          <p className="mt-4 break-words text-sm">
            Seu objetivo: {data.goal_detail}
          </p>
        )}
        <Link
          href="/student/profile"
          className="master-secondary mt-5 min-h-11"
        >
          Ver meu perfil
        </Link>
      </section>
      <Link className="master-primary mt-5" href="/student/diet">
        <Leaf className="size-4" aria-hidden="true" />
        Minha dieta
      </Link>
      {data.status === "ACTIVE" && (
        <section
          aria-label="Áreas em preparação"
          className="mt-7 grid gap-4 lg:grid-cols-3"
        >
          {[
            {
              title: "Meu treino",
              text: "Ainda não disponível.",
              icon: Dumbbell,
            },

            {
              title: "Minha evolução",
              text: "Em preparação.",
              icon: TrendingUp,
            },
          ].map(({ title, text, icon: Icon }) => (
            <div
              key={title}
              className="rounded-lg border border-dashed bg-white p-5"
            >
              <Icon
                className="mb-3 size-5 text-muted-foreground"
                aria-hidden="true"
              />
              <h2 className="font-medium">{title}</h2>
              <p className="mt-2 text-sm text-muted-foreground">{text}</p>
            </div>
          ))}
        </section>
      )}
    </div>
  );
}
