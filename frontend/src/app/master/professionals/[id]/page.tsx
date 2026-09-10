import { ProfessionalDetail } from "@/components/master/professional-detail";

export default async function ProfessionalPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ProfessionalDetail id={id} />;
}
