import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { ProfessionalForm } from "@/components/master/professional-form";

export default function NewProfessionalPage() {
  return (
    <div>
      <Link
        href="/master/professionals"
        className="mb-6 inline-flex items-center gap-2 text-sm text-muted-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden="true" /> Profissionais
      </Link>
      <h1 className="text-2xl font-semibold tracking-tight">
        Novo profissional
      </h1>
      <p className="mt-2 mb-7 text-sm text-muted-foreground">
        Cadastre o profissional e defina sua senha de acesso.
      </p>
      <ProfessionalForm />
    </div>
  );
}
