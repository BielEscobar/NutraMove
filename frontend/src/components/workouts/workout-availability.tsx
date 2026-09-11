"use client";
import { Dumbbell } from "lucide-react";
import Link from "next/link";
import { ErrorState, LoadingState } from "@/components/master/resource-state";
import { useApiResource } from "@/lib/use-api-resource";
import type { PublishedWorkout } from "@/lib/workouts";
export function WorkoutAvailability() {
  const { data, loading, error, reload } = useApiResource<{
    workout: PublishedWorkout | null;
  }>("/student/workout");
  return (
    <section className="mt-5 rounded-lg border bg-white p-5">
      <h2 className="flex items-center gap-2 font-semibold">
        <Dumbbell className="size-5 text-primary" aria-hidden="true" />
        Meu treino
      </h2>
      {loading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState message={error} retry={reload} />
      ) : data?.workout ? (
        <>
          <p className="mt-3 break-words text-sm">
            Plano disponível: {data.workout.name}
          </p>
          <Link
            href="/student/workout"
            className="master-primary mt-4 min-h-11"
          >
            Ver treino
          </Link>
        </>
      ) : (
        <p className="mt-3 text-sm text-muted-foreground">
          Seu treino ainda não foi publicado.
        </p>
      )}
    </section>
  );
}
