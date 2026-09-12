"use client";
import Link from "next/link";
import { useState } from "react";
import { ErrorState, LoadingState } from "@/components/master/resource-state";
import {
  type Area,
  type AssessmentList,
  bmiNote,
  displayDate,
  type Evolution,
  measureLabel,
  number,
  type Period,
  periods,
  studentPath,
} from "@/lib/evolution";
import { useApiResource } from "@/lib/use-api-resource";
import { EvolutionChart } from "./evolution-chart";

export function EvolutionPage({
  area,
  studentId,
}: {
  area: Area;
  studentId?: string;
}) {
  const [period, setPeriod] = useState<Period>("90d"),
    [series, setSeries] = useState("weight"),
    [page, setPage] = useState(1);
  const base = studentPath(area, studentId);
  const resource = useApiResource<Evolution>(
    `${base}/evolution?period=${period}`,
  );
  const history = useApiResource<AssessmentList>(
    `${base}/assessments?page=${page}`,
  );
  const chosen = resource.data?.measurements.find(
    (item) => `${item.measurement_type}-${item.side}` === series,
  );
  const current = resource.data?.current;
  return (
    <div className="space-y-6 [overflow-wrap:anywhere]">
      {area !== "student" && (
        <Link href={base} className="text-sm text-primary underline">
          Voltar ao aluno
        </Link>
      )}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold">
          {area === "student" ? "Minha evolução" : "Evolução física"}
        </h1>
        {area === "professional" && (
          <Link
            className="master-primary min-h-11"
            href={`${base}/assessments/new`}
          >
            Nova avaliação
          </Link>
        )}
      </div>
      {resource.loading ? (
        <LoadingState />
      ) : resource.error ? (
        <ErrorState message={resource.error} retry={resource.reload} />
      ) : !current ? (
        <section className="rounded-lg border border-dashed bg-white p-6">
          <h2 className="font-semibold">
            Ainda não há avaliações registradas.
          </h2>
          <p className="mt-3 text-sm text-muted-foreground">
            {area === "professional"
              ? "Registre a primeira avaliação para começar a acompanhar a evolução deste aluno."
              : "Seu profissional ainda não registrou avaliações."}
          </p>
        </section>
      ) : (
        <section
          className="grid gap-4 sm:grid-cols-3"
          aria-label="Resumo da evolução"
        >
          <div className="rounded-lg border bg-white p-5">
            <h2 className="text-sm text-muted-foreground">
              Peso atual registrado
            </h2>
            <p className="mt-2 text-2xl font-semibold">
              {number(current.weight_kg)}
              {current.weight_kg !== null ? " kg" : ""}
            </p>
            {current.weight_date && (
              <p className="mt-2 text-xs text-muted-foreground">
                Avaliação de {displayDate(current.weight_date)}
              </p>
            )}
          </div>
          <div className="rounded-lg border bg-white p-5">
            <h2 className="text-sm text-muted-foreground">IMC de referência</h2>
            <p className="mt-2 text-2xl font-semibold">{number(current.bmi)}</p>
            <p className="mt-2 text-xs leading-5 text-muted-foreground">
              {bmiNote}
            </p>
          </div>
          <div className="rounded-lg border bg-white p-5">
            <h2 className="text-sm text-muted-foreground">Última avaliação</h2>
            <p className="mt-2 text-xl font-semibold">
              {displayDate(current.latest_assessment_date)}
            </p>
            <p className="mt-2 text-xs text-muted-foreground">
              Resumo considera todo o histórico.
            </p>
          </div>
        </section>
      )}
      <section className="min-w-0 rounded-lg border bg-white p-5">
        <h2 className="text-lg font-semibold">Histórico em gráfico</h2>
        <div className="my-5 grid gap-4 sm:grid-cols-2">
          <label className="text-sm">
            Período
            <select
              id="evolution-period"
              className="auth-input mt-2"
              value={period}
              onChange={(e) => setPeriod(e.target.value as Period)}
            >
              {Object.entries(periods).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            Série
            <select
              className="auth-input mt-2"
              value={chosen ? series : "weight"}
              onChange={(e) => setSeries(e.target.value)}
            >
              <option value="weight">Peso</option>
              {resource.data?.measurements.map((item) => (
                <option
                  key={`${item.measurement_type}-${item.side}`}
                  value={`${item.measurement_type}-${item.side}`}
                >
                  {measureLabel(item.measurement_type, item.side)}
                </option>
              ))}
            </select>
          </label>
        </div>
        {!resource.loading && !resource.error && resource.data && (
          <EvolutionChart
            points={chosen?.points ?? resource.data.weight_history}
            label={
              chosen
                ? measureLabel(chosen.measurement_type, chosen.side)
                : "Peso"
            }
            unit={chosen ? "cm" : "kg"}
          />
        )}
      </section>
      <section>
        <h2 className="mb-4 text-xl font-semibold">
          Avaliações — histórico completo
        </h2>
        {history.loading ? (
          <LoadingState />
        ) : history.error ? (
          <ErrorState message={history.error} retry={history.reload} />
        ) : (
          <>
            <ul className="space-y-3">
              {history.data?.items.map((item) => (
                <li key={item.id}>
                  <Link
                    href={`/${area}/assessments/${item.id}`}
                    className="block rounded-lg border bg-white p-5 hover:border-primary"
                  >
                    <h3 className="font-semibold">
                      Avaliação de {displayDate(item.assessment_date)}
                    </h3>
                    <p className="mt-2 text-sm">
                      Peso: {number(item.weight_kg)}
                      {item.weight_kg !== null ? " kg" : ""} · IMC:{" "}
                      {number(item.bmi)}
                    </p>
                    <span className="mt-3 block text-sm text-primary">
                      Ver medidas e observações
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
            {history.data && history.data.total > 20 && (
              <div className="mt-4 flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  className="master-secondary"
                  disabled={page === 1}
                  onClick={() => setPage(page - 1)}
                >
                  Anterior
                </button>
                <span className="text-sm">Página {page}</span>
                <button
                  type="button"
                  className="master-secondary"
                  disabled={page * 20 >= history.data.total}
                  onClick={() => setPage(page + 1)}
                >
                  Próxima
                </button>
              </div>
            )}
          </>
        )}
      </section>
    </div>
  );
}
