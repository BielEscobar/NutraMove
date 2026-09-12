import { EvolutionPage } from "@/components/evolution/evolution-page";
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <EvolutionPage area="master" studentId={id} />;
}
