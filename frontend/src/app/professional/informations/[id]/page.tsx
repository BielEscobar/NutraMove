import { InformationDetailPage } from "@/components/informations/information-detail";
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <InformationDetailPage area="professional" id={id} />;
}
