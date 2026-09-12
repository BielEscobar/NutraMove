"use client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ErrorState, LoadingState } from "@/components/master/resource-state";
import {
  type Area,
  type Assessment,
  bmiNote,
  displayDate,
  measureLabel,
  number,
  type StaffAssessment,
  studentPath,
} from "@/lib/evolution";
import { useApiResource } from "@/lib/use-api-resource";
import { AssessmentForm } from "./assessment-form";
export function AssessmentDetail({
  area,
  id,
  edit = false,
}: {
  area: Area;
  id: string;
  edit?: boolean;
}) {
  const { data, loading, error, reload } = useApiResource<
    Assessment | StaffAssessment
  >(`/${area}/assessments/${encodeURIComponent(id)}`);
  const params = useSearchParams();
  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} retry={reload} />;
  if (!data) return null;
  const staff = "student_id" in data ? data : null;
  if (edit && area === "professional" && staff)
    return (
      <AssessmentForm
        key={`${staff.id}-${staff.edit_revision}`}
        studentId={staff.student_id}
        initial={staff}
      />
    );
  return (
    <div className="space-y-6 [overflow-wrap:anywhere]">
      <Link
        href={`${studentPath(area, staff?.student_id)}/evolution`}
        className="text-sm text-primary underline"
      >
        Voltar à evolução
      </Link>
      {params.get("saved") === "1" && (
        <p role="status" className="text-primary">
          Avaliação salva com sucesso.
        </p>
      )}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">
          Avaliação de {displayDate(data.assessment_date)}
        </h1>
        {area === "professional" && (
          <Link
            className="master-secondary"
            href={`/professional/assessments/${data.id}/edit`}
          >
            Corrigir avaliação
          </Link>
        )}
      </div>
      <section className="rounded-lg border bg-white p-5">
        <dl className="grid gap-4 sm:grid-cols-3">
          <div>
            <dt className="text-sm text-muted-foreground">Peso (kg)</dt>
            <dd className="mt-2 text-xl font-semibold">
              {number(data.weight_kg)}
            </dd>
          </div>
          <div>
            <dt className="text-sm text-muted-foreground">
              Altura registrada (cm)
            </dt>
            <dd className="mt-2 text-xl font-semibold">
              {number(data.height_cm)}
            </dd>
          </div>
          <div>
            <dt className="text-sm text-muted-foreground">IMC de referência</dt>
            <dd className="mt-2 text-xl font-semibold">{number(data.bmi)}</dd>
          </div>
        </dl>
        <p className="mt-5 text-xs leading-5 text-muted-foreground">
          {bmiNote}
        </p>
      </section>
      <section className="rounded-lg border bg-white p-5">
        <h2 className="text-lg font-semibold">Medidas corporais</h2>
        {!data.measurements.length ? (
          <p className="mt-4 text-sm text-muted-foreground">
            Nenhuma medida informada.
          </p>
        ) : (
          <ul className="mt-4 grid gap-4 sm:grid-cols-2">
            {data.measurements.map((item) => (
              <li
                key={`${item.measurement_type}-${item.side}`}
                className="border-t pt-3"
              >
                <h3 className="text-sm font-medium">
                  {measureLabel(item.measurement_type, item.side)}
                </h3>
                <p className="mt-1 text-lg">{number(item.value_cm)} cm</p>
                {item.notes && (
                  <p className="mt-2 whitespace-pre-wrap text-sm text-muted-foreground">
                    {item.notes}
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
      {data.notes && (
        <section className="rounded-lg border bg-white p-5">
          <h2 className="font-semibold">Observações</h2>
          <p className="mt-3 whitespace-pre-wrap text-sm leading-6">
            {data.notes}
          </p>
        </section>
      )}
      <p className="text-xs leading-6 text-muted-foreground">
        Registrada em {new Date(data.created_at).toLocaleString("pt-BR")}.
        Atualizada em {new Date(data.updated_at).toLocaleString("pt-BR")}.
      </p>
    </div>
  );
}
