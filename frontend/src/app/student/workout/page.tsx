"use client";
import { ErrorState, LoadingState } from "@/components/master/resource-state";
import { WorkoutReader } from "@/components/workouts/workout-reader";
import { useApiResource } from "@/lib/use-api-resource";
import type { PublishedWorkout } from "@/lib/workouts";

export default function StudentWorkoutPage() {
  const { data, loading, error, reload } = useApiResource<{
    workout: PublishedWorkout | null;
  }>("/student/workout");
  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} retry={reload} />;
  return (
    <div>
      <p className="mb-5 text-sm font-medium text-primary">Meu treino</p>
      {data?.workout ? (
        <WorkoutReader key={data.workout.approved_at} workout={data.workout} />
      ) : (
        <section className="rounded-lg border border-dashed bg-white p-6">
          <h1 className="text-xl font-semibold">
            Seu treino ainda não foi publicado.
          </h1>
          <p className="mt-3 text-sm leading-6 text-muted-foreground">
            Quando seu acompanhamento estiver ativo e o profissional publicar um
            plano, ele aparecerá aqui.
          </p>
        </section>
      )}
    </div>
  );
}
