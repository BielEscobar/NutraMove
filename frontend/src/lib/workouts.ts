export const workoutStatuses = {
  DRAFT: "Rascunho",
  PENDING_REVIEW: "Aguardando revisão",
  APPROVED: "Publicado",
  ARCHIVED: "Arquivado",
} as const;
export type WorkoutStatus = keyof typeof workoutStatuses;
export type WorkoutExercise = {
  name: string;
  muscle_group: string | null;
  description: string | null;
  instructions: string | null;
  sets: number | null;
  repetitions: string | null;
  load: string | null;
  duration: string | null;
  rest_seconds: number | null;
  notes: string | null;
};
export type WorkoutDay = {
  name: string;
  description: string | null;
  isRest: boolean;
  exercises: WorkoutExercise[];
};
export type WorkoutContent = {
  name: string;
  goal: string | null;
  frequency_per_week: number | null;
  start_date: string | null;
  next_review_date: string | null;
  notes: string | null;
  days: WorkoutDay[];
};
export type WorkoutSummary = {
  id: string;
  student_id: string;
  name: string;
  created_at: string;
};
export type VersionSummary = {
  id: string;
  workout_id: string;
  version_number: number;
  edit_revision: number;
  name: string;
  status: WorkoutStatus;
  source: "MANUAL" | "AI_GENERATED";
  approved_at: string | null;
  created_at: string;
};
export type WorkoutVersion = WorkoutContent &
  VersionSummary & {
    created_by_user_id: string;
    approved_by_user_id: string | null;
    updated_at: string;
  };
export type PublishedWorkout = WorkoutContent & {
  version_number: number;
  approved_at: string;
};
export type WorkoutArea = "professional" | "master";
