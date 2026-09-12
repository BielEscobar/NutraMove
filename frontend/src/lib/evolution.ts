export const measurementTypes = {
  ARM: "Braço",
  CHEST: "Peito / tórax",
  WAIST: "Cintura",
  ABDOMEN: "Abdômen",
  HIP: "Quadril",
  THIGH: "Coxa",
  CALF: "Panturrilha",
} as const;
export type MeasurementType = keyof typeof measurementTypes;
export type Side = "LEFT" | "RIGHT" | null;
export const periods = {
  "7d": "7 dias",
  "30d": "30 dias",
  "90d": "90 dias",
  "6m": "6 meses",
  "1y": "1 ano",
  all: "Todo o histórico",
} as const;
export type Period = keyof typeof periods;
export type Area = "professional" | "master" | "student";
export type Measurement = {
  measurement_type: MeasurementType;
  side: Side;
  value_cm: number;
  notes: string | null;
};
export type AssessmentContent = {
  weight_kg: number | null;
  height_cm: number | null;
  notes: string | null;
  measurements: Measurement[];
};
export type Assessment = AssessmentContent & {
  id: string;
  assessment_date: string;
  bmi: number | null;
  created_at: string;
  updated_at: string;
};
export type StaffAssessment = Assessment & {
  student_id: string;
  created_by_user_id: string;
  updated_by_user_id: string;
  edit_revision: number;
};
export type AssessmentBrief = Pick<
  Assessment,
  | "id"
  | "assessment_date"
  | "weight_kg"
  | "height_cm"
  | "bmi"
  | "created_at"
  | "updated_at"
>;
export type AssessmentList = {
  items: AssessmentBrief[];
  total: number;
  page: number;
  page_size: number;
};
export type Point = { assessment_id: string; date: string; value: number };
export type Evolution = {
  current: {
    latest_assessment_date: string;
    weight_kg: number | null;
    weight_date: string | null;
    bmi: number | null;
  } | null;
  weight_history: Point[];
  bmi_history: Point[];
  measurements: {
    measurement_type: MeasurementType;
    side: Side;
    points: Point[];
  }[];
  period: Period;
};
export const bmiNote =
  "Indicador de referência calculado a partir do peso e altura registrados. Não é um diagnóstico.";
export function measureLabel(kind: MeasurementType, side: Side) {
  return `${measurementTypes[kind]}${side === "LEFT" ? " — esquerdo(a)" : side === "RIGHT" ? " — direito(a)" : ""}`;
}
export function displayDate(value: string) {
  return value.split("-").reverse().join("/");
}
export function number(value: number | null) {
  return value === null
    ? "Não informado"
    : value.toLocaleString("pt-BR", { maximumFractionDigits: 2 });
}
export function studentPath(area: Area, id?: string) {
  return area === "student"
    ? "/student"
    : `/${area}/students/${encodeURIComponent(id ?? "")}`;
}
