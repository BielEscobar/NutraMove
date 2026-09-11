"use client";
import Link from "next/link";
import { ErrorState, LoadingState } from "@/components/master/resource-state";
import { useApiResource } from "@/lib/use-api-resource";
import {
  type VersionSummary,
  type WorkoutArea,
  type WorkoutSummary,
  workoutStatuses,
} from "@/lib/workouts";

export function WorkoutHistory({
  area,
  id,
}: {
  area: WorkoutArea;
  id: string;
}) {
  const parent = useApiResource<WorkoutSummary>(
    `/${area}/workouts/${encodeURIComponent(id)}`,
  );
  const versions = useApiResource<VersionSummary[]>(
    `/${area}/workouts/${encodeURIComponent(id)}/versions`,
  );
  if (parent.loading || versions.loading) return <LoadingState />;
  if (parent.error || versions.error)
    return (
      <ErrorState
        message={parent.error || versions.error}
        retry={() => {
          void parent.reload();
          void versions.reload();
        }}
      />
    );
  return (
    <div>
      {parent.data && (
        <Link
          href={`/${area}/students/${parent.data.student_id}/workouts`}
          className="text-sm text-primary underline"
        >
          Voltar aos planos
        </Link>
      )}
      <h1 className="mt-5 break-words text-2xl font-semibold">
        {parent.data?.name}
      </h1>
      <p className="mt-2 text-sm text-muted-foreground">
        Histórico de versões. Para alterar uma versão publicada, duplique-a.
      </p>
      {area === "professional" && (
        <Link
          href={`/professional/workouts/${id}/versions/new`}
          className="master-secondary mt-5"
        >
          Nova versão em branco
        </Link>
      )}
      <ul className="mt-6 space-y-3">
        {versions.data?.map((version) => (
          <li key={version.id}>
            <Link
              href={`/${area}/workout-versions/${version.id}`}
              className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-white p-5 hover:border-primary"
            >
              <div className="min-w-0">
                <h2 className="break-words font-medium">
                  Versão {version.version_number} · {version.name}
                </h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  {version.source === "MANUAL"
                    ? "Criado manualmente"
                    : "Origem: IA"}{" "}
                  · {new Date(version.created_at).toLocaleDateString("pt-BR")}
                </p>
              </div>
              <span className="text-sm font-medium text-primary">
                {workoutStatuses[version.status]}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
