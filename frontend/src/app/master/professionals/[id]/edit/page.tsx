import { ProfessionalEditor } from "@/components/master/professional-editor";

export default async function EditProfessionalPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ProfessionalEditor id={id} />;
}
