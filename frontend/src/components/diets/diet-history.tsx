"use client";
import Link from "next/link";
import { ErrorState, LoadingState } from "@/components/master/resource-state";
import {
  type DietArea,
  type DietSummary,
  dietStatuses,
  type VersionSummary,
} from "@/lib/diets";
import { useApiResource } from "@/lib/use-api-resource";

export function DietHistory({ area, id }: { area: DietArea; id: string }) {
  const parent = useApiResource<DietSummary>(
    `/${area}/diets/${encodeURIComponent(id)}`,
  );
  const versions = useApiResource<VersionSummary[]>(
    `/${area}/diets/${encodeURIComponent(id)}/versions`,
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
          href={`/${area}/students/${parent.data.student_id}/diets`}
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
          href={`/professional/diets/${id}/versions/new`}
          className="master-secondary mt-5"
        >
          Nova versão em branco
        </Link>
      )}
      <ul className="mt-6 space-y-3">
        {versions.data?.map((version) => (
          <li key={version.id}>
            <Link
              href={`/${area}/diet-versions/${version.id}`}
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
                {dietStatuses[version.status]}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
