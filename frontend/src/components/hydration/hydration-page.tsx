"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useRef, useState } from "react";
import { ErrorState, LoadingState } from "@/components/master/resource-state";
import { ApiError, apiRequest } from "@/lib/api";
import { type Area, displayDate, studentPath } from "@/lib/evolution";
import {
  type HydrationDay,
  type HydrationHistory,
  volume,
} from "@/lib/hydration";
import { useApiResource } from "@/lib/use-api-resource";
import { HydrationProgress } from "./hydration-card";
import { HydrationChart } from "./hydration-chart";

export function HydrationPage({
  area,
  studentId,
}: {
  area: Area;
  studentId?: string;
}) {
  const base = studentPath(area, studentId);
  const [page, setPage] = useState(1);
  const [days, setDays] = useState(7);
  const resource = useApiResource<HydrationDay>(
    `${base}/hydration?page=${page}`,
  );
  const history = useApiResource<HydrationHistory>(
    `${base}/hydration/history?days=${days}`,
  );
  const [amount, setAmount] = useState("");
  const [consumedAt, setConsumedAt] = useState("");
  const [goal, setGoal] = useState("");
  const [editingGoal, setEditingGoal] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const guard = useRef(false);
  const router = useRouter();
  async function mutate(
    path: string,
    method: string,
    body: object,
    message: string,
  ) {
    if (guard.current) return;
    guard.current = true;
    setBusy(true);
    setError("");
    setSuccess("");
    try {
      await apiRequest(path, { method, body: JSON.stringify(body) });
      setSuccess(message);
      setAmount("");
      setConsumedAt("");
      setEditingGoal(false);
      setPage(1);
      await Promise.all([resource.reload(), history.reload()]);
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401)
        router.replace("/login");
      else
        setError(
          cause instanceof Error ? cause.message : "Não foi possível salvar.",
        );
    } finally {
      guard.current = false;
      setBusy(false);
    }
  }
  function register(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = Number(amount);
    if (!Number.isInteger(value) || value < 1 || value > 10000) {
      setError("Informe um valor inteiro entre 1 e 10000 ml.");
      return;
    }
    const instant = consumedAt ? new Date(consumedAt) : null;
    if (
      instant &&
      (!Number.isFinite(instant.getTime()) ||
        instant.getTime() > Date.now() + 5 * 60 * 1000)
    ) {
      setError("Revise o horário. A tolerância de futuro é de cinco minutos.");
      return;
    }
    void mutate(
      "/student/water-records",
      "POST",
      {
        amount_ml: value,
        ...(instant ? { consumed_at: instant.toISOString() } : {}),
      },
      "Consumo registrado.",
    );
  }
  return (
    <div className="space-y-6 [overflow-wrap:anywhere]">
      {area !== "student" && (
        <Link href={base} className="text-sm text-primary underline">
          Voltar ao aluno
        </Link>
      )}
      <h1 className="text-2xl font-semibold">Hidratação</h1>
      <p className="text-sm text-muted-foreground">
        Registros de consumo e acompanhamento da meta definida pelo
        profissional.
      </p>
      {error && (
        <p
          id="hydration-error"
          role="alert"
          className="text-sm text-destructive"
        >
          {error}
        </p>
      )}
      {success && (
        <p role="status" className="text-sm text-primary">
          {success}
        </p>
      )}
      {resource.loading ? (
        <LoadingState />
      ) : resource.error ? (
        <ErrorState message={resource.error} retry={resource.reload} />
      ) : (
        resource.data && (
          <>
            <section className="space-y-4 rounded-lg border bg-white p-5">
              <h2 className="font-semibold">
                Água hoje · {displayDate(resource.data.date)}
              </h2>
              <HydrationProgress data={resource.data} />
              <p className="text-xs text-muted-foreground">
                Dia calculado em {resource.data.timezone}. A meta é atual; não
                representa uma recomendação automática.
              </p>
              {area === "professional" && (
                <button
                  type="button"
                  className="master-secondary"
                  disabled={busy}
                  onClick={() => {
                    setGoal(
                      resource.data?.goal_ml == null
                        ? ""
                        : String(resource.data.goal_ml / 1000),
                    );
                    setEditingGoal(!editingGoal);
                  }}
                >
                  Configurar meta
                </button>
              )}
              {editingGoal && (
                <form
                  className="space-y-3 border-t pt-4"
                  aria-busy={busy}
                  onSubmit={(event) => {
                    event.preventDefault();
                    void mutate(
                      base,
                      "PATCH",
                      { water_goal: goal === "" ? null : Number(goal) },
                      "Meta atualizada.",
                    );
                  }}
                >
                  <label className="block text-sm" htmlFor="hydration-goal">
                    Meta em litros/dia (opcional)
                  </label>
                  <input
                    id="hydration-goal"
                    className="auth-input"
                    type="number"
                    min={0}
                    step="any"
                    value={goal}
                    disabled={busy}
                    onChange={(event) => setGoal(event.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">
                    Deixe vazio para retirar a meta.
                  </p>
                  <button
                    className="master-primary"
                    type="submit"
                    disabled={busy}
                  >
                    Salvar meta
                  </button>
                </form>
              )}
            </section>
            {area === "student" && (
              <section className="space-y-5 rounded-lg border bg-white p-5">
                <h2 className="font-semibold">Registrar água</h2>
                <div className="flex flex-wrap gap-3">
                  {[250, 300, 500].map((value) => (
                    <button
                      key={value}
                      type="button"
                      disabled={busy}
                      className="master-primary min-h-11"
                      onClick={() =>
                        void mutate(
                          "/student/water-records",
                          "POST",
                          { amount_ml: value },
                          "Consumo registrado.",
                        )
                      }
                    >
                      + {value} ml
                    </button>
                  ))}
                </div>
                <form
                  onSubmit={register}
                  aria-busy={busy}
                  aria-describedby={error ? "hydration-error" : undefined}
                  className="space-y-4 border-t pt-4"
                >
                  <div className="grid gap-4 sm:grid-cols-2">
                    <label className="text-sm" htmlFor="water-amount">
                      Outro valor (ml)
                      <input
                        id="water-amount"
                        className="auth-input mt-2"
                        type="number"
                        inputMode="numeric"
                        required
                        min={1}
                        max={10000}
                        step={1}
                        value={amount}
                        onChange={(event) => setAmount(event.target.value)}
                        disabled={busy}
                      />
                    </label>
                    <label className="min-w-0 text-sm" htmlFor="water-time">
                      Horário real (opcional)
                      <input
                        id="water-time"
                        className="auth-input mt-2 min-w-0"
                        type="datetime-local"
                        value={consumedAt}
                        onChange={(event) => setConsumedAt(event.target.value)}
                        disabled={busy}
                      />
                    </label>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Sem horário, registra agora. O horário informado usa o fuso
                    do seu dispositivo. Os atalhos são apenas opções de
                    registro.
                  </p>
                  <button
                    className="master-primary min-h-11"
                    type="submit"
                    disabled={busy}
                  >
                    {busy ? "Salvando…" : "Registrar outro valor"}
                  </button>
                </form>
              </section>
            )}
            <section className="rounded-lg border bg-white p-5">
              <h2 className="font-semibold">Registros de hoje</h2>
              {!resource.data.records.length ? (
                <p className="mt-4 text-sm text-muted-foreground">
                  Nenhum consumo registrado hoje.
                </p>
              ) : (
                <ul className="mt-3 divide-y">
                  {resource.data.records.map((record) => (
                    <li
                      key={record.id}
                      className="flex justify-between gap-3 py-3 text-sm"
                    >
                      <time dateTime={record.consumed_at}>
                        {new Date(record.consumed_at).toLocaleTimeString(
                          "pt-BR",
                          {
                            timeZone: resource.data?.timezone,
                            hour: "2-digit",
                            minute: "2-digit",
                          },
                        )}
                      </time>
                      <span className="font-medium">
                        {volume(record.amount_ml)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
              {resource.data.total_records > 20 && (
                <div className="mt-3 flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    className="master-secondary"
                    disabled={page === 1}
                    onClick={() => setPage(page - 1)}
                  >
                    Anterior
                  </button>
                  <span className="text-sm">Página {page}</span>
                  <button
                    type="button"
                    className="master-secondary"
                    disabled={page * 20 >= resource.data.total_records}
                    onClick={() => setPage(page + 1)}
                  >
                    Próxima
                  </button>
                </div>
              )}
              <p className="mt-4 text-xs text-muted-foreground">
                Os registros não podem ser editados ou excluídos nesta versão.
              </p>
            </section>
          </>
        )
      )}
      <section className="min-w-0 space-y-5 rounded-lg border bg-white p-5">
        <h2 className="font-semibold">Histórico de consumo</h2>
        <label className="block text-sm" htmlFor="hydration-days">
          Período
          <select
            id="hydration-days"
            className="auth-input mt-2"
            value={days}
            onChange={(event) => setDays(Number(event.target.value))}
          >
            <option value={1}>Hoje</option>
            <option value={7}>Últimos 7 dias</option>
            <option value={30}>Últimos 30 dias</option>
          </select>
        </label>
        {history.loading ? (
          <LoadingState />
        ) : history.error ? (
          <ErrorState message={history.error} retry={history.reload} />
        ) : (
          history.data && <HydrationChart data={history.data} />
        )}
      </section>
    </div>
  );
}
