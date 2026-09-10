"use client";
import { DietReader } from "@/components/diets/diet-reader";
import { ErrorState, LoadingState } from "@/components/master/resource-state";
import type { PublishedDiet } from "@/lib/diets";
import { useApiResource } from "@/lib/use-api-resource";

export default function StudentDietPage() {
  const { data, loading, error, reload } = useApiResource<{
    diet: PublishedDiet | null;
  }>("/student/diet");
  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} retry={reload} />;
  return (
    <div>
      <p className="mb-5 text-sm font-medium text-primary">Minha dieta</p>
      {data?.diet ? (
        <DietReader key={data.diet.approved_at} diet={data.diet} />
      ) : (
        <section className="rounded-lg border border-dashed bg-white p-6">
          <h1 className="text-xl font-semibold">
            Seu plano alimentar ainda não foi publicado.
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
