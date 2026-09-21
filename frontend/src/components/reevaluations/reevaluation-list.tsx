"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useRef, useState } from "react";
import { ErrorState, LoadingState } from "@/components/master/resource-state";
import {
  draftFromStudent,
  type ProfileDraft,
  ProfileFields,
  ProfileSummary,
  profilePayload,
} from "@/components/students/profile-fields";
import { ApiError, apiRequest } from "@/lib/api";
import type { Area } from "@/lib/evolution";
import {
  type Reevaluation,
  type ReevaluationCategory,
  type ReevaluationList,
  reevaluationCategories,
  reevaluationStatuses,
  requestDate,
} from "@/lib/reevaluations";
import type { Student } from "@/lib/students";
import { useApiResource } from "@/lib/use-api-resource";

function NewRequest() {
  const profile = useApiResource<Student>("/students/me");
  const [step, setStep] = useState(0);
  const [draft, setDraft] = useState<ProfileDraft>({});
  const [category, setCategory] = useState<ReevaluationCategory>("WORKOUT");
  const [reason, setReason] = useState("");
  const [progress, setProgress] = useState("");
  const [difficulties, setDifficulties] = useState("");
  const [observations, setObservations] = useState("");
  const [front, setFront] = useState<File | null>(null);
  const [side, setSide] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const guard = useRef(false);
  const formRef = useRef<HTMLFormElement>(null);
  const router = useRouter();
  const student = profile.data;
  useEffect(() => {
    if (!student) return;
    let cancelled = false;
    async function loadLatest() {
      const base = draftFromStudent(student as Student);
      try {
        const listing = await apiRequest<ReevaluationList>(
          "/student/reevaluation-requests?status=COMPLETED&page_size=1",
        );
        const latest = listing.items[0];
        if (latest) {
          const detail = await apiRequest<Reevaluation>(
            `/student/reevaluation-requests/${encodeURIComponent(latest.id)}`,
          );
          if (detail.snapshot) {
            for (const [name, value] of Object.entries(detail.snapshot)) {
              if (name in base) base[name] = value == null ? "" : String(value);
            }
          }
        }
      } catch {
        // The current profile remains usable if historical prefill is unavailable.
      }
      if (!cancelled) setDraft(base);
    }
    void loadLatest();
    return () => {
      cancelled = true;
    };
  }, [student]);
  const change = (name: string, value: string) =>
    setDraft((current) => ({ ...current, [name]: value }));
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (guard.current || !student) return;
    if (
      reason.trim().length < 10 ||
      !progress.trim() ||
      !difficulties.trim() ||
      !observations.trim() ||
      !front ||
      !side
    ) {
      setError("Preencha o snapshot e envie as fotos frontal e lateral.");
      return;
    }
    const updated = profilePayload(draft);
    if (
      (updated.goal === "OTHER" && !updated.goal_detail) ||
      (updated.has_injury === true && !updated.injury_description)
    ) {
      setError("Revise os campos condicionais antes de enviar.");
      return;
    }
    guard.current = true;
    setBusy(true);
    setError("");
    const snapshot = {
      weight: updated.weight,
      desired_weight: updated.desired_weight,
      goal: updated.goal,
      goal_detail: updated.goal_detail,
      activity_level: updated.activity_level,
      training_frequency: updated.training_frequency,
      available_training_days:
        updated.available_training_days || String(updated.training_frequency),
      progress_perception: progress.trim(),
      difficulties: difficulties.trim(),
      observations: observations.trim(),
      work_routine: updated.work_routine,
      wake_time: updated.wake_time,
      sleep_time: updated.sleep_time,
      trains_currently: updated.trains_currently,
      training_location: updated.training_location,
      available_equipment: updated.available_equipment,
      training_experience: updated.training_experience,
      training_history: updated.training_history,
      training_duration_minutes: updated.training_duration_minutes,
      preferred_training_time: updated.preferred_training_time,
      has_injury: updated.has_injury,
      injury_description: updated.injury_description,
      physical_limitations: updated.physical_limitations,
      medical_restrictions: updated.medical_restrictions,
      meal_count: updated.meal_count,
      meal_schedule: updated.meal_schedule,
      cooking_skill: updated.cooking_skill,
      food_preferences: updated.food_preferences,
      disliked_foods: updated.disliked_foods,
      food_restrictions: updated.food_restrictions,
      food_allergies: updated.food_allergies,
      weekly_food_budget: updated.weekly_food_budget,
      food_notes: updated.food_notes,
    };
    const form = new FormData();
    form.set(
      "data",
      JSON.stringify({ category, reason: reason.trim(), snapshot }),
    );
    form.set("front", front);
    form.set("side", side);
    try {
      const result = await apiRequest<Reevaluation>(
        "/student/reevaluation-requests/with-photos",
        { method: "POST", body: form },
      );
      router.push(`/student/reevaluation-requests/${result.id}?sent=1`);
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401)
        router.replace("/login");
      else
        setError(
          cause instanceof Error ? cause.message : "Não foi possível enviar.",
        );
      guard.current = false;
      setBusy(false);
    }
  }
  if (profile.loading) return <LoadingState />;
  if (profile.error)
    return <ErrorState message={profile.error} retry={profile.reload} />;
  if (student?.status !== "ACTIVE" || !student.professional_id)
    return (
      <p className="rounded-lg border bg-white p-5 text-sm text-muted-foreground">
        Para solicitar reavaliação, seu cadastro precisa estar ativo e vinculado
        a um profissional.
      </p>
    );
  return (
    <form
      ref={formRef}
      onSubmit={submit}
      aria-busy={busy}
      className="space-y-5 rounded-lg border bg-white p-5"
    >
      <h2 className="text-lg font-semibold">Solicitar reavaliação</h2>
      <p className="text-sm text-muted-foreground">
        Os valores atuais foram usados como base. Informe o que mudou; o envio
        cria um snapshot histórico.
      </p>
      <p className="text-sm font-medium" aria-live="polite">
        Etapa {step + 1} de 6
      </p>
      <div
        className="h-2 overflow-hidden rounded-full bg-secondary"
        aria-hidden="true"
      >
        <div
          className="h-full bg-primary"
          style={{ width: `${((step + 1) / 6) * 100}%` }}
        />
      </div>
      {step === 0 && (
        <div className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="text-sm">
              Categoria
              <select
                className="auth-input mt-2"
                value={category}
                onChange={(e) =>
                  setCategory(e.target.value as ReevaluationCategory)
                }
              >
                {Object.entries(reevaluationCategories).map(([v, l]) => (
                  <option key={v} value={v}>
                    {l}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <ProfileFields
            group={0}
            values={draft}
            change={change}
            disabled={busy}
            fieldNames={[
              "weight",
              "desired_weight",
              "goal",
              "goal_detail",
              "activity_level",
            ]}
          />
          <label className="block text-sm">
            Motivo *
            <textarea
              className="auth-input mt-2 min-h-24"
              required
              minLength={10}
              maxLength={2000}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </label>
          <label className="block text-sm">
            Percepção de evolução *
            <textarea
              className="auth-input mt-2 min-h-20"
              required
              maxLength={2000}
              value={progress}
              onChange={(e) => setProgress(e.target.value)}
            />
          </label>
          <label className="block text-sm">
            Dificuldades encontradas *
            <textarea
              className="auth-input mt-2 min-h-20"
              required
              maxLength={2000}
              value={difficulties}
              onChange={(e) => setDifficulties(e.target.value)}
            />
          </label>
          <label className="block text-sm">
            Observações atuais *
            <textarea
              className="auth-input mt-2 min-h-20"
              required
              maxLength={2000}
              value={observations}
              onChange={(e) => setObservations(e.target.value)}
            />
          </label>
        </div>
      )}
      {step === 1 && (
        <ProfileFields
          group={1}
          values={draft}
          change={change}
          disabled={busy}
        />
      )}
      {step === 2 && (
        <ProfileFields
          group={2}
          values={draft}
          change={change}
          disabled={busy}
          fieldNames={[
            "meal_count",
            "meal_schedule",
            "cooking_skill",
            "food_preferences",
            "disliked_foods",
            "food_restrictions",
            "food_allergies",
            "weekly_food_budget",
            "food_notes",
          ]}
        />
      )}
      {step === 3 && (
        <ProfileFields
          group={3}
          values={draft}
          change={change}
          disabled={busy}
          fieldNames={[
            "has_injury",
            "injury_description",
            "physical_limitations",
            "medical_restrictions",
          ]}
        />
      )}
      {step === 4 && (
        <div className="space-y-5">
          <p className="rounded-md bg-secondary p-4 text-sm">
            Envie fotos do corpo para acompanhamento da sua evolução. Não inclua
            o rosto nas imagens.
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="text-sm">
              Foto frontal *
              <input
                className="auth-input mt-2"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                required
                onChange={(e) => setFront(e.target.files?.[0] ?? null)}
              />
            </label>
            <label className="text-sm">
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
        </div>
      )}
      {step === 5 && (
        <div className="space-y-4">
          <h3 className="font-semibold">Revise os dados antes de enviar</h3>
          <ProfileSummary values={draft} />
          <p className="text-sm">
            Fotos selecionadas: {front?.name || "frontal pendente"} e{" "}
            {side?.name || "lateral pendente"}.
          </p>
        </div>
      )}
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      <div className="flex flex-wrap justify-between gap-3">
        {step > 0 && (
          <button
            type="button"
            className="master-secondary min-h-11"
            disabled={busy}
            onClick={() => {
              setError("");
              setStep((value) => value - 1);
            }}
          >
            Voltar
          </button>
        )}
        {step < 5 ? (
          <button
            type="button"
            className="master-primary ml-auto min-h-11"
            disabled={busy}
            onClick={() => {
              if (formRef.current?.reportValidity()) {
                setError("");
                setStep((value) => value + 1);
              }
            }}
          >
            Continuar
          </button>
        ) : (
          <button
            type="submit"
            className="master-primary ml-auto min-h-11"
            disabled={busy}
          >
            {busy ? "Enviando…" : "Enviar solicitação"}
          </button>
        )}
      </div>
    </form>
  );
}
export function ReevaluationListPage({ area }: { area: Area }) {
  const [status, setStatus] = useState("");
  const [category, setCategory] = useState("");
  const [page, setPage] = useState(1);
  const query = new URLSearchParams({ page: String(page) });
  if (status) query.set("status", status);
  if (category) query.set("category", category);
  const resource = useApiResource<ReevaluationList>(
    `/${area}/reevaluation-requests?${query}`,
  );
  return (
    <div className="space-y-6 [overflow-wrap:anywhere]">
      <h1 className="text-2xl font-semibold">
        {area === "student" ? "Minhas reavaliações" : "Reavaliações"}
      </h1>
      <p className="text-sm text-muted-foreground">
        {area === "master"
          ? "Consulta administrativa das solicitações e respostas."
          : area === "professional"
            ? "Acompanhe as solicitações dos alunos da sua carteira."
            : "Solicite uma revisão e acompanhe a resposta do seu profissional."}
      </p>
      {area === "student" && <NewRequest />}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">
          {area === "student" ? "Histórico de solicitações" : "Solicitações"}
        </h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <label htmlFor="request-status-filter" className="text-sm">
            Status
            <select
              id="request-status-filter"
              className="auth-input mt-2"
              value={status}
              onChange={(event) => {
                setStatus(event.target.value);
                setPage(1);
              }}
            >
              <option value="">Todos</option>
              {Object.entries(reevaluationStatuses).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label htmlFor="request-category-filter" className="text-sm">
            Categoria
            <select
              id="request-category-filter"
              className="auth-input mt-2"
              value={category}
              onChange={(event) => {
                setCategory(event.target.value);
                setPage(1);
              }}
            >
              <option value="">Todas</option>
              {Object.entries(reevaluationCategories).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        </div>
        {resource.loading ? (
          <LoadingState />
        ) : resource.error ? (
          <ErrorState message={resource.error} retry={resource.reload} />
        ) : (
          resource.data && (
            <>
              {!resource.data.total ? (
                <p className="rounded-lg border border-dashed p-5 text-sm text-muted-foreground">
                  Nenhuma solicitação encontrada.
                </p>
              ) : (
                <ul className="space-y-3">
                  {resource.data.items.map((item) => (
                    <li key={item.id}>
                      <Link
                        href={`/${area}/reevaluation-requests/${item.id}`}
                        className="block space-y-3 rounded-lg border bg-white p-5 hover:border-primary"
                      >
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <h3 className="font-semibold">
                            {item.student_name ? `${item.student_name} · ` : ""}
                            {reevaluationCategories[item.category]}
                          </h3>
                          <span className="rounded-full bg-secondary px-3 py-1 text-xs font-medium">
                            {reevaluationStatuses[item.status]}
                          </span>
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {item.reason_summary}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {requestDate(item.created_at)}
                        </p>
                        <span className="block text-sm text-primary">
                          Ver solicitação
                        </span>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
              {resource.data.total > 20 && (
                <div className="flex flex-wrap items-center gap-3">
                  <button
                    className="master-secondary"
                    type="button"
                    disabled={page === 1}
                    onClick={() => setPage(page - 1)}
                  >
                    Anterior
                  </button>
                  <span className="text-sm">Página {page}</span>
                  <button
                    className="master-secondary"
                    type="button"
                    disabled={page * 20 >= resource.data.total}
                    onClick={() => setPage(page + 1)}
                  >
                    Próxima
                  </button>
                </div>
              )}
            </>
          )
        )}
      </section>
    </div>
  );
}
