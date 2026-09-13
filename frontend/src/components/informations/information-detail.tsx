"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useRef, useState } from "react";
import { ErrorState, LoadingState } from "@/components/master/resource-state";
import { ApiError, apiRequest } from "@/lib/api";
import {
  type Information,
  type InformationCategory,
  informationCategories,
  informationStatuses,
} from "@/lib/informations";
import type { StudentList } from "@/lib/students";
import { useApiResource } from "@/lib/use-api-resource";

export function InformationDetailPage({
  area,
  id,
}: {
  area: "professional" | "student" | "master";
  id?: string;
}) {
  const isNew = id === undefined;
  const router = useRouter();
  const resource = useApiResource<Information>(
    isNew ? null : `/${area}/informations/${id}`,
  );
  const [studentQuery, setStudentQuery] = useState("");
  const students = useApiResource<StudentList>(
    area === "professional"
      ? `/professional/students?status=ACTIVE&page_size=20&q=${encodeURIComponent(studentQuery)}`
      : null,
  );
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [category, setCategory] = useState<InformationCategory>("INFO");
  const [studentId, setStudentId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const guard = useRef(false);
  const [editing, setEditing] = useState(false);
  const record = resource.data;
  async function action(
    kind: "save" | "publish" | "archive" | "create_publish",
    event?: FormEvent<HTMLFormElement>,
  ) {
    event?.preventDefault();
    if (guard.current) return;
    guard.current = true;
    setBusy(true);
    setError("");
    setSuccess("");
    try {
      const payload = {
        title: title.trim(),
        content: content.trim(),
        category,
        student_id: studentId || null,
      };
      if (isNew && (kind === "save" || kind === "create_publish")) {
        const created = await apiRequest<Information>(
          "/professional/informations",
          { method: "POST", body: JSON.stringify(payload) },
        );
        if (kind === "create_publish") {
          await apiRequest(`/professional/informations/${created.id}/publish`, {
            method: "POST",
            body: JSON.stringify({ expected_revision: created.edit_revision }),
          });
        }
        router.push(`/professional/informations/${created.id}`);
        return;
      }
      if (!record) return;
      if (kind === "save") {
        await apiRequest(`/professional/informations/${record.id}`, {
          method: "PATCH",
          body: JSON.stringify({
            ...payload,
            expected_revision: record.edit_revision,
          }),
        });
        setSuccess("Rascunho salvo.");
        setEditing(false);
      } else {
        await apiRequest(`/professional/informations/${record.id}/${kind}`, {
          method: "POST",
          body: JSON.stringify({ expected_revision: record.edit_revision }),
        });
        setSuccess(
          kind === "publish"
            ? "Informativo publicado."
            : "Informativo arquivado.",
        );
      }
      await resource.reload();
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
  const form =
    area === "professional" &&
    (isNew || (record?.status === "DRAFT" && editing));
  if (!isNew && resource.loading) return <LoadingState />;
  if (!isNew && resource.error)
    return <ErrorState message={resource.error} retry={resource.reload} />;
  if (!isNew && !record) return null;
  return (
    <div className="max-w-3xl space-y-6 [overflow-wrap:anywhere]">
      <Link
        className="text-sm text-primary underline"
        href={`/${area}/informations`}
      >
        Voltar aos informativos
      </Link>
      <h1 className="text-2xl font-semibold">
        {isNew ? "Novo informativo" : record?.title}
      </h1>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      {success && (
        <p role="status" className="text-sm text-primary">
          {success}
        </p>
      )}
      {form ? (
        <form
          className="space-y-5 rounded-lg border bg-white p-5"
          onSubmit={(e) => void action("save", e)}
          aria-busy={busy}
        >
          <label className="block text-sm">
            Título
            <input
              className="auth-input mt-2"
              required
              minLength={3}
              maxLength={160}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </label>
          <label className="block text-sm">
            Categoria
            <select
              className="auth-input mt-2"
              value={category}
              onChange={(e) =>
                setCategory(e.target.value as InformationCategory)
              }
            >
              {Object.entries(informationCategories).map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm">
            Buscar aluno da minha carteira
            <input
              className="auth-input mt-2"
              value={studentQuery}
              onChange={(e) => setStudentQuery(e.target.value)}
              maxLength={120}
              placeholder="Digite o nome"
            />
          </label>
          <label className="block text-sm">
            Destinatário
            <select
              className="auth-input mt-2"
              value={studentId}
              onChange={(e) => setStudentId(e.target.value)}
            >
              <option value="">Todos os meus alunos</option>
              {studentId &&
                !students.data?.items.some(
                  (student) => student.id === studentId,
                ) && <option value={studentId}>Aluno selecionado</option>}
              {students.data?.items.map((student) => (
                <option key={student.id} value={student.id}>
                  {student.name}
                </option>
              ))}
            </select>
          </label>
          {students.error && (
            <ErrorState message={students.error} retry={students.reload} />
          )}
          <label className="block text-sm">
            Conteúdo
            <textarea
              className="auth-input mt-2 min-h-52"
              required
              minLength={10}
              maxLength={10000}
              value={content}
              onChange={(e) => setContent(e.target.value)}
            />
          </label>
          <div className="flex flex-wrap gap-3">
            <button
              className="master-primary min-h-11"
              disabled={busy || !!students.error}
              type="submit"
            >
              Salvar rascunho
            </button>
            {isNew && (
              <button
                className="master-secondary min-h-11"
                disabled={busy || !!students.error}
                type="button"
                onClick={() => void action("create_publish")}
              >
                Publicar
              </button>
            )}
            {!isNew && (
              <button
                type="button"
                className="master-secondary min-h-11"
                onClick={() => setEditing(false)}
              >
                Cancelar
              </button>
            )}
          </div>
        </form>
      ) : (
        record && (
          <article className="space-y-4 rounded-lg border bg-white p-5">
            <div className="flex flex-wrap gap-2 text-xs">
              <span className="rounded-full bg-secondary px-3 py-1">
                {informationCategories[record.category]}
              </span>
              {record.status && (
                <span className="rounded-full bg-secondary px-3 py-1">
                  {informationStatuses[record.status]}
                </span>
              )}
            </div>
            <p className="text-xs text-muted-foreground">
              {record.published_at
                ? `Publicado em ${new Date(record.published_at).toLocaleDateString("pt-BR")}`
                : "Ainda não publicado"}
            </p>
            <div className="whitespace-pre-wrap text-sm leading-7">
              {record.content}
            </div>
            {area === "professional" && (
              <div className="flex flex-wrap gap-3 border-t pt-4">
                {record.status === "DRAFT" && (
                  <>
                    <button
                      className="master-secondary min-h-11"
                      type="button"
                      onClick={() => {
                        setTitle(record.title);
                        setContent(record.content);
                        setCategory(record.category);
                        setStudentId(record.student_id || "");
                        setEditing(true);
                      }}
                    >
                      Editar
                    </button>
                    <button
                      className="master-primary min-h-11"
                      disabled={busy}
                      type="button"
                      onClick={() => void action("publish")}
                    >
                      Publicar
                    </button>
                  </>
                )}
                {record.status !== "ARCHIVED" && (
                  <button
                    className="master-secondary min-h-11"
                    disabled={busy}
                    type="button"
                    onClick={() => void action("archive")}
                  >
                    Arquivar
                  </button>
                )}
              </div>
            )}
          </article>
        )
      )}
    </div>
  );
}
