export function StatusBadge({ active }: { active: boolean }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium ${active ? "bg-brand-mint/30 text-brand-deep" : "bg-secondary text-muted-foreground"}`}
    >
      <span
        className={`size-1.5 rounded-full ${active ? "bg-primary" : "bg-muted-foreground"}`}
        aria-hidden="true"
      />
      {active ? "Ativo" : "Inativo"}
    </span>
  );
}
