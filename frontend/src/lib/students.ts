export const statuses = {
  PENDING_APPROVAL: "Em análise",
  ACTIVE: "Ativo",
  INACTIVE: "Inativo",
  REJECTED: "Rejeitado",
} as const;
export const goals = {
  WEIGHT_LOSS: "Emagrecimento",
  MUSCLE_GAIN: "Hipertrofia",
  MAINTENANCE: "Manutenção",
  FITNESS: "Condicionamento",
  BODY_RECOMPOSITION: "Recomposição corporal",
  OTHER: "Outro",
} as const;
export type StudentStatus = keyof typeof statuses;
export type StudentBrief = {
  id: string;
  name: string;
  email: string;
  goal: keyof typeof goals;
  status: StudentStatus;
  professional_id: string | null;
  professional_name: string | null;
};
export type Student = StudentBrief & {
  birth_date: string;
  phone: string | null;
  weight: number;
  height: number;
  goal_detail: string | null;
  activity_level: string;
  training_experience: string;
  training_frequency: number;
  preferred_training_time: string | null;
  work_routine: string | null;
  meal_schedule: string | null;
  approximate_water_intake: number | null;
  food_preferences: string | null;
  food_restrictions: string | null;
  notes: string | null;
  water_goal: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};
export type StudentList = {
  items: StudentBrief[];
  total: number;
  page: number;
  page_size: number;
};
export type StudentArea = "master" | "professional";
export function homeForRole(role: "MASTER" | "PROFESSIONAL" | "STUDENT") {
  return role === "MASTER"
    ? "/master"
    : role === "PROFESSIONAL"
      ? "/professional"
      : "/student";
}
