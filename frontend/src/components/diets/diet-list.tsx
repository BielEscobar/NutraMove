"use client";
import Link from "next/link";
import { ErrorState, LoadingState } from "@/components/master/resource-state";
import type { DietArea, DietSummary } from "@/lib/diets";
import { useApiResource } from "@/lib/use-api-resource";

export function DietList({
  area,
  studentId,
}: {
  area: DietArea;
  studentId: string;
}) {
  const { data, loading, error, reload } = useApiResource<DietSummary[]>(
    `/${area}/students/${encodeURIComponent(studentId)}/diets`,
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
        <h1 className="text-2xl font-semibold">Planos alimentares</h1>
        {area === "professional" && (
          <Link
            href={`/professional/students/${studentId}/diets/new`}
            className="master-primary"
          >
            Criar dieta
          </Link>
        )}
      </div>
      {loading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState message={error} retry={reload} />
      ) : data && data.length === 0 ? (
        <p className="rounded-lg border border-dashed bg-white p-6">
          Nenhuma dieta cadastrada para este aluno.
        </p>
      ) : (
        <ul className="space-y-3">
          {data?.map((diet) => (
            <li key={diet.id}>
              <Link
                className="block rounded-lg border bg-white p-5 hover:border-primary"
                href={`/${area}/diets/${diet.id}`}
              >
                <h2 className="break-words font-semibold">{diet.name}</h2>
                <p className="mt-2 text-sm text-muted-foreground">
                  Criada em{" "}
                  {new Date(diet.created_at).toLocaleDateString("pt-BR")} · Ver
                  versões
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
