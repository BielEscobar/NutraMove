"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useRef, useState } from "react";
import { ApiError, apiRequest } from "@/lib/api";
import type {
  DietContent,
  DietVersion,
  Food,
  Meal,
  Substitution,
} from "@/lib/diets";

type EditSub = Substitution & { key: string };
type EditFood = Omit<Food, "substitutions"> & {
  key: string;
  substitutions: EditSub[];
};
type EditMeal = Omit<Meal, "foods"> & { key: string; foods: EditFood[] };
type Draft = Omit<DietContent, "meals"> & { meals: EditMeal[] };
function hydrate(content: DietContent): Draft {
  return {
    ...content,
    meals: content.meals.map((meal) => ({
      ...meal,
      key: crypto.randomUUID(),
      foods: meal.foods.map((food) => ({
        ...food,
        key: crypto.randomUUID(),
        substitutions: food.substitutions.map((item) => ({
          ...item,
          key: crypto.randomUUID(),
        })),
      })),
    })),
  };
}
function clean(draft: Draft): DietContent {
  return {
    name: draft.name,
    goal: draft.goal || null,
    start_date: draft.start_date || null,
    next_review_date: draft.next_review_date || null,
    notes: draft.notes || null,
    meals: draft.meals.map((meal) => ({
      name: meal.name,
      time: meal.time || null,
      foods: meal.foods.map((food) => ({
        name: food.name,
        quantity: food.quantity,
        unit: food.unit,
        notes: food.notes || null,
        substitutions: food.substitutions.map((item) => ({
          name: item.name,
          quantity: item.quantity || null,
          unit: item.unit || null,
          notes: item.notes || null,
        })),
      })),
    })),
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
}: {
  id: string;
  label: string;
  value: string | null;
  change: (value: string) => void;
  type?: string;
  required?: boolean;
  maxLength?: number;
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
            ? { min: "0.001", max: "999999999.999", step: "0.001" }
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

export function DietEditor({
  path,
  backHref,
  initial,
}: {
  path: string;
  backHref: string;
  initial?: DietVersion;
}) {
  const [draft, setDraft] = useState<Draft>(() =>
    hydrate(
      initial ?? {
        name: "",
        goal: null,
        start_date: null,
        next_review_date: null,
        notes: null,
        meals: [],
      },
    ),
  );
  const [dirty, setDirty] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [saved, setSaved] = useState<DietVersion | null>(null);
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
  function mealChange(index: number, patch: Partial<EditMeal>) {
    change({
      meals: draft.meals.map((meal, i) =>
        i === index ? { ...meal, ...patch } : meal,
      ),
    });
  }
  function foodChange(mi: number, fi: number, patch: Partial<EditFood>) {
    mealChange(mi, {
      foods: draft.meals[mi].foods.map((food, i) =>
        i === fi ? { ...food, ...patch } : food,
      ),
    });
  }
  function subChange(
    mi: number,
    fi: number,
    si: number,
    patch: Partial<EditSub>,
  ) {
    foodChange(mi, fi, {
      substitutions: draft.meals[mi].foods[fi].substitutions.map((item, i) =>
        i === si ? { ...item, ...patch } : item,
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
      const version = await apiRequest<DietVersion>(path, {
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
              ? "Revise nomes, quantidades, unidades e datas. Quantidades aceitam até três casas decimais."
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
          href={`/professional/diet-versions/${saved.id}`}
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
          : "Novo rascunho de dieta"}
      </h1>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">
        Criado manualmente. O aluno só terá acesso após a publicação. Campos com
        * são obrigatórios.
      </p>
      <form onSubmit={save} className="mt-6 space-y-6" aria-busy={busy}>
        <fieldset disabled={busy} className="space-y-6">
          <section className="grid gap-5 rounded-lg border bg-white p-5 sm:grid-cols-2">
            <Field
              id="diet-name"
              label="Nome da dieta"
              value={draft.name}
              required
              change={(name) => change({ name })}
            />
            <Field
              id="diet-goal"
              label="Objetivo (opcional)"
              value={draft.goal}
              maxLength={500}
              change={(goal) => change({ goal })}
            />
            <Field
              id="diet-start"
              label="Início"
              type="date"
              value={draft.start_date}
              change={(start_date) => change({ start_date })}
            />
            <Field
              id="diet-review"
              label="Próxima revisão"
              type="date"
              value={draft.next_review_date}
              change={(next_review_date) => change({ next_review_date })}
            />
            <Field
              id="diet-notes"
              label="Orientações para o aluno"
              type="textarea"
              value={draft.notes}
              maxLength={4000}
              change={(notes) => change({ notes })}
            />
          </section>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-xl font-semibold">Refeições</h2>
            <button
              type="button"
              className="master-secondary"
              disabled={draft.meals.length >= 30}
              onClick={() =>
                change({
                  meals: [
                    ...draft.meals,
                    {
                      key: crypto.randomUUID(),
                      name: "",
                      time: null,
                      foods: [],
                    },
                  ],
                })
              }
            >
              Adicionar refeição
            </button>
          </div>
          {draft.meals.length === 0 && (
            <p className="rounded-lg border border-dashed p-5 text-sm text-muted-foreground">
              Você pode salvar o rascunho vazio e adicionar refeições depois. A
              publicação exige ao menos uma refeição com alimentos.
            </p>
          )}
          {draft.meals.map((meal, mi) => (
            <details open key={meal.key} className="rounded-lg border bg-white">
              <summary className="min-h-14 cursor-pointer p-5 font-semibold">
                Refeição {mi + 1}
                {meal.name ? ` · ${meal.name}` : ""}
              </summary>
              <div className="space-y-5 border-t p-5">
                <Ordering
                  label={`refeição ${mi + 1}`}
                  index={mi}
                  length={draft.meals.length}
                  onMove={(delta) =>
                    change({ meals: move(draft.meals, mi, delta) })
                  }
                  onRemove={() =>
                    change({ meals: draft.meals.filter((_, i) => i !== mi) })
                  }
                />
                <div className="grid gap-5 sm:grid-cols-2">
                  <Field
                    id={`meal-${meal.key}-name`}
                    label="Nome da refeição"
                    value={meal.name}
                    required
                    change={(name) => mealChange(mi, { name })}
                  />
                  <Field
                    id={`meal-${meal.key}-time`}
                    label="Horário"
                    type="time"
                    value={meal.time}
                    change={(time) => mealChange(mi, { time })}
                  />
                </div>
                {meal.foods.map((food, fi) => (
                  <div key={food.key} className="space-y-4 border-t pt-5">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <h3 className="font-medium">Alimento {fi + 1}</h3>
                      <Ordering
                        label={`alimento ${fi + 1}`}
                        index={fi}
                        length={meal.foods.length}
                        onMove={(delta) =>
                          mealChange(mi, { foods: move(meal.foods, fi, delta) })
                        }
                        onRemove={() =>
                          mealChange(mi, {
                            foods: meal.foods.filter((_, i) => i !== fi),
                          })
                        }
                      />
                    </div>
                    <div className="grid gap-4 sm:grid-cols-2">
                      <Field
                        id={`food-${food.key}-name`}
                        label="Alimento"
                        required
                        value={food.name}
                        change={(name) => foodChange(mi, fi, { name })}
                      />
                      <Field
                        id={`food-${food.key}-quantity`}
                        label="Quantidade"
                        type="number"
                        required
                        value={food.quantity}
                        change={(quantity) => foodChange(mi, fi, { quantity })}
                      />
                      <Field
                        id={`food-${food.key}-unit`}
                        label="Unidade"
                        required
                        maxLength={40}
                        value={food.unit}
                        change={(unit) => foodChange(mi, fi, { unit })}
                      />
                      <Field
                        id={`food-${food.key}-notes`}
                        label="Observações do alimento"
                        maxLength={1000}
                        value={food.notes}
                        change={(notes) => foodChange(mi, fi, { notes })}
                      />
                    </div>
                    <details
                      className="rounded-md bg-secondary/50 p-3"
                      open={food.substitutions.length > 0}
                    >
                      <summary className="min-h-11 cursor-pointer py-2 text-sm font-medium">
                        Substituições ({food.substitutions.length})
                      </summary>
                      <p className="mb-3 text-xs leading-5 text-muted-foreground">
                        Quantidades e unidades são definidas por você. Não há
                        cálculo automático de equivalência.
                      </p>
                      {food.substitutions.map((item, si) => (
                        <div
                          key={item.key}
                          className="mb-4 space-y-3 border-t pt-4"
                        >
                          <Ordering
                            label={`substituição ${si + 1}`}
                            index={si}
                            length={food.substitutions.length}
                            onMove={(delta) =>
                              foodChange(mi, fi, {
                                substitutions: move(
                                  food.substitutions,
                                  si,
                                  delta,
                                ),
                              })
                            }
                            onRemove={() =>
                              foodChange(mi, fi, {
                                substitutions: food.substitutions.filter(
                                  (_, i) => i !== si,
                                ),
                              })
                            }
                          />
                          <div className="grid gap-4 sm:grid-cols-2">
                            <Field
                              id={`sub-${item.key}-name`}
                              label="Substituição"
                              required
                              value={item.name}
                              change={(name) => subChange(mi, fi, si, { name })}
                            />
                            <Field
                              id={`sub-${item.key}-quantity`}
                              label="Quantidade da substituição"
                              type="number"
                              required={!!item.unit}
                              value={item.quantity}
                              change={(quantity) =>
                                subChange(mi, fi, si, { quantity })
                              }
                            />
                            <Field
                              id={`sub-${item.key}-unit`}
                              label="Unidade da substituição"
                              required={!!item.quantity}
                              maxLength={40}
                              value={item.unit}
                              change={(unit) => subChange(mi, fi, si, { unit })}
                            />
                            <Field
                              id={`sub-${item.key}-notes`}
                              label="Observações da substituição"
                              value={item.notes}
                              maxLength={1000}
                              change={(notes) =>
                                subChange(mi, fi, si, { notes })
                              }
                            />
                          </div>
                        </div>
                      ))}
                      <button
                        type="button"
                        className="master-secondary"
                        disabled={food.substitutions.length >= 20}
                        onClick={() =>
                          foodChange(mi, fi, {
                            substitutions: [
                              ...food.substitutions,
                              {
                                key: crypto.randomUUID(),
                                name: "",
                                quantity: null,
                                unit: null,
                                notes: null,
                              },
                            ],
                          })
                        }
                      >
                        Adicionar substituição
                      </button>
                    </details>
                  </div>
                ))}
                <button
                  type="button"
                  className="master-secondary"
                  disabled={meal.foods.length >= 50}
                  onClick={() =>
                    mealChange(mi, {
                      foods: [
                        ...meal.foods,
                        {
                          key: crypto.randomUUID(),
                          name: "",
                          quantity: "",
                          unit: "",
                          notes: null,
                          substitutions: [],
                        },
                      ],
                    })
                  }
                >
                  Adicionar alimento
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
