import { Leaf } from "lucide-react";

export default function Home() {
  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <div className="flex items-center gap-3">
        <Leaf className="size-8 text-primary" aria-hidden="true" />
        <h1 className="text-3xl font-semibold tracking-tight">NUTRAMOVE</h1>
      </div>
    </main>
  );
}
