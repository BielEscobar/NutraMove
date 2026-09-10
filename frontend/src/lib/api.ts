const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export type User = {
  id: string;
  name: string;
  email: string;
  role: "MASTER" | "PROFESSIONAL" | "STUDENT";
  is_active: boolean;
  created_at: string;
};

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...options,
      credentials: "include",
      cache: "no-store",
      headers: { "Content-Type": "application/json", ...options.headers },
    });
  } catch {
    throw new ApiError(0, "Não foi possível conectar à API. Tente novamente.");
  }
  if (!response.ok) {
    const message =
      response.status === 401
        ? "E-mail ou senha inválidos, ou sessão expirada."
        : response.status === 403
          ? "Acesso não permitido. Verifique a configuração de origem da aplicação."
          : "Não foi possível concluir a solicitação. Tente novamente.";
    throw new ApiError(response.status, message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
