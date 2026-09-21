"use client";

import { useState } from "react";
import { ErrorState, LoadingState } from "@/components/master/resource-state";
import type { Area } from "@/lib/evolution";
import { useApiResource } from "@/lib/use-api-resource";

type Photo = {
  id: string;
  position: "FRONT" | "SIDE";
  mime_type: string;
  byte_size: number;
};
type Set = {
  id: string;
  source: "INITIAL" | "REEVALUATION";
  context: string | null;
  captured_at: string;
  photos: Photo[];
};
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function AuthorizedPhotoEvolution({
  area,
  studentId,
}: {
  area: "student" | "professional";
  studentId?: string;
}) {
  const base =
    area === "student"
      ? "/student/progress-photos"
      : `/professional/students/${studentId}/progress-photos`;
  const resource = useApiResource<Set[]>(base);
  const [selected, setSelected] = useState<string[]>([]);
  if (resource.loading) return <LoadingState />;
  if (resource.error)
    return <ErrorState message={resource.error} retry={resource.reload} />;
  const items = resource.data ?? [];
  const visible =
    selected.length === 2
      ? items.filter((item) => selected.includes(item.id))
      : items;
  return (
    <section className="space-y-4 rounded-lg border bg-white p-5">
      <div>
        <h2 className="text-lg font-semibold">Evolução fotográfica</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Histórico privado. Selecione duas datas para comparar lado a lado.
        </p>
      </div>
      {!items.length ? (
        <p className="text-sm text-muted-foreground">
          Nenhum conjunto de fotos registrado.
        </p>
      ) : (
        <>
          <div className="flex flex-wrap gap-2">
            {items.map((item) => (
              <label
                key={item.id}
                className="flex min-h-11 items-center gap-2 rounded-md border px-3 text-sm"
              >
                <input
                  type="checkbox"
                  checked={selected.includes(item.id)}
                  disabled={
                    !selected.includes(item.id) && selected.length === 2
                  }
                  onChange={() =>
                    setSelected((value) =>
                      value.includes(item.id)
                        ? value.filter((id) => id !== item.id)
                        : [...value, item.id],
                    )
                  }
                />
                {new Date(item.captured_at).toLocaleDateString("pt-BR")}
              </label>
            ))}
          </div>
          <div className="grid gap-5 lg:grid-cols-2">
            {visible.map((item) => (
              <article key={item.id} className="rounded-md border p-4">
                <h3 className="font-medium">
                  {new Date(item.captured_at).toLocaleDateString("pt-BR")} ·{" "}
                  {item.source === "INITIAL"
                    ? "Cadastro inicial"
                    : "Reavaliação"}
                </h3>
                <div className="mt-3 grid grid-cols-2 gap-3">
                  {item.photos.map((photo) => (
                    <figure key={photo.id}>
                      {/* biome-ignore lint/performance/noImgElement: private authenticated images cannot use the public optimizer */}
                      <img
                        className="aspect-[3/4] w-full rounded-md bg-secondary object-contain"
                        src={`${API}${base}/${photo.id}/content`}
                        alt={
                          photo.position === "FRONT"
                            ? "Foto corporal frontal"
                            : "Foto corporal lateral"
                        }
                      />
                      <figcaption className="mt-1 text-center text-xs">
                        {photo.position === "FRONT" ? "Frontal" : "Lateral"}
                      </figcaption>
                    </figure>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </>
      )}
    </section>
  );
}

export function PhotoEvolution({
  area,
  studentId,
}: {
  area: Area;
  studentId?: string;
}) {
  if (area === "master")
    return (
      <section className="rounded-lg border bg-white p-5">
        <h2 className="text-lg font-semibold">Evolução fotográfica</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          O perfil MASTER não visualiza fotos corporais para minimizar o acesso
          a dados privados.
        </p>
      </section>
    );
  return <AuthorizedPhotoEvolution area={area} studentId={studentId} />;
}
