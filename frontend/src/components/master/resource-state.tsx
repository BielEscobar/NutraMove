import { LoaderCircle } from "lucide-react";

export function LoadingState() {
  return (
    <p
      role="status"
      className="flex items-center gap-2 py-8 text-sm text-muted-foreground"
    >
      <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />{" "}
      Carregando…
    </p>
  );
}

export function ErrorState({
  message,
  retry,
}: {
  message: string;
  retry: () => void;
}) {
  return (
    <div
      role="alert"
      className="rounded-lg border border-destructive/30 bg-white p-5"
    >
      <p className="text-sm text-destructive">{message}</p>
      <button
        type="button"
        onClick={retry}
        className="mt-3 min-h-11 px-2 text-sm font-medium underline"
      >
        Tentar novamente
      </button>
    </div>
  );
}
