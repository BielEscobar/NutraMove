import { AssessmentDetail } from "@/components/evolution/assessment-detail";
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <AssessmentDetail area="professional" id={id} edit />;
}
