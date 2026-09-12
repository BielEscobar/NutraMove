"use client";
import Link from "next/link";
import { ErrorState, LoadingState } from "@/components/master/resource-state";
import { type HydrationSummary, volume } from "@/lib/hydration";
import { useApiResource } from "@/lib/use-api-resource";

export function HydrationProgress({ data }: { data: HydrationSummary }) {
  return (
    <div className="space-y-3">
      <p className="text-2xl font-semibold text-brand-deep">
        {volume(data.consumed_ml)}
        {data.goal_ml !== null && (
          <span className="text-base font-normal text-muted-foreground">
            {" "}
            / {volume(data.goal_ml)}
          </span>
        )}
      </p>
      {data.percentage !== null ? (
        <>
          <progress
            aria-label="Progresso da hidratação de hoje"
            max={100}
            value={Math.min(100, data.percentage)}
            className="h-3 w-full accent-primary"
          />
          <p className="text-sm">
            {data.percentage.toLocaleString("pt-BR")}% da meta ·{" "}
            {data.remaining_ml === 0
              ? "Meta registrada alcançada"
              : `Faltam ${volume(data.remaining_ml ?? 0)}`}
          </p>
        </>
      ) : (
        <p className="text-sm text-muted-foreground">
          Meta ainda não definida.
        </p>
      )}
    </div>
  );
}
export function HydrationCard() {
  const resource = useApiResource<HydrationSummary>(
    "/student/hydration/summary",
  );
  return (
    <section className="mt-5 space-y-4 rounded-lg border bg-white p-5">
      <h2 className="font-semibold">Água hoje</h2>
      {resource.loading ? (
        <LoadingState />
      ) : resource.error ? (
        <ErrorState message={resource.error} retry={resource.reload} />
      ) : (
        resource.data && <HydrationProgress data={resource.data} />
      )}
      <Link className="master-secondary" href="/student/hydration">
        Registrar água
      </Link>
    </section>
  );
}
