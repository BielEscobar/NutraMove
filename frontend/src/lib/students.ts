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
  sex: string | null;
  phone: string | null;
  weight: number;
  height: number;
  desired_weight: number | null;
  goal_detail: string | null;
  activity_level: string;
  training_experience: string;
  training_frequency: number;
  preferred_training_time: string | null;
  wake_time: string | null;
  sleep_time: string | null;
  trains_currently: boolean | null;
  training_history: string | null;
  training_location: string | null;
  available_equipment: string | null;
  available_training_days: string | null;
  training_duration_minutes: number | null;
  work_routine: string | null;
  meal_schedule: string | null;
  meal_count: number | null;
  cooking_skill: string | null;
  approximate_water_intake: number | null;
  food_preferences: string | null;
  disliked_foods: string | null;
  food_restrictions: string | null;
  food_allergies: string | null;
  weekly_food_budget: number | null;
  food_notes: string | null;
  has_injury: boolean | null;
  injury_description: string | null;
  physical_limitations: string | null;
  medical_restrictions: string | null;
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
