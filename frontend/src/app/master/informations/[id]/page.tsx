import { AppShell } from "@/components/app-shell";
import { InformationDetailPage } from "@/components/informations/information-detail";
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <AppShell allowedRole="MASTER">
      <InformationDetailPage area="master" id={id} />
    </AppShell>
  );
}
