export const dietStatuses = {
  DRAFT: "Rascunho",
  PENDING_REVIEW: "Aguardando revisão",
  APPROVED: "Publicado",
  ARCHIVED: "Arquivado",
} as const;
export type DietStatus = keyof typeof dietStatuses;
export type Substitution = {
  name: string;
  quantity: string | null;
  unit: string | null;
  notes: string | null;
};
export type Food = {
  name: string;
  quantity: string;
  unit: string;
  notes: string | null;
  substitutions: Substitution[];
};
export type Meal = { name: string; time: string | null; foods: Food[] };
export type DietContent = {
  name: string;
  goal: string | null;
  start_date: string | null;
  next_review_date: string | null;
  notes: string | null;
  meals: Meal[];
};
export type DietSummary = {
  id: string;
  student_id: string;
  name: string;
  created_at: string;
};
export type VersionSummary = {
  id: string;
  diet_id: string;
  version_number: number;
  edit_revision: number;
  name: string;
  status: DietStatus;
  source: "MANUAL" | "AI_GENERATED";
  approved_at: string | null;
  created_at: string;
};
export type DietVersion = DietContent &
  VersionSummary & {
    created_by_user_id: string;
    approved_by_user_id: string | null;
    updated_at: string;
  };
export type PublishedDiet = DietContent & {
  version_number: number;
  approved_at: string;
};
export type DietArea = "professional" | "master";
