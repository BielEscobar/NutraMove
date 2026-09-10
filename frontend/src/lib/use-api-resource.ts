"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, apiRequest } from "@/lib/api";

export function useApiResource<T>(path: string) {
  const router = useRouter();
  const controller = useRef<AbortController | null>(null);
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    controller.current?.abort();
    const request = new AbortController();
    controller.current = request;
    setLoading(true);
    setError("");
    try {
      const result = await apiRequest<T>(path, { signal: request.signal });
      if (!request.signal.aborted) setData(result);
    } catch (cause) {
      if (request.signal.aborted) return;
      setData(null);
      if (cause instanceof ApiError && cause.status === 401)
        router.replace("/login");
      else if (cause instanceof ApiError && cause.status === 403)
        router.replace("/account");
      else
        setError(
          cause instanceof Error
            ? cause.message
            : "Não foi possível carregar os dados.",
        );
    } finally {
      if (!request.signal.aborted) setLoading(false);
    }
  }, [path, router]);

  useEffect(() => {
    void reload();
    return () => controller.current?.abort();
  }, [reload]);

  return { data, loading, error, reload };
}
