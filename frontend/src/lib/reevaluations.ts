export const reevaluationCategories = {
  DIET: "Dieta",
  WORKOUT: "Treino",
  EVOLUTION: "Evolução",
  DIFFICULTY: "Dificuldade no acompanhamento",
  OTHER: "Outro",
} as const;
export const reevaluationStatuses = {
  PENDING: "Pendente",
  IN_REVIEW: "Em análise",
  COMPLETED: "Concluída",
  CANCELLED: "Cancelada",
} as const;
export type ReevaluationCategory = keyof typeof reevaluationCategories;
export type ReevaluationStatus = keyof typeof reevaluationStatuses;
export type ReevaluationBrief = {
  id: string;
  category: ReevaluationCategory;
  reason_summary: string;
  status: ReevaluationStatus;
  created_at: string;
  student_id?: string;
  student_name?: string;
};
export type Reevaluation = Omit<ReevaluationBrief, "reason_summary"> & {
  reason: string;
  professional_response: string | null;
  updated_at: string;
  reviewed_at: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
};
export type ReevaluationList = {
  items: ReevaluationBrief[];
  total: number;
  page: number;
  page_size: number;
};
export function requestDate(value: string) {
  return new Date(value).toLocaleString("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  });
}
