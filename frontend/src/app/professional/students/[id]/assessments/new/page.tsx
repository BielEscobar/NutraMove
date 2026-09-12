import { AssessmentForm } from "@/components/evolution/assessment-form";
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <AssessmentForm studentId={id} />;
}
