import type { Student, StudentStatus } from "./students";

export type StudentMetrics = {
  total: number;
  active: number;
  pending: number;
  inactive: number;
  rejected: number;
};
export type MasterDashboard = {
  professionals_total: number;
  professionals_active: number;
  students: StudentMetrics;
  students_unassigned: number;
};
export type ProfessionalDashboard = {
  students: StudentMetrics;
  recent_students: {
    id: string;
    name: string;
    status: StudentStatus;
    created_at: string;
  }[];
};
export type StudentDashboard = Pick<
  Student,
  | "name"
  | "status"
  | "goal"
  | "goal_detail"
  | "weight"
  | "height"
  | "professional_name"
>;
