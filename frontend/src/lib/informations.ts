export const informationCategories = {
  INFO: "Informação",
  TIP: "Dica",
  NOTICE: "Aviso",
  GUIDANCE: "Orientação",
} as const;
export const informationStatuses = {
  DRAFT: "Rascunho",
  PUBLISHED: "Publicado",
  ARCHIVED: "Arquivado",
} as const;
export type InformationCategory = keyof typeof informationCategories;
export type InformationStatus = keyof typeof informationStatuses;
export type InformationBrief = {
  id: string;
  title: string;
  summary: string;
  category: InformationCategory;
  published_at: string | null;
  student_id?: string | null;
  status?: InformationStatus;
};
export type Information = InformationBrief & {
  content: string;
  created_at: string;
  updated_at: string;
  edit_revision?: number;
};
export type InformationList = {
  items: InformationBrief[];
  total: number;
  page: number;
  page_size: number;
};
