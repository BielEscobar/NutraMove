"use client";
import { goals, type Student } from "@/lib/students";

type Field = {
  name: string;
  label: string;
  type?: "number" | "date" | "tel" | "time";
  required?: boolean;
  maxLength?: number;
  min?: number;
  max?: number;
  options?: Record<string, string>;
  boolean?: boolean;
};
const experience = {
  NONE: "Sem experiência",
  BEGINNER: "Iniciante",
  INTERMEDIATE: "Intermediário",
  ADVANCED: "Avançado",
};
export const groups: { title: string; fields: Field[] }[] = [
  {
    title: "Objetivo e dados corporais",
    fields: [
      {
        name: "birth_date",
        label: "Data de nascimento",
        type: "date",
        required: true,
      },
      {
        name: "sex",
        label: "Sexo",
        options: {
          FEMALE: "Feminino",
          MALE: "Masculino",
          OTHER: "Outro",
          NOT_INFORMED: "Prefiro não informar",
        },
      },
      {
        name: "phone",
        label: "Telefone (opcional)",
        type: "tel",
        maxLength: 40,
      },
      {
        name: "weight",
        label: "Peso atual (kg)",
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
      {
        name: "desired_weight",
        label: "Peso/meta desejada (kg)",
        type: "number",
        min: 0.01,
      },
      {
        name: "goal",
        label: "Objetivo principal",
        required: true,
        options: goals,
      },
      { name: "goal_detail", label: "Objetivo detalhado", maxLength: 500 },
      {
        name: "activity_level",
        label: "Atividade diária",
        required: true,
        options: { LOW: "Baixa", MODERATE: "Moderada", HIGH: "Alta" },
      },
    ],
  },
  {
    title: "Rotina e treino",
    fields: [
      { name: "wake_time", label: "Horário em que acorda", type: "time" },
      { name: "sleep_time", label: "Horário em que dorme", type: "time" },
      { name: "work_routine", label: "Rotina de trabalho", maxLength: 1000 },
      {
        name: "trains_currently",
        label: "Treina atualmente?",
        options: { true: "Sim", false: "Não" },
        boolean: true,
      },
      {
        name: "training_experience",
        label: "Nível de treino",
        required: true,
        options: experience,
      },
      {
        name: "training_history",
        label: "Há quanto tempo treina / histórico",
        maxLength: 1000,
      },
      {
        name: "training_location",
        label: "Local de treino",
        options: {
          GYM: "Academia",
          HOME: "Casa",
          CONDOMINIUM: "Condomínio",
          OTHER: "Outro",
        },
      },
      {
        name: "available_equipment",
        label: "Equipamentos disponíveis",
        maxLength: 1000,
      },
      {
        name: "available_training_days",
        label: "Dias disponíveis",
        maxLength: 500,
      },
      {
        name: "training_duration_minutes",
        label: "Minutos disponíveis por treino",
        type: "number",
        min: 10,
        max: 360,
      },
      {
        name: "training_frequency",
        label: "Frequência desejada por semana",
        type: "number",
        required: true,
        min: 0,
        max: 7,
      },
      {
        name: "preferred_training_time",
        label: "Horários preferenciais",
        maxLength: 120,
      },
    ],
  },
  {
    title: "Alimentação",
    fields: [
      {
        name: "meal_count",
        label: "Refeições por dia",
        type: "number",
        min: 1,
        max: 12,
      },
      {
        name: "meal_schedule",
        label: "Horários disponíveis para refeições",
        maxLength: 1000,
      },
      {
        name: "cooking_skill",
        label: "Habilidade na cozinha",
        options: { EASY: "Fácil", MODERATE: "Moderada", ADVANCED: "Avançada" },
      },
      {
        name: "food_preferences",
        label: "Alimentos preferidos",
        maxLength: 1000,
      },
      {
        name: "disliked_foods",
        label: "Alimentos de que não gosta",
        maxLength: 1000,
      },
      {
        name: "food_restrictions",
        label: "Restrições alimentares (informe nenhuma, se aplicável)",
        maxLength: 1000,
      },
      {
        name: "food_allergies",
        label: "Alergias alimentares (informe nenhuma, se aplicável)",
        maxLength: 1000,
      },
      {
        name: "weekly_food_budget",
        label: "Orçamento semanal aproximado (R$)",
        type: "number",
        min: 0,
      },
      { name: "food_notes", label: "Observações alimentares", maxLength: 2000 },
      {
        name: "approximate_water_intake",
        label: "Água aproximada (litros/dia)",
        type: "number",
        min: 0,
      },
    ],
  },
  {
    title: "Saúde e limitações",
    fields: [
      {
        name: "has_injury",
        label: "Possui lesão?",
        options: { true: "Sim", false: "Não" },
        boolean: true,
      },
      {
        name: "injury_description",
        label: "Descrição da lesão",
        maxLength: 2000,
      },
      {
        name: "physical_limitations",
        label: "Limitações físicas",
        maxLength: 2000,
      },
      {
        name: "medical_restrictions",
        label: "Restrições médicas relevantes",
        maxLength: 2000,
      },
      { name: "notes", label: "Observações adicionais", maxLength: 2000 },
    ],
  },
];
export type ProfileDraft = Record<string, string>;
export function draftFromStudent(student: Student) {
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
): Record<string, string | number | boolean | null> {
  const result: Record<string, string | number | boolean | null> = {};
  for (const group of groups)
    for (const field of group.fields) {
      const value = (draft[field.name] ?? "").trim();
      result[field.name] =
        value === ""
          ? null
          : field.boolean
            ? value === "true"
            : field.type === "number"
              ? Number(value)
              : value;
    }
  if (draft.goal !== "OTHER") result.goal_detail = null;
  if (draft.has_injury !== "true") result.injury_description = null;
  return result;
}
export function ProfileFields({
  group,
  values,
  change,
  disabled,
  fieldNames,
}: {
  group: number;
  values: ProfileDraft;
  change: (name: string, value: string) => void;
  disabled: boolean;
  fieldNames?: readonly string[];
}) {
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  const maxDate = yesterday.toISOString().slice(0, 10);
  return (
    <div className="grid gap-5 sm:grid-cols-2">
      {groups[group].fields
        .filter((field) => !fieldNames || fieldNames.includes(field.name))
        .map((field) => {
          if (field.name === "goal_detail" && values.goal !== "OTHER")
            return null;
          if (
            field.name === "injury_description" &&
            values.has_injury !== "true"
          )
            return null;
          const long = (field.maxLength ?? 0) > 120;
          return (
            <div key={field.name} className={long ? "sm:col-span-2" : ""}>
              <label
                className="mb-2 block text-sm font-medium"
                htmlFor={field.name}
              >
                {field.label}
                {field.required ||
                field.name === "goal_detail" ||
                field.name === "injury_description"
                  ? " *"
                  : ""}
              </label>
              {field.options ? (
                <select
                  id={field.name}
                  className="auth-input"
                  required={field.required}
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
              ) : long ? (
                <textarea
                  id={field.name}
                  className="auth-input min-h-24"
                  maxLength={field.maxLength}
                  required={
                    field.name === "goal_detail" ||
                    field.name === "injury_description"
                  }
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
                  step={field.type === "number" ? "any" : undefined}
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
        .flatMap((g) => g.fields)
        .filter(
          (f) =>
            values[f.name] &&
            (f.name !== "goal_detail" || values.goal === "OTHER") &&
            (f.name !== "injury_description" || values.has_injury === "true"),
        )
        .map((f) => (
          <div key={f.name}>
            <dt className="text-muted-foreground">{f.label}</dt>
            <dd className="mt-1 whitespace-pre-wrap break-words">
              {f.options?.[values[f.name]] ?? values[f.name]}
            </dd>
          </div>
        ))}
    </dl>
  );
}
