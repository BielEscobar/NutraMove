export type Professional = {
  id: string;
  user_id: string;
  name: string;
  email: string;
  specialty: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type ProfessionalList = {
  items: Professional[];
  total: number;
  page: number;
  page_size: number;
};

export type ProfessionalSummary = {
  total: number;
  active: number;
  inactive: number;
};
