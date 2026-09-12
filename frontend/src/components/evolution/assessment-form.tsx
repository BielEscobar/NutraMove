"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useRef, useState } from "react";
import { ApiError, apiRequest } from "@/lib/api";
import {
  type AssessmentContent,
  displayDate,
  type MeasurementType,
  measurementTypes,
  type Side,
  type StaffAssessment,
} from "@/lib/evolution";

type EditMeasurement = {
  key: string;
  measurement_type: MeasurementType;
  side: Side;
  value: string;
  notes: string;
};
function today() {
  const value = new Date();
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
}
export function AssessmentForm({
  studentId,
  initial,
}: {
  studentId: string;
  initial?: StaffAssessment;
}) {
  const router = useRouter(),
    guard = useRef(false);
  const [day, setDay] = useState(initial?.assessment_date ?? today()),
    [weight, setWeight] = useState(initial?.weight_kg?.toString() ?? ""),
    [height, setHeight] = useState(initial?.height_cm?.toString() ?? ""),
    [notes, setNotes] = useState(initial?.notes ?? "");
  const [measurements, setMeasurements] = useState<EditMeasurement[]>(
    () =>
      initial?.measurements.map((item) => ({
        key: crypto.randomUUID(),
        measurement_type: item.measurement_type,
        side: item.side,
        value: item.value_cm.toString(),
        notes: item.notes ?? "",
      })) ?? [],
  );
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [dirty, setDirty] = useState(false);
  const back = `/professional/students/${studentId}/evolution`;
  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
  function update(index: number, patch: Partial<EditMeasurement>) {
    setDirty(true);
    setMeasurements((items) =>
      items.map((item, i) => (i === index ? { ...item, ...patch } : item)),
    );
  }
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (guard.current) return;
    const keys = measurements.map((m) => `${m.measurement_type}-${m.side}`);
    if (new Set(keys).size !== keys.length) {
      setError("Não repita uma medida com a mesma lateralidade.");
      return;
    }
    if (!weight && !height && !notes.trim() && !measurements.length) {
      setError("Informe peso, altura, medida ou observação.");
      return;
    }
    guard.current = true;
    setBusy(true);
    setError("");
    const content: AssessmentContent = {
      weight_kg: weight ? Number(weight) : null,
      height_cm: height ? Number(height) : null,
      notes: notes.trim() || null,
      measurements: measurements.map((m) => ({
        measurement_type: m.measurement_type,
        side: m.side,
        value_cm: Number(m.value),
        notes: m.notes.trim() || null,
      })),
    };
    try {
      const result = await apiRequest<StaffAssessment>(
        initial
          ? `/professional/assessments/${initial.id}`
          : `/professional/students/${studentId}/assessments`,
        {
          method: initial ? "PATCH" : "POST",
          body: JSON.stringify({
            ...content,
            ...(initial
              ? { expected_revision: initial.edit_revision }
              : { assessment_date: day }),
          }),
        },
      );
      setDirty(false);
      router.push(`/professional/assessments/${result.id}?saved=1`);
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401)
        router.replace("/login");
      else
        setError(
          cause instanceof ApiError && cause.status === 409
            ? "A avaliação mudou. Reabra a página para corrigir os dados atuais."
            : cause instanceof ApiError && cause.status === 422
              ? "Revise valores, data e lateralidade. Um peso já registrado pode ser corrigido, mas não removido."
              : cause instanceof Error
                ? cause.message
                : "Não foi possível salvar.",
        );
      guard.current = false;
      setBusy(false);
    }
  }
  return (
    <div className="[overflow-wrap:anywhere]">
      <Link
        href={back}
        className="text-sm text-primary underline"
        onClick={(event) => {
          if (dirty && !window.confirm("Sair sem salvar as alterações?"))
            event.preventDefault();
        }}
      >
        Voltar à evolução
      </Link>
      <h1 className="mt-5 text-2xl font-semibold">
        {initial ? "Corrigir avaliação" : "Nova avaliação física"}
      </h1>
      <p className="mt-3 text-sm leading-6 text-muted-foreground">
        {initial
          ? `Data preservada: ${displayDate(day)}. A correção registra autor e atualização.`
          : "Preencha apenas os dados coletados. A altura informada será preservada nesta avaliação."}
      </p>
      <form
        onSubmit={save}
        onChange={() => setDirty(true)}
        className="mt-6 space-y-6"
        aria-busy={busy}
      >
        <fieldset disabled={busy} className="space-y-6">
          <section className="rounded-lg border bg-white p-5">
            <h2 className="mb-5 text-lg font-semibold">Dados principais</h2>
            <div className="grid gap-5 sm:grid-cols-3">
              <label className="text-sm font-medium">
                Data da avaliação
                <input
                  id="assessment-date"
                  className="auth-input mt-2"
                  type="date"
                  required
                  max={today()}
                  disabled={!!initial}
                  value={day}
                  onChange={(e) => setDay(e.target.value)}
                />
              </label>
              <label className="text-sm font-medium">
                Peso (kg)
                <input
                  id="assessment-weight"
                  className="auth-input mt-2"
                  type="number"
                  min="0.1"
                  max="10000"
                  step="any"
                  required={initial?.weight_kg !== null && !!initial}
                  value={weight}
                  onChange={(e) => setWeight(e.target.value)}
                />
              </label>
              <label className="text-sm font-medium">
                Altura (cm)
                <input
                  id="assessment-height"
                  className="auth-input mt-2"
                  type="number"
                  min="0.1"
                  max="10000"
                  step="any"
                  value={height}
                  onChange={(e) => setHeight(e.target.value)}
                />
              </label>
            </div>
          </section>
          <section className="rounded-lg border bg-white p-5">
            <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-lg font-semibold">
                Medidas corporais (opcionais)
              </h2>
              <button
                type="button"
                className="master-secondary min-h-11"
                disabled={measurements.length >= 13}
                onClick={() => {
                  setDirty(true);
                  setMeasurements((items) => [
                    ...items,
                    {
                      key: crypto.randomUUID(),
                      measurement_type: "WAIST",
                      side: null,
                      value: "",
                      notes: "",
                    },
                  ]);
                }}
              >
                Adicionar medida
              </button>
            </div>
            <div className="space-y-5">
              {measurements.map((item, index) => (
                <fieldset key={item.key} className="min-w-0 border-t pt-5">
                  <legend className="text-sm font-medium">
                    Medida {index + 1}
                  </legend>
                  <div className="grid gap-4 sm:grid-cols-3">
                    <label className="text-sm">
                      Tipo
                      <select
                        className="auth-input mt-2"
                        value={item.measurement_type}
                        onChange={(e) =>
                          update(index, {
                            measurement_type: e.target.value as MeasurementType,
                            side: null,
                          })
                        }
                      >
                        {Object.entries(measurementTypes).map(
                          ([value, label]) => (
                            <option key={value} value={value}>
                              {label}
                            </option>
                          ),
                        )}
                      </select>
                    </label>
                    <label className="text-sm">
                      Lateralidade
                      <select
                        className="auth-input mt-2"
                        disabled={
                          !["ARM", "THIGH", "CALF"].includes(
                            item.measurement_type,
                          )
                        }
                        value={item.side ?? ""}
                        onChange={(e) =>
                          update(index, {
                            side: e.target.value
                              ? (e.target.value as Side)
                              : null,
                          })
                        }
                      >
                        <option value="">Não especificada</option>
                        <option value="LEFT">Esquerda</option>
                        <option value="RIGHT">Direita</option>
                      </select>
                    </label>
                    <label className="text-sm">
                      Valor (cm)
                      <input
                        className="auth-input mt-2"
                        id={`measurement-${item.key}-value`}
                        required
                        type="number"
                        min="0.1"
                        max="10000"
                        step="any"
                        value={item.value}
                        onChange={(e) =>
                          update(index, { value: e.target.value })
                        }
                      />
                    </label>
                  </div>
                  <label className="mt-4 block text-sm">
                    Observação da medida
                    <input
                      className="auth-input mt-2"
                      maxLength={1000}
                      value={item.notes}
                      onChange={(e) => update(index, { notes: e.target.value })}
                    />
                  </label>
                  <button
                    className="master-secondary mt-4 min-h-11 text-destructive"
                    type="button"
                    onClick={() => {
                      if (
                        window.confirm("Remover esta medida do formulário?")
                      ) {
                        setDirty(true);
                        setMeasurements((items) =>
                          items.filter((_, i) => i !== index),
                        );
                      }
                    }}
                  >
                    Remover medida
                  </button>
                </fieldset>
              ))}
            </div>
          </section>
          <label className="block rounded-lg border bg-white p-5 text-sm font-medium">
            Observações para o aluno
            <textarea
              id="assessment-notes"
              className="auth-input mt-3 min-h-28"
              maxLength={4000}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </label>
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          <button type="submit" className="master-primary min-h-11">
            {busy
              ? "Salvando…"
              : initial
                ? "Salvar correção"
                : "Salvar avaliação"}
          </button>
        </fieldset>
      </form>
    </div>
  );
}
