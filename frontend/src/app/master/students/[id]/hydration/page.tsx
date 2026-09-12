import { HydrationPage } from "@/components/hydration/hydration-page";
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <HydrationPage area="master" studentId={id} />;
}
