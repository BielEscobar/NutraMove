"use client";

import { ErrorState, LoadingState } from "@/components/master/resource-state";
import {
  draftFromStudent,
  ProfileSummary,
} from "@/components/students/profile-fields";
import type { Student } from "@/lib/students";
import { useApiResource } from "@/lib/use-api-resource";

export default function StudentProfilePage() {
  const { data, loading, error, reload } =
    useApiResource<Student>("/students/me");
  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} retry={reload} />;
  if (!data) return null;
  const message = {
    PENDING_APPROVAL: [
      "Seu cadastro está em análise.",
      "Assim que seu acompanhamento for preparado, você terá acesso aos seus planos.",
    ],
    ACTIVE: [
      "Seu cadastro foi aprovado.",
      "Seus dados estão disponíveis abaixo. Converse com seu profissional sobre os próximos passos do acompanhamento.",
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
      <h1 className="text-2xl font-semibold">Meu perfil</h1>
      <p className="mt-4 leading-7 text-muted-foreground">{message[1]}</p>
      <section className="mt-8 rounded-lg border bg-white p-6">
        <h2 className="text-lg font-semibold">Meus dados</h2>
        <p className="my-4 break-words">
          {data.name} · {data.email}
        </p>
        <p className="mb-6 text-sm">
          Profissional: {data.professional_name || "Ainda não atribuído"}
        </p>
        <ProfileSummary values={draftFromStudent(data)} />
        <p className="mt-5 text-sm">
          Meta de água:{" "}
          {data.water_goal == null
            ? "Não definida"
            : `${data.water_goal} L/dia`}
        </p>
      </section>
    </div>
  );
}
