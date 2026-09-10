"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { ProfessionalForm } from "@/components/master/professional-form";
import { ErrorState, LoadingState } from "@/components/master/resource-state";
import type { Professional } from "@/lib/professionals";
import { useMasterResource } from "@/lib/use-master-resource";

export function ProfessionalEditor({ id }: { id: string }) {
  const { data, loading, error, reload } = useMasterResource<Professional>(
    `/master/professionals/${encodeURIComponent(id)}`,
  );
  return (
    <div>
      <Link
        href={`/master/professionals/${encodeURIComponent(id)}`}
        className="mb-6 inline-flex items-center gap-2 text-sm text-muted-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden="true" /> Voltar ao cadastro
      </Link>
      <h1 className="mb-7 text-2xl font-semibold tracking-tight">
        Editar profissional
      </h1>
      {loading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState message={error} retry={reload} />
      ) : (
        data && <ProfessionalForm professional={data} />
      )}
    </div>
  );
}
