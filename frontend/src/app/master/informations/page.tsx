import { AppShell } from "@/components/app-shell";
import { InformationListPage } from "@/components/informations/information-list";
export default function Page() {
  return (
    <AppShell allowedRole="MASTER">
      <InformationListPage area="master" />
    </AppShell>
  );
}
