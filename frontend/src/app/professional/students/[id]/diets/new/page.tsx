import { DietEditor } from "@/components/diets/diet-editor";
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <DietEditor
      path={`/professional/students/${id}/diets`}
      backHref={`/professional/students/${id}/diets`}
    />
  );
}
