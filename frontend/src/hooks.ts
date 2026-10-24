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
