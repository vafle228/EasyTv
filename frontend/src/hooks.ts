import { useCallback, useEffect, useRef, useState } from "react";

/** Calls `load` now and then every `intervalMs`; `reload()` forces an immediate refresh. */
export function usePolling<T>(load: () => Promise<T>, intervalMs: number, key: string = "") {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const loadRef = useRef(load);
  loadRef.current = load;
  const tick = useRef<() => Promise<void>>(async () => {});

  useEffect(() => {
    let alive = true;
    let timer: number | undefined;
    setData(null);
    setError(null);

    const run = async () => {
      window.clearTimeout(timer);
      try {
        const value = await loadRef.current();
        if (!alive) return;
        setData(value);
        setError(null);
      } catch (e) {
        if (alive) setError(e instanceof Error ? e.message : String(e));
      }
      if (alive) timer = window.setTimeout(run, intervalMs);
    };
    tick.current = run;
    void run();
    return () => {
      alive = false;
      window.clearTimeout(timer);
    };
  }, [intervalMs, key]);

  const reload = useCallback(() => tick.current(), []);
  return { data, error, reload, setData };
}

/** Loads once per `key` (no polling). `reload()` fetches again; `setData` lets callers patch the result. */
export function useLoad<T>(load: () => Promise<T>, key: string) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const loadRef = useRef(load);
  loadRef.current = load;
  const run = useRef<() => Promise<void>>(async () => {});

  useEffect(() => {
    let alive = true;
    run.current = async () => {
      setLoading(true);
      setError(null);
      try {
        const value = await loadRef.current();
        if (alive) setData(value);
      } catch (e) {
        if (alive) setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (alive) setLoading(false);
      }
    };
    setData(null);
    void run.current();
    return () => {
      alive = false;
    };
  }, [key]);

  const reload = useCallback(() => run.current(), []);
  return { data, error, loading, reload, setData };
}
