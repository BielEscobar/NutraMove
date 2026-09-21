import { Clock3, Dumbbell } from "lucide-react";
import type { WorkoutContent } from "@/lib/workouts";

export function WorkoutReader({ workout }: { workout: WorkoutContent }) {
  // Read-only snapshots remount on version/revision changes; no child IDs are exposed.
  const days = workout.days.map((day, position) => ({
    ...day,
    snapshotKey: `day-${position}`,
    exercises: day.exercises.map((exercise, index) => ({
      ...exercise,
      snapshotKey: `exercise-${index}`,
    })),
  }));
  return (
    <div className="space-y-6 [overflow-wrap:anywhere]">
      <section className="rounded-lg border bg-white p-5">
        <p className="mb-3 flex items-center gap-2 text-sm text-primary">
          <Dumbbell className="size-5" aria-hidden="true" />
          Plano de treino
        </p>
        <h1 className="text-2xl font-semibold">{workout.name}</h1>
        {workout.goal && (
          <p className="mt-2 text-muted-foreground">{workout.goal}</p>
        )}
        <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-3">
          {workout.frequency_per_week !== null && (
            <div>
              <dt className="text-muted-foreground">Frequência semanal</dt>
              <dd className="mt-1 font-medium">
                {workout.frequency_per_week} dias/semana
              </dd>
            </div>
          )}
          {workout.start_date && (
            <div>
              <dt className="text-muted-foreground">Início</dt>
              <dd className="mt-1">
                {workout.start_date.split("-").reverse().join("/")}
              </dd>
            </div>
          )}
          {workout.next_review_date && (
            <div>
              <dt className="text-muted-foreground">Próxima atualização</dt>
              <dd className="mt-1">
                {workout.next_review_date.split("-").reverse().join("/")}
              </dd>
            </div>
          )}
        </dl>
        {workout.notes && (
          <div className="mt-5 border-t pt-4">
            <h2 className="font-medium">Orientações</h2>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-6">
              {workout.notes}
            </p>
          </div>
        )}
      </section>
      {days.length === 0 && (
        <p className="rounded-lg border border-dashed p-5">
          Nenhuma divisão adicionada a esta versão.
        </p>
      )}
      {days.map((day) => (
        <section
          key={day.snapshotKey}
          className="overflow-hidden rounded-lg border bg-white"
        >
          <header className="border-b bg-secondary/60 p-5">
            <h2 className="text-xl font-semibold text-brand-deep">
              {day.name}
            </h2>
            {day.description && (
              <p className="mt-2 whitespace-pre-wrap text-sm leading-6">
                {day.description}
              </p>
            )}
            {day.isRest && (
              <p className="mt-2 text-sm font-medium text-primary">
                Dia de descanso
              </p>
            )}
          </header>
          <ol className="divide-y px-5">
            {day.exercises.map((exercise, index) => (
              <li key={exercise.snapshotKey} className="py-5">
                <h3 className="text-lg font-semibold">
                  {index + 1}. {exercise.name}
                </h3>
                {exercise.muscle_group && (
                  <p className="mt-1 text-sm text-muted-foreground">
                    {exercise.muscle_group}
                  </p>
                )}
                <dl className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
                  {exercise.sets !== null && (
                    <div>
                      <dt className="text-xs text-muted-foreground">Séries</dt>
                      <dd className="mt-1 text-lg font-semibold text-primary">
                        {exercise.sets}
                      </dd>
                    </div>
                  )}
                  {exercise.repetitions && (
                    <div>
                      <dt className="text-xs text-muted-foreground">
                        Repetições
                      </dt>
                      <dd className="mt-1 text-lg font-semibold text-primary">
                        {exercise.repetitions}
                      </dd>
                    </div>
                  )}
                  {exercise.load && (
                    <div>
                      <dt className="text-xs text-muted-foreground">Carga</dt>
                      <dd className="mt-1 font-medium">{exercise.load}</dd>
                    </div>
                  )}
                  {exercise.rest_seconds !== null && (
                    <div>
                      <dt className="flex items-center gap-1 text-xs text-muted-foreground">
                        <Clock3 className="size-3" aria-hidden="true" />
                        Descanso
                      </dt>
                      <dd className="mt-1 font-medium">
                        {exercise.rest_seconds} s
                      </dd>
                    </div>
                  )}
                  {exercise.duration && (
                    <div>
                      <dt className="text-xs text-muted-foreground">
                        Duração / tempo
                      </dt>
                      <dd className="mt-1 font-medium">{exercise.duration}</dd>
                    </div>
                  )}
                </dl>
                {(exercise.description ||
                  exercise.instructions ||
                  exercise.notes) && (
                  <details className="mt-4 rounded-md bg-secondary/40 px-3">
                    <summary className="min-h-11 cursor-pointer py-3 text-sm font-medium">
                      Instruções e observações
                    </summary>
                    <div className="space-y-3 pb-4 text-sm leading-6">
                      {exercise.description && (
                        <p className="whitespace-pre-wrap">
                          {exercise.description}
                        </p>
                      )}
                      {exercise.instructions && (
                        <p className="whitespace-pre-wrap">
                          {exercise.instructions}
                        </p>
                      )}
                      {exercise.notes && (
                        <p className="whitespace-pre-wrap">{exercise.notes}</p>
                      )}
                    </div>
                  </details>
                )}
              </li>
            ))}
          </ol>
        </section>
      ))}
    </div>
  );
}
