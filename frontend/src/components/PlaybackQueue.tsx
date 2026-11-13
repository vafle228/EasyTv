import type { PlaybackQueue as Queue } from "../types";
import { Icon } from "./Icons";
import { jobLabel, useEnhancement } from "../enhancement";

export function PlaybackQueue({
  queue,
  error,
  busy,
  onRemove,
}: {
  queue: Queue | null;
  error: string | null;
  busy: boolean;
  onRemove: (itemId: string) => void;
}) {
  const ai = useEnhancement();
  return (
    <section className="card" aria-label="Очередь просмотра">
      <div className="section-head">
        <h2 className="label">Дальше</h2>
        {!!queue?.items.length && <span className="muted small">{queue.items.length}</span>}
      </div>
      {error && <p className="video__error" role="status">{error}</p>}
      {queue?.error && <p className="video__error" role="status">{queue.error}</p>}
      {!queue && !error && <p className="muted small">Загружаю очередь…</p>}
      {queue?.items.length === 0 && (
        <p className="muted small">Очередь пуста. Добавьте видео из библиотеки или серию из каталога.</p>
      )}
      {!!queue?.items.length && (
        <ol className="videos queue-items">
          {queue.items.map((item, index) => (
            <li key={item.id} className="row queue-item">
              <span className="muted small" aria-hidden="true">{index + 1}</span>
              <span className="grow">
                <span className="video__title" title={item.title}>{item.title}</span>
                {ai.data?.enabled && (() => {
                  const ref = item.stream;
                  const key = item.videoId ? `video:${item.videoId}` : ref
                    ? `stream:/stream/animego/${encodeURIComponent(ref.titleId)}/${ref.episode}/${encodeURIComponent(ref.translationId)}/${ref.provider ?? "auto"}.mp4` : "";
                  const job = ai.data.jobs.find((value) => value.key === key);
                  return <span className="video__meta">{job ? jobLabel(job) : "ИИ: подготовлю перед просмотром"}</span>;
                })()}
              </span>
              <button
                className="icon-btn"
                onClick={() => onRemove(item.id)}
                aria-label={`Убрать ${item.title} из очереди`}
                disabled={busy}
              >
                <Icon name="trash" />
              </button>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
