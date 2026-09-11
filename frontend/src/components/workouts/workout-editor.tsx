"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useRef, useState } from "react";
import { ApiError, apiRequest } from "@/lib/api";
import type {
  WorkoutContent,
  WorkoutDay,
  WorkoutExercise,
  WorkoutVersion,
} from "@/lib/workouts";

type EditExercise = WorkoutExercise & { key: string };
type EditDay = Omit<WorkoutDay, "exercises"> & {
  key: string;
  exercises: EditExercise[];
};
type Draft = Omit<WorkoutContent, "days"> & { days: EditDay[] };
function hydrate(content: WorkoutContent): Draft {
  return {
    ...content,
    days: content.days.map((day) => ({
      ...day,
      key: crypto.randomUUID(),
      exercises: day.exercises.map((exercise) => ({
        ...exercise,
        key: crypto.randomUUID(),
      })),
    })),
  };
}
function clean(draft: Draft): WorkoutContent {
  return {
    name: draft.name,
    goal: draft.goal || null,
    frequency_per_week: draft.frequency_per_week,
    start_date: draft.start_date || null,
    next_review_date: draft.next_review_date || null,
    notes: draft.notes || null,
    days: draft.days.map((day) => ({
      name: day.name,
      description: day.description || null,
      exercises: day.exercises.map(({ key: _key, ...exercise }) => exercise),
    })),
  };
}
function emptyExercise(): EditExercise {
  return {
    key: crypto.randomUUID(),
    name: "",
    muscle_group: null,
    description: null,
    instructions: null,
    sets: null,
    repetitions: null,
    load: null,
    duration: null,
    rest_seconds: null,
    notes: null,
  };
}
function move<T>(items: T[], index: number, delta: number): T[] {
  const next = [...items];
  const target = index + delta;
  if (target >= 0 && target < next.length)
    [next[index], next[target]] = [next[target], next[index]];
  return next;
}

function Field({
  id,
  label,
  value,
  change,
  type = "text",
  required = false,
  maxLength = 160,
  min = 1,
  max = 100,
}: {
  id: string;
  label: string;
  value: string | null;
  change: (value: string) => void;
  type?: string;
  required?: boolean;
  maxLength?: number;
  min?: number;
  max?: number;
}) {
  return (
    <div className={type === "textarea" ? "sm:col-span-2" : ""}>
      <label htmlFor={id} className="mb-2 block text-sm font-medium">
        {label}
        {required ? " *" : ""}
      </label>
      {type === "textarea" ? (
        <textarea
          id={id}
          className="auth-input min-h-24"
          maxLength={maxLength}
          value={value ?? ""}
          onChange={(e) => change(e.target.value)}
        />
      ) : (
        <input
          id={id}
          className="auth-input"
          type={type}
          required={required}
          maxLength={maxLength}
          value={value ?? ""}
          onChange={(e) => change(e.target.value)}
          {...(type === "number"
            ? { min, max, step: 1 }
            : type === "time"
              ? { step: 1 }
              : {})}
        />
      )}
    </div>
  );
}
function Ordering({
  label,
  index,
  length,
  onMove,
  onRemove,
}: {
  label: string;
  index: number;
  length: number;
  onMove: (delta: number) => void;
  onRemove: () => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      <button
        className="master-secondary text-xs"
        type="button"
        aria-label={`Mover ${label} para cima`}
        disabled={index === 0}
        onClick={() => onMove(-1)}
      >
        Subir
      </button>
      <button
        className="master-secondary text-xs"
        type="button"
        aria-label={`Mover ${label} para baixo`}
        disabled={index === length - 1}
        onClick={() => onMove(1)}
      >
        Descer
      </button>
      <button
        type="button"
        className="master-secondary text-xs text-destructive"
        aria-label={`Remover ${label}`}
        onClick={() => {
          if (window.confirm("Remover este item do rascunho?")) onRemove();
        }}
      >
        Remover
      </button>
    </div>
  );
}

export function WorkoutEditor({
  path,
  backHref,
  initial,
}: {
  path: string;
  backHref: string;
  initial?: WorkoutVersion;
}) {
  const [draft, setDraft] = useState<Draft>(() =>
    hydrate(
      initial ?? {
        name: "",
        goal: null,
        start_date: null,
        next_review_date: null,
        notes: null,
        days: [],
        frequency_per_week: null,
      },
    ),
  );
  const [dirty, setDirty] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [saved, setSaved] = useState<WorkoutVersion | null>(null);
  const guard = useRef(false),
    router = useRouter();
  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
  function change(patch: Partial<Draft>) {
    setDraft((previous) => ({ ...previous, ...patch }));
    setDirty(true);
    setSaved(null);
  }
  function dayChange(index: number, patch: Partial<EditDay>) {
    change({
      days: draft.days.map((day, i) =>
        i === index ? { ...day, ...patch } : day,
      ),
    });
  }
  function exerciseChange(
    di: number,
    ei: number,
    patch: Partial<EditExercise>,
  ) {
    dayChange(di, {
      exercises: draft.days[di].exercises.map((exercise, i) =>
        i === ei ? { ...exercise, ...patch } : exercise,
      ),
    });
  }
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (guard.current) return;
    if (
      draft.start_date &&
      draft.next_review_date &&
      draft.next_review_date < draft.start_date
    ) {
      setError("A próxima revisão não pode ser anterior ao início.");
      return;
    }
    guard.current = true;
    setBusy(true);
    setError("");
    try {
      const version = await apiRequest<WorkoutVersion>(path, {
        method: initial ? "PATCH" : "POST",
        body: JSON.stringify({
          ...clean(draft),
          ...(initial ? { expected_revision: initial.edit_revision } : {}),
        }),
      });
      setDirty(false);
      setSaved(version);
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401)
        router.replace("/login");
      else
        setError(
          cause instanceof ApiError && cause.status === 409
            ? "A versão mudou ou não pode mais ser editada. Reabra o rascunho para carregar os dados atuais."
            : cause instanceof ApiError && cause.status === 422
              ? "Revise nomes, datas, séries, frequência e descanso. Séries e descanso exigem números inteiros."
              : cause instanceof Error
                ? cause.message
                : "Não foi possível salvar.",
        );
    } finally {
      guard.current = false;
      setBusy(false);
    }
  }
  if (saved)
    return (
      <section className="rounded-lg border bg-white p-6">
        <h1 className="text-2xl font-semibold">Rascunho salvo</h1>
        <p role="status" className="mt-3 text-sm text-muted-foreground">
          Versão {saved.version_number} salva. Revise o conteúdo antes de
          aprovar e publicar.
        </p>
        <Link
          href={`/professional/workout-versions/${saved.id}`}
          className="master-primary mt-6"
        >
          Revisar versão
        </Link>
      </section>
    );
  return (
    <div>
      <button
        type="button"
        className="text-sm text-primary underline"
        onClick={() => {
          if (!dirty || window.confirm("Sair sem salvar as alterações?"))
            router.push(backHref);
        }}
      >
        Voltar
      </button>
      <h1 className="mt-5 text-2xl font-semibold">
        {initial
          ? `Editar versão ${initial.version_number}`
          : "Novo rascunho de treino"}
      </h1>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">
        Criado manualmente. O aluno só terá acesso após a publicação. Campos com
        * são obrigatórios.
      </p>
      <form onSubmit={save} className="mt-6 space-y-6" aria-busy={busy}>
        <fieldset disabled={busy} className="space-y-6">
          <section className="grid gap-5 rounded-lg border bg-white p-5 sm:grid-cols-2">
            <Field
              id="workout-name"
              label="Nome do treino"
              value={draft.name}
              required
              change={(name) => change({ name })}
            />
            <Field
              id="workout-goal"
              label="Objetivo (opcional)"
              value={draft.goal}
              maxLength={500}
              change={(goal) => change({ goal })}
            />
            <Field
              id="workout-frequency"
              label="Frequência semanal (dias)"
              type="number"
              max={7}
              value={draft.frequency_per_week?.toString() ?? null}
              change={(value) =>
                change({
                  frequency_per_week: value === "" ? null : Number(value),
                })
              }
            />
            <Field
              id="workout-start"
              label="Início"
              type="date"
              value={draft.start_date}
              change={(start_date) => change({ start_date })}
            />
            <Field
              id="workout-review"
              label="Próxima revisão"
              type="date"
              value={draft.next_review_date}
              change={(next_review_date) => change({ next_review_date })}
            />
            <Field
              id="workout-notes"
              label="Orientações para o aluno"
              type="textarea"
              value={draft.notes}
              maxLength={4000}
              change={(notes) => change({ notes })}
            />
          </section>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-xl font-semibold">Divisões de treino</h2>
            <button
              type="button"
              className="master-secondary"
              disabled={draft.days.length >= 30}
              onClick={() =>
                change({
                  days: [
                    ...draft.days,
                    {
                      key: crypto.randomUUID(),
                      name: "",
                      description: null,
                      exercises: [],
                    },
                  ],
                })
              }
            >
              Adicionar divisão
            </button>
          </div>
          {draft.days.length === 0 && (
            <p className="rounded-lg border border-dashed p-5 text-sm text-muted-foreground">
              Você pode salvar o rascunho vazio. Para publicar, inclua ao menos
              uma divisão com exercícios.
            </p>
          )}
          {draft.days.map((day, di) => (
            <details
              open
              key={day.key}
              className="min-w-0 rounded-lg border bg-white"
            >
              <summary className="min-h-14 cursor-pointer p-5 font-semibold [overflow-wrap:anywhere]">
                Divisão {di + 1} {day.name ? ` · ${day.name}` : ""}
              </summary>
              <div className="space-y-5 border-t p-5">
                <Ordering
                  label={`divisão ${di + 1}`}
                  index={di}
                  length={draft.days.length}
                  onMove={(delta) =>
                    change({ days: move(draft.days, di, delta) })
                  }
                  onRemove={() =>
                    change({ days: draft.days.filter((_, i) => i !== di) })
                  }
                />
                <div className="grid gap-5 sm:grid-cols-2">
                  <Field
                    id={`day-${day.key}-name`}
                    label="Nome da divisão"
                    required
                    value={day.name}
                    change={(name) => dayChange(di, { name })}
                  />
                  <Field
                    id={`day-${day.key}-description`}
                    label="Descrição da divisão"
                    value={day.description}
                    maxLength={2000}
                    change={(description) => dayChange(di, { description })}
                  />
                </div>
                {day.exercises.map((exercise, ei) => (
                  <div key={exercise.key} className="space-y-4 border-t pt-5">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <h3 className="font-medium">Exercício {ei + 1}</h3>
                      <Ordering
                        label={`exercício ${ei + 1} da divisão ${di + 1}`}
                        index={ei}
                        length={day.exercises.length}
                        onMove={(delta) =>
                          dayChange(di, {
                            exercises: move(day.exercises, ei, delta),
                          })
                        }
                        onRemove={() =>
                          dayChange(di, {
                            exercises: day.exercises.filter((_, i) => i !== ei),
                          })
                        }
                      />
                    </div>
                    <div className="grid gap-5 sm:grid-cols-2">
                      <Field
                        id={`exercise-${exercise.key}-name`}
                        label="Nome do exercício"
                        required
                        value={exercise.name}
                        change={(name) => exerciseChange(di, ei, { name })}
                      />
                      <Field
                        id={`exercise-${exercise.key}-muscle`}
                        label="Grupo muscular"
                        value={exercise.muscle_group}
                        change={(muscle_group) =>
                          exerciseChange(di, ei, { muscle_group })
                        }
                      />
                      <Field
                        id={`exercise-${exercise.key}-sets`}
                        label="Séries"
                        type="number"
                        value={exercise.sets?.toString() ?? null}
                        change={(value) =>
                          exerciseChange(di, ei, {
                            sets: value === "" ? null : Number(value),
                          })
                        }
                      />
                      <Field
                        id={`exercise-${exercise.key}-repetitions`}
                        label="Repetições (ex.: 8-12, falha, 12 por lado)"
                        value={exercise.repetitions}
                        change={(repetitions) =>
                          exerciseChange(di, ei, { repetitions })
                        }
                      />
                      <Field
                        id={`exercise-${exercise.key}-load`}
                        label="Carga (ex.: 20 kg, peso corporal, RPE 8)"
                        value={exercise.load}
                        change={(load) => exerciseChange(di, ei, { load })}
                      />
                      <Field
                        id={`exercise-${exercise.key}-duration`}
                        label="Duração / tempo (ex.: 30 segundos)"
                        value={exercise.duration}
                        change={(duration) =>
                          exerciseChange(di, ei, { duration })
                        }
                      />
                      <Field
                        id={`exercise-${exercise.key}-rest`}
                        label="Descanso em segundos"
                        type="number"
                        min={0}
                        max={86400}
                        value={exercise.rest_seconds?.toString() ?? null}
                        change={(value) =>
                          exerciseChange(di, ei, {
                            rest_seconds: value === "" ? null : Number(value),
                          })
                        }
                      />
                      <Field
                        id={`exercise-${exercise.key}-description`}
                        label="Descrição do exercício"
                        maxLength={2000}
                        value={exercise.description}
                        change={(description) =>
                          exerciseChange(di, ei, { description })
                        }
                      />
                      <Field
                        id={`exercise-${exercise.key}-instructions`}
                        label="Instruções"
                        type="textarea"
                        maxLength={2000}
                        value={exercise.instructions}
                        change={(instructions) =>
                          exerciseChange(di, ei, { instructions })
                        }
                      />
                      <Field
                        id={`exercise-${exercise.key}-notes`}
                        label="Observações"
                        type="textarea"
                        maxLength={2000}
                        value={exercise.notes}
                        change={(notes) => exerciseChange(di, ei, { notes })}
                      />
                    </div>
                  </div>
                ))}
                <button
                  type="button"
                  className="master-secondary"
                  disabled={day.exercises.length >= 100}
                  onClick={() =>
                    dayChange(di, {
                      exercises: [...day.exercises, emptyExercise()],
                    })
                  }
                >
                  Adicionar exercício
                </button>
              </div>
            </details>
          ))}
        </fieldset>
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        <div className="sticky bottom-0 flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-white p-4 shadow-sm">
          <p className="text-sm text-muted-foreground">
            {dirty ? "Alterações não salvas" : "Rascunho"}
          </p>
          <button type="submit" disabled={busy} className="master-primary">
            {busy ? "Salvando…" : "Salvar rascunho"}
          </button>
        </div>
      </form>
    </div>
  );
}
