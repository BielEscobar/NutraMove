"use client";
import { TrendingUp } from "lucide-react";
import Link from "next/link";
import { ErrorState, LoadingState } from "@/components/master/resource-state";
import { bmiNote, type Evolution, number } from "@/lib/evolution";
import { useApiResource } from "@/lib/use-api-resource";
export function EvolutionSummary() {
  const { data, loading, error, reload } = useApiResource<Evolution>(
    "/student/evolution?period=7d",
  );
  return (
    <section className="mt-5 rounded-lg border bg-white p-5">
      <h2 className="flex items-center gap-2 font-semibold">
        <TrendingUp className="size-5 text-primary" aria-hidden="true" />
        Minha evolução
      </h2>
      {loading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState message={error} retry={reload} />
      ) : data?.current ? (
        <>
          <p className="mt-3 text-sm">
            Peso atual registrado: {number(data.current.weight_kg)}
            {data.current.weight_kg !== null ? " kg" : ""}
          </p>
          <p className="mt-2 text-sm">
            IMC de referência: {number(data.current.bmi)}
          </p>
          <p className="mt-2 text-xs text-muted-foreground">{bmiNote}</p>
        </>
      ) : (
        <p className="mt-3 text-sm text-muted-foreground">
          Ainda não há avaliações registradas.
        </p>
      )}
      <Link className="master-secondary mt-4" href="/student/evolution">
        Ver evolução
      </Link>
    </section>
  );
}
