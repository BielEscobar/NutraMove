import { AppShell } from "@/components/app-shell";
import { AuditLogPage } from "@/components/transfers/audit-log-page";

export default function Page() {
  return (
    <AppShell allowedRole="MASTER">
      <AuditLogPage />
    </AppShell>
  );
}
