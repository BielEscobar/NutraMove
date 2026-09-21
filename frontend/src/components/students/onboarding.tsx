"use client";

import Link from "next/link";
import { type FormEvent, useRef, useState } from "react";
import { ApiError, apiRequest } from "@/lib/api";
import {
  groups,
  type ProfileDraft,
  ProfileFields,
  ProfileSummary,
  profilePayload,
} from "./profile-fields";

const steps = [
  "Conta",
  ...groups.map((group) => group.title),
  "Fotos de evolução",
  "Revisão",
];
const photoStep = 1 + groups.length;
const reviewStep = photoStep + 1;
export function Onboarding({ professionalId }: { professionalId: string }) {
  const [step, setStep] = useState(0);
  const [account, setAccount] = useState({
    name: "",
    email: "",
    password: "",
    password_confirmation: "",
    professional_id: professionalId,
  });
  const [profile, setProfile] = useState<ProfileDraft>({});
  const [front, setFront] = useState<File | null>(null);
  const [side, setSide] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const submitting = useRef(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  function change(name: string, value: string) {
    setProfile((previous) => ({ ...previous, [name]: value }));
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    if (step === 0 && account.password !== account.password_confirmation) {
      setError("As senhas devem ser iguais.");
      return;
    }
    if (step === 0 && !account.name.trim()) {
      setError("Informe seu nome.");
      return;
    }
    if (
      step === 1 &&
      profile.goal === "OTHER" &&
      !profile.goal_detail?.trim()
    ) {
      setError("Descreva seu objetivo.");
      return;
    }
    if (step === photoStep && (!front || !side)) {
      setError("Envie as fotos frontal e lateral.");
      return;
    }
    if (step < reviewStep) {
      setStep(step + 1);
      return;
    }
    if (submitting.current) return;
    submitting.current = true;
    setBusy(true);
    try {
      const form = new FormData();
      form.set(
        "data",
        JSON.stringify({
          ...account,
          professional_id: account.professional_id.trim() || null,
          ...profilePayload(profile),
        }),
      );
      form.set("front", front as File);
      form.set("side", side as File);
      await apiRequest("/students/register-with-photos", {
        method: "POST",
        body: form,
      });
      setAccount({
        name: "",
        email: "",
        password: "",
        password_confirmation: "",
        professional_id: "",
      });
      setProfile({});
      setDone(true);
    } catch (cause) {
      setError(
        cause instanceof ApiError && cause.status === 409
          ? "E-mail já cadastrado. Volte à etapa Conta para revisar."
          : cause instanceof ApiError && cause.status === 422
            ? "Revise os dados e o código do profissional. O profissional precisa estar disponível para cadastro."
            : cause instanceof Error
              ? cause.message
              : "Não foi possível cadastrar.",
      );
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }
  if (done)
    return (
      <section className="mx-auto max-w-2xl p-8">
        <h1 className="text-2xl font-semibold">
          Seu cadastro está em análise.
        </h1>
        <p className="my-5">
          Assim que seu acompanhamento for preparado, você terá acesso aos seus
          planos.
        </p>
        <Link className="master-primary" href="/login">
          Entrar na minha conta
        </Link>
      </section>
    );
  return (
    <main className="mx-auto max-w-3xl px-5 py-10">
      <Link href="/login" className="text-sm text-primary">
        Já tenho conta
      </Link>
      <h1 className="mt-5 text-3xl font-semibold">
        Seu primeiro passo no NUTRAMOVE
      </h1>
      <p className="mt-3 text-muted-foreground">
        Conte um pouco sobre você. Campos com * são obrigatórios.
      </p>
      <ol
        aria-label="Etapas do cadastro"
        className="my-8 grid grid-cols-3 gap-2 text-xs sm:grid-cols-6"
      >
        {steps.map((label, index) => (
          <li
            key={label}
            aria-current={index === step ? "step" : undefined}
            className={
              index <= step
                ? "rounded-md bg-primary/10 p-3 text-primary"
                : "rounded-md bg-secondary p-3"
            }
          >
            {index + 1}. {label}
          </li>
        ))}
      </ol>
      <form
        onSubmit={submit}
        className="rounded-lg border bg-white p-6"
        aria-busy={busy}
      >
        <h2 className="mb-6 text-xl font-semibold">{steps[step]}</h2>
        {step === 0 && (
          <div className="space-y-5">
            {(
              ["name", "email", "password", "password_confirmation"] as const
            ).map((name) => (
              <div key={name}>
                <label
                  htmlFor={name}
                  className="mb-2 block text-sm font-medium"
                >
                  {
                    {
                      name: "Nome completo",
                      email: "E-mail",
                      password: "Senha (12 a 128 caracteres)",
                      password_confirmation: "Confirme a senha",
                    }[name]
                  }{" "}
                  *
                </label>
                <input
                  id={name}
                  className="auth-input"
                  type={
                    name.includes("password")
                      ? "password"
                      : name === "email"
                        ? "email"
                        : "text"
                  }
                  autoComplete={
                    name.includes("password")
                      ? "new-password"
                      : name === "name"
                        ? "name"
                        : "email"
                  }
                  required
                  minLength={name.includes("password") ? 12 : 1}
                  maxLength={
                    name.includes("password")
                      ? 128
                      : name === "name"
                        ? 120
                        : 320
                  }
                  value={account[name]}
                  onChange={(e) =>
                    setAccount((previous) => ({
                      ...previous,
                      [name]: e.target.value,
                    }))
                  }
                />
              </div>
            ))}
            <div>
              <label
                htmlFor="professional_id"
                className="mb-2 block text-sm font-medium"
              >
                Código do profissional (opcional)
              </label>
              <input
                id="professional_id"
                className="auth-input"
                maxLength={36}
                pattern="[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
                value={account.professional_id}
                onChange={(e) =>
                  setAccount((previous) => ({
                    ...previous,
                    professional_id: e.target.value,
                  }))
                }
              />
              <p className="mt-2 text-xs text-muted-foreground">
                Use o link ou código fornecido pelo seu profissional. Sem
                código, seu cadastro será analisado pela administração.
              </p>
            </div>
          </div>
        )}
        {step > 0 && step <= groups.length && (
          <ProfileFields
            group={step - 1}
            values={profile}
            change={change}
            disabled={busy}
          />
        )}
        {step === photoStep && (
          <div className="space-y-5">
            <p className="rounded-md bg-secondary p-4 text-sm">
              Envie fotos do corpo para acompanhamento da sua evolução. Não
              inclua o rosto nas imagens.
            </p>
            <label className="block text-sm font-medium">
              Foto frontal *
              <input
                className="auth-input mt-2"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                required
                onChange={(e) => setFront(e.target.files?.[0] ?? null)}
              />
            </label>
            <label className="block text-sm font-medium">
              Foto lateral *
              <input
                className="auth-input mt-2"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                required
                onChange={(e) => setSide(e.target.files?.[0] ?? null)}
              />
            </label>
          </div>
        )}
        {step === reviewStep && (
          <div className="space-y-6">
            <p>Confira seus dados antes de enviar. Use Voltar para corrigir.</p>
            <p className="break-words">
              {account.name} · {account.email}
            </p>
            <p className="text-sm">
              Profissional:{" "}
              {account.professional_id || "Sem profissional atribuído"}
            </p>
            <ProfileSummary values={profile} />
            <p className="text-sm text-muted-foreground">
              Informe apenas dados relevantes ao acompanhamento. Seu cadastro
              será acessível à administração e ao profissional responsável. A
              senha não é exibida no resumo.
            </p>
          </div>
        )}
        {error && (
          <p role="alert" className="mt-5 text-sm text-destructive">
            {error}
          </p>
        )}
        <div className="mt-8 flex justify-between gap-3">
          <button
            type="button"
            className="master-secondary"
            disabled={step === 0 || busy}
            onClick={() => {
              setError("");
              setStep(step - 1);
            }}
          >
            Voltar
          </button>
          <button className="master-primary" type="submit" disabled={busy}>
            {busy
              ? "Enviando…"
              : step === reviewStep
                ? "Enviar cadastro"
                : "Continuar"}
          </button>
        </div>
      </form>
    </main>
  );
}
