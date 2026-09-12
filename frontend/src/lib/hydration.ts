export type HydrationSummary = {
  date: string;
  timezone: string;
  consumed_ml: number;
  goal_ml: number | null;
  remaining_ml: number | null;
  percentage: number | null;
};
export type WaterRecord = {
  id: string;
  amount_ml: number;
  consumed_at: string;
  created_at: string;
};
export type HydrationDay = HydrationSummary & {
  records: WaterRecord[];
  total_records: number;
  page: number;
  page_size: number;
};
export type HydrationHistory = {
  timezone: string;
  days: number;
  items: { date: string; consumed_ml: number }[];
};
export function volume(ml: number) {
  return ml >= 1000
    ? `${(ml / 1000).toLocaleString("pt-BR", { maximumFractionDigits: 3 })} L`
    : `${ml.toLocaleString("pt-BR")} ml`;
}
