import { AppShell } from "@/components/app-shell";
import { InformationDetailPage } from "@/components/informations/information-detail";
export default function Page() {
  return (
    <AppShell allowedRole="PROFESSIONAL">
      <InformationDetailPage area="professional" />
    </AppShell>
  );
}
