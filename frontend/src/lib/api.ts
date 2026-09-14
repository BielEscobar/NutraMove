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
    const messages: Record<number, string> = {
      401: "Sessão expirada ou credenciais inválidas. Entre novamente.",
      403: "Você não tem permissão para realizar esta ação.",
      404: "Registro não encontrado.",
      409:
        path.startsWith("/master/professionals") ||
        path === "/students/register"
          ? "E-mail já cadastrado. Informe outro e-mail."
          : "A situação do cadastro não permite esta ação. Atualize os dados.",
      422: "Revise os campos informados e tente novamente.",
      429: "Muitas tentativas. Aguarde alguns minutos e tente novamente.",
    };
    if (response.status === 409 && path.includes("/reevaluation-requests")) {
      const body: unknown = await response.json().catch(() => null);
      if (
        body &&
        typeof body === "object" &&
        "error" in body &&
        body.error &&
        typeof body.error === "object" &&
        "message" in body.error &&
        typeof body.error.message === "string"
      ) {
        throw new ApiError(409, body.error.message);
      }
    }
    throw new ApiError(
      response.status,
      messages[response.status] ??
        "Não foi possível concluir a solicitação. Tente novamente.",
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
