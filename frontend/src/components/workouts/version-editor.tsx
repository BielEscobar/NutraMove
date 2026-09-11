"use client";
import Link from "next/link";
import { ErrorState, LoadingState } from "@/components/master/resource-state";
import { useApiResource } from "@/lib/use-api-resource";
import type { WorkoutVersion } from "@/lib/workouts";
import { WorkoutEditor } from "./workout-editor";

export function VersionEditor({ id }: { id: string }) {
  const path = `/professional/workout-versions/${encodeURIComponent(id)}`;
  const { data, loading, error, reload } = useApiResource<WorkoutVersion>(path);
  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} retry={reload} />;
  if (!data) return null;
  if (!["DRAFT", "PENDING_REVIEW"].includes(data.status))
    return (
      <section className="rounded-lg border bg-white p-6">
        <h1 className="text-xl font-semibold">
          Esta versão tem conteúdo preservado
        </h1>
        <p className="my-4 text-sm">
          Duplique a versão para criar um novo rascunho editável.
        </p>
        <Link
          href={`/professional/workout-versions/${id}`}
          className="master-primary"
        >
          Ver versão
        </Link>
      </section>
    );
  return (
    <WorkoutEditor
      key={data.id}
      path={path}
      backHref={`/professional/workout-versions/${id}`}
      initial={data}
    />
  );
}
