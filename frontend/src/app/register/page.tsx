import { Onboarding } from "@/components/students/onboarding";

export default async function RegisterPage({
  searchParams,
}: {
  searchParams: Promise<{ professional_id?: string }>;
}) {
  const query = await searchParams;
  return (
    <Onboarding
      professionalId={
        typeof query.professional_id === "string" ? query.professional_id : ""
      }
    />
  );
}
