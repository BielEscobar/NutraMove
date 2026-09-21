import type { WorkoutContent, WorkoutDay, WorkoutExercise } from "./workouts";

export type EditExercise = WorkoutExercise & { key: string };
export type EditDay = Omit<WorkoutDay, "exercises"> & {
  key: string;
  exercises: EditExercise[];
};
export type Draft = Omit<WorkoutContent, "days"> & { days: EditDay[] };

export function hydrate(content: WorkoutContent): Draft {
  return {
    ...content,
    days: content.days.map((day) => ({
      ...day,
      isRest: day.isRest ?? false,
      key: crypto.randomUUID(),
      exercises: day.exercises.map((exercise) => ({
        ...exercise,
        key: crypto.randomUUID(),
      })),
    })),
  };
}

export function clean(draft: Draft): WorkoutContent {
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
      isRest: day.isRest,
      exercises: day.isRest
        ? []
        : day.exercises.map(({ key: _key, ...exercise }) => exercise),
    })),
  };
}

export function hasUnsavedChanges(draft: Draft, savedContent: string): boolean {
  return JSON.stringify(clean(draft)) !== savedContent;
}
