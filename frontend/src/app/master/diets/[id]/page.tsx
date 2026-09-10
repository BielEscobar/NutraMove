import { DietHistory } from "@/components/diets/diet-history";
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <DietHistory area="master" id={id} />;
}
