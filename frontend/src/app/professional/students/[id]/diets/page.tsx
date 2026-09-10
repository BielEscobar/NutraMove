import { DietList } from "@/components/diets/diet-list";
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <DietList area="professional" studentId={id} />;
}
