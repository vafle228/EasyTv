import { createContext, useContext, useId, useState } from "react";
import type { ReactNode } from "react";
import { api } from "./api";
import { usePolling } from "./hooks";
import type { Enhancement, EnhancementJob } from "./types";

const Context = createContext<{
  data: Enhancement | null;
  error: string | null;
  busy: boolean;
  configure: (enabled: boolean, streaming: boolean) => Promise<void>;
}>({ data: null, error: null, busy: false, configure: async () => {} });

export function EnhancementProvider({ children }: { children: ReactNode }) {
  const { data, error, reload } = usePolling(api.enhancement, 3000);
  const [busy, setBusy] = useState(false);
  const [saveError, setError] = useState<string | null>(null);
  const configure = async (enabled: boolean, streaming: boolean) => {
    setBusy(true);
    setError(null);
    try {
      await api.configureEnhancement(enabled, streaming);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };
  return <Context.Provider value={{ data, error: saveError ?? error, busy, configure }}>{children}</Context.Provider>;
}

export const useEnhancement = () => useContext(Context);

export function jobLabel(job: EnhancementJob) {
  if (job.state === "failed") return job.error ?? "Ошибка улучшения";
  if (job.state === "ready") return `ИИ: готово${job.height ? `, ${job.height}p` : ""}`;
  if (job.state === "pending") return "ИИ: ожидает обработки";
  if (job.state === "loading") return "ИИ: загружаю модель";
  if (job.state === "cancelled") return "ИИ: обработка отменена";
  const progress = job.progress == null ? "" : ` ${Math.round(job.progress * 100)}%`;
  return `ИИ: улучшаю${progress}${job.speed ? ` · ${job.speed.toFixed(2)}× скорости видео` : ""}`;
}

export function EnhancementControl() {
  const { data, error, busy, configure } = useEnhancement();
  const modeName = useId();
  return (
    <section className="ai-control" aria-label="ИИ улучшение видео">
      <label className="ai-control__toggle">
        <span><strong>ИИ улучшение</strong><small className="muted">До 1080p · RelayVSR</small></span>
        <input type="checkbox" role="switch" checked={data?.enabled ?? false}
          disabled={busy || !data || (!data.enabled && !data.available)}
          onChange={(e) => void configure(e.target.checked, data?.streaming ?? true)} />
      </label>
      {data?.enabled && <>
        <fieldset className="ai-control__mode" disabled={busy}>
          <legend>Запуск видео</legend>
          <div className="ai-control__choices">
            <label className="ai-control__choice">
              <input type="radio" name={modeName} checked={data.streaming}
                onChange={() => void configure(true, true)} />
              <span><strong>В потоке</strong><small>По мере улучшения</small></span>
            </label>
            <label className="ai-control__choice">
              <input type="radio" name={modeName} checked={!data.streaming}
                onChange={() => void configure(true, false)} />
              <span><strong>Готовый файл</strong><small>После обработки</small></span>
            </label>
          </div>
        </fieldset>
        <p className="small muted">144p, 240p, 360p, 480p, 720p и другие разрешения ниже Full HD улучшаются до 1080p с сохранением пропорций. Для 1080p и выше используется оригинал.</p>
        <p className="small muted">Следующие видео из очереди готовятся заранее. Настройка общая; на ТВ действует при новом запуске.</p>
        {data.streaming && <p className="small muted">В потоке возможны паузы; перемотка доступна после обработки. Если ТВ не запускает видео, выберите полную обработку.</p>}
      </>}
      {(error || data?.error) && <p className="video__error" role="status">{error ?? data?.error}</p>}
      {data?.enabled && data.jobs.filter((j) => !["ready", "cancelled"].includes(j.state)).slice(0, 3).map((job) => (
        <p key={job.id} className="small" role="status">{job.title ? `${job.title}: ` : ""}{jobLabel(job)}</p>
      ))}
    </section>
  );
}
