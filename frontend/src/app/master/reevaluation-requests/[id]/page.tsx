import { ReevaluationDetail } from "@/components/reevaluations/reevaluation-detail";
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ReevaluationDetail area="master" id={id} />;
}
