"use client";
import Link from "next/link";
import { AIGenerator } from "@/components/ai/ai-generator";
import { ErrorState, LoadingState } from "@/components/master/resource-state";
import { useApiResource } from "@/lib/use-api-resource";
import type { WorkoutArea, WorkoutSummary } from "@/lib/workouts";

export function WorkoutList({
  area,
  studentId,
}: {
  area: WorkoutArea;
  studentId: string;
}) {
  const { data, loading, error, reload } = useApiResource<WorkoutSummary[]>(
    `/${area}/students/${encodeURIComponent(studentId)}/workouts`,
  );
  return (
    <div>
      <Link
        href={`/${area}/students/${studentId}`}
        className="text-sm text-primary underline"
      >
        Voltar ao aluno
      </Link>
      <div className="my-6 flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold">Planos de treino</h1>
        {area === "professional" && (
          <div className="flex flex-wrap gap-2">
            <AIGenerator
              kind="workout"
              studentId={studentId}
              onGenerated={() => void reload()}
            />
            <Link
              href={`/professional/students/${studentId}/workouts/new`}
              className="master-primary"
            >
              Criar treino
            </Link>
          </div>
        )}
      </div>
      {loading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState message={error} retry={reload} />
      ) : data && data.length === 0 ? (
        <p className="rounded-lg border border-dashed bg-white p-6">
          Nenhum treino cadastrado para este aluno.
        </p>
      ) : (
        <ul className="space-y-3">
          {data?.map((workout) => (
            <li key={workout.id}>
              <Link
                className="block rounded-lg border bg-white p-5 hover:border-primary"
                href={`/${area}/workouts/${workout.id}`}
              >
                <h2 className="break-words font-semibold">{workout.name}</h2>
                <p className="mt-2 text-sm text-muted-foreground">
                  Criado em{" "}
                  {new Date(workout.created_at).toLocaleDateString("pt-BR")} ·
                  Ver versões
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
