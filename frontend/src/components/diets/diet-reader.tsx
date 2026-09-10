/* biome-ignore-all lint/suspicious/noArrayIndexKey: Read-only ordered snapshots have no child IDs. The parent remounts this reader on version/revision changes; the editable form uses stable UUID keys. */
import { Clock3 } from "lucide-react";
import type { DietContent } from "@/lib/diets";

function dateLabel(value: string | null) {
  return value
    ? new Date(`${value}T12:00:00`).toLocaleDateString("pt-BR")
    : "Não informado";
}
export function DietReader({ diet }: { diet: DietContent }) {
  return (
    <div className="space-y-5">
      <section className="rounded-lg border bg-white p-5">
        <h1 className="break-words text-2xl font-semibold">{diet.name}</h1>
        {diet.goal && (
          <p className="mt-3 whitespace-pre-wrap break-words text-sm text-muted-foreground">
            {diet.goal}
          </p>
        )}
        <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-muted-foreground">Início</dt>
            <dd className="mt-1">{dateLabel(diet.start_date)}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Próxima atualização</dt>
            <dd className="mt-1">{dateLabel(diet.next_review_date)}</dd>
          </div>
        </dl>
        {diet.notes && (
          <div className="mt-5 border-t pt-4">
            <h2 className="text-sm font-medium">Orientações</h2>
            <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-6">
              {diet.notes}
            </p>
          </div>
        )}
      </section>
      {diet.meals.length === 0 && (
        <p className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
          Nenhuma refeição adicionada a esta versão.
        </p>
      )}
      {diet.meals.map((meal, index) => (
        <section
          key={`${index}-${meal.name}`}
          className="rounded-lg border bg-white p-5"
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="break-words text-lg font-semibold">{meal.name}</h2>
            {meal.time && (
              <span className="flex items-center gap-2 text-sm text-primary">
                <Clock3 className="size-4" aria-hidden="true" />
                {meal.time.slice(0, 5)}
              </span>
            )}
          </div>
          <ul className="mt-3 divide-y">
            {meal.foods.map((food, foodIndex) => (
              <li key={`${foodIndex}-${food.name}`} className="py-4">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <h3 className="min-w-0 break-words font-medium">
                    {food.name}
                  </h3>
                  <p className="break-words text-sm text-primary">
                    {Number(food.quantity).toLocaleString("pt-BR", {
                      maximumFractionDigits: 3,
                    })}{" "}
                    {food.unit}
                  </p>
                </div>
                {food.notes && (
                  <p className="mt-2 whitespace-pre-wrap break-words text-sm text-muted-foreground">
                    {food.notes}
                  </p>
                )}
                {food.substitutions.length > 0 && (
                  <details className="mt-3 rounded-md bg-secondary/60 px-3">
                    <summary className="min-h-11 cursor-pointer py-3 text-sm font-medium">
                      Substituições ({food.substitutions.length})
                    </summary>
                    <ul className="space-y-3 pb-4">
                      {food.substitutions.map((item, subIndex) => (
                        <li
                          key={`${subIndex}-${item.name}`}
                          className="text-sm"
                        >
                          <p className="break-words">
                            {item.name}
                            {item.quantity !== null && (
                              <>
                                {" "}
                                ·{" "}
                                {Number(item.quantity).toLocaleString("pt-BR", {
                                  maximumFractionDigits: 3,
                                })}{" "}
                                {item.unit}
                              </>
                            )}
                          </p>
                          {item.notes && (
                            <p className="mt-1 whitespace-pre-wrap break-words text-muted-foreground">
                              {item.notes}
                            </p>
                          )}
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
