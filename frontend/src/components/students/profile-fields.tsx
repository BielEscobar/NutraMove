"use client";

import { goals, type Student } from "@/lib/students";

type Field = {
  name: string;
  label: string;
  type?: "number" | "date" | "tel";
  required?: boolean;
  maxLength?: number;
  min?: number;
  max?: number;
  options?: Record<string, string>;
};
export const groups: { title: string; fields: Field[] }[] = [
  {
    title: "Dados pessoais",
    fields: [
      {
        name: "birth_date",
        label: "Data de nascimento",
        type: "date",
        required: true,
      },
      {
        name: "phone",
        label: "Telefone (opcional)",
        type: "tel",
        maxLength: 40,
      },
      {
        name: "weight",
        label: "Peso (kg)",
        type: "number",
        required: true,
        min: 0.01,
      },
      {
        name: "height",
        label: "Altura (cm)",
        type: "number",
        required: true,
        min: 0.01,
      },
    ],
  },
  {
    title: "Objetivos",
    fields: [
      { name: "goal", label: "Objetivo", required: true, options: goals },
      { name: "goal_detail", label: "Descreva seu objetivo", maxLength: 500 },
      {
        name: "activity_level",
        label: "Atividade no dia a dia",
        required: true,
        options: { LOW: "Baixa", MODERATE: "Moderada", HIGH: "Alta" },
      },
      {
        name: "training_experience",
        label: "Experiência com treino",
        required: true,
        options: {
          NONE: "Sem experiência",
          BEGINNER: "Iniciante",
          INTERMEDIATE: "Intermediário",
          ADVANCED: "Avançado",
        },
      },
      {
        name: "training_frequency",
        label: "Dias de treino por semana",
        type: "number",
        required: true,
        min: 0,
        max: 7,
      },
    ],
  },
  {
    title: "Rotina",
    fields: [
      {
        name: "preferred_training_time",
        label: "Horário preferido para treinar",
        maxLength: 120,
      },
      { name: "work_routine", label: "Rotina de trabalho", maxLength: 1000 },
      {
        name: "meal_schedule",
        label: "Horários aproximados das refeições",
        maxLength: 1000,
      },
      {
        name: "approximate_water_intake",
        label: "Consumo aproximado de água (litros/dia)",
        type: "number",
        min: 0,
      },
    ],
  },
  {
    title: "Alimentação",
    fields: [
      {
        name: "food_preferences",
        label: "Preferências alimentares",
        maxLength: 1000,
      },
      {
        name: "food_restrictions",
        label: "Restrições alimentares",
        maxLength: 1000,
      },
      {
        name: "notes",
        label: "Observações relevantes (opcional)",
        maxLength: 2000,
      },
    ],
  },
];
export type ProfileDraft = Record<string, string>;
export function draftFromStudent(student: Student): ProfileDraft {
  const values: ProfileDraft = {};
  for (const group of groups)
    for (const field of group.fields) {
      const value = student[field.name as keyof Student];
      values[field.name] = value == null ? "" : String(value);
    }
  return values;
}
export function profilePayload(
  draft: ProfileDraft,
): Record<string, string | number | null> {
  const result: Record<string, string | number | null> = {};
  for (const group of groups)
    for (const field of group.fields) {
      const value = (draft[field.name] ?? "").trim();
      result[field.name] =
        value === "" ? null : field.type === "number" ? Number(value) : value;
    }
  if (draft.goal !== "OTHER") result.goal_detail = null;
  return result;
}
export function ProfileFields({
  group,
  values,
  change,
  disabled,
}: {
  group: number;
  values: ProfileDraft;
  change: (name: string, value: string) => void;
  disabled: boolean;
}) {
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  const maxDate = [
    yesterday.getFullYear(),
    String(yesterday.getMonth() + 1).padStart(2, "0"),
    String(yesterday.getDate()).padStart(2, "0"),
  ].join("-");
  return (
    <div className="grid gap-5 sm:grid-cols-2">
      {groups[group].fields.map((field) => {
        if (field.name === "goal_detail" && values.goal !== "OTHER")
          return null;
        return (
          <div
            key={field.name}
            className={
              field.maxLength && field.maxLength > 120 ? "sm:col-span-2" : ""
            }
          >
            <label
              className="mb-2 block text-sm font-medium"
              htmlFor={field.name}
            >
              {field.label}
              {field.required || field.name === "goal_detail" ? " *" : ""}
            </label>
            {field.options ? (
              <select
                id={field.name}
                className="auth-input"
                required
                disabled={disabled}
                value={values[field.name] ?? ""}
                onChange={(e) => change(field.name, e.target.value)}
              >
                <option value="">Selecione</option>
                {Object.entries(field.options).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            ) : field.maxLength && field.maxLength > 120 ? (
              <textarea
                id={field.name}
                className="auth-input min-h-24"
                maxLength={field.maxLength}
                required={field.name === "goal_detail"}
                disabled={disabled}
                value={values[field.name] ?? ""}
                onChange={(e) => change(field.name, e.target.value)}
              />
            ) : (
              <input
                id={field.name}
                className="auth-input"
                type={field.type ?? "text"}
                required={field.required}
                maxLength={field.maxLength}
                min={field.min}
                max={field.type === "date" ? maxDate : field.max}
                step={field.name === "training_frequency" ? 1 : "any"}
                disabled={disabled}
                value={values[field.name] ?? ""}
                onChange={(e) => change(field.name, e.target.value)}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
export function ProfileSummary({ values }: { values: ProfileDraft }) {
  return (
    <dl className="grid gap-4 text-sm sm:grid-cols-2">
      {groups
        .flatMap((group) => group.fields)
        .filter(
          (field) =>
            values[field.name] &&
            (field.name !== "goal_detail" || values.goal === "OTHER"),
        )
        .map((field) => (
          <div key={field.name}>
            <dt className="text-muted-foreground">{field.label}</dt>
            <dd className="mt-1 whitespace-pre-wrap break-words">
              {field.options?.[values[field.name]] ?? values[field.name]}
            </dd>
          </div>
        ))}
    </dl>
  );
}
