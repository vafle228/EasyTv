import { useRef, useState } from "react";
import type { DragEvent } from "react";
import { api } from "../api";
import { formatSize } from "../format";
import type { Video } from "../types";
import { AddField } from "./AddField";
import { Icon } from "./Icons";

interface Props {
  videos: Video[] | null;
  playingId: string | null;
  canPlay: boolean;
  onPlay: (video: Video) => Promise<void>;
  onChanged: () => void;
  onError: (message: string) => void;
}

interface UploadState {
  name: string;
  progress: number;
}

type Filter = "all" | "cinema" | "youtube" | "upload" | "live";

const FILTERS: { value: Filter; label: string }[] = [
  { value: "all", label: "Всё" },
  { value: "cinema", label: "Кинотеатр" },
  { value: "youtube", label: "YouTube" },
  { value: "upload", label: "Файлы" },
  { value: "live", label: "Эфир" },
];

export function Library({ videos, playingId, canPlay, onPlay, onChanged, onError }: Props) {
  const [uploads, setUploads] = useState<UploadState[]>([]);
  const [dragging, setDragging] = useState(false);
  const [starting, setStarting] = useState<string | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [query, setQuery] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);

  const uploadFiles = async (files: FileList | File[]) => {
    for (const file of Array.from(files)) {
      setUploads((u) => [...u, { name: file.name, progress: 0 }]);
      try {
        await api.upload(file, (p) =>
          setUploads((u) => u.map((x) => (x.name === file.name ? { ...x, progress: p } : x))),
        );
        onChanged();
      } catch (e) {
        onError(`${file.name}: ${e instanceof Error ? e.message : e}`);
      } finally {
        setUploads((u) => u.filter((x) => x.name !== file.name));
      }
    }
  };

  const remove = async (video: Video, ask: boolean) => {
    if (ask && !window.confirm(`Удалить «${video.title}» из библиотеки?`)) return;
    try {
      await api.deleteVideo(video.id);
      onChanged();
    } catch (e) {
      onError(e instanceof Error ? e.message : String(e));
    }
  };

  const play = async (video: Video) => {
    setStarting(video.id);
    try {
      await onPlay(video);
    } finally {
      setStarting(null);
    }
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files.length) void uploadFiles(e.dataTransfer.files);
  };

  const q = query.trim().toLowerCase();
  const shown = videos?.filter(
    (v) => (filter === "all" || filter === v.source) && (!q || v.title.toLowerCase().includes(q)),
  );

  return (
    <section className="card" aria-labelledby="library-title">
      <h2 id="library-title" className="label">
        Что показать
      </h2>

      <div style={{ marginTop: 18 }}>
        <AddField onAdded={onChanged} onError={onError} />
      </div>
      <div
        className={`drop ${dragging ? "drop--over" : ""}`}
        style={{ marginTop: 18 }}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <button className="btn" onClick={() => fileInput.current?.click()}>
          <Icon name="upload" />
          Выбрать файл на компьютере
        </button>
        <span className="muted small">или перетащите сюда видео (mp4, mkv, avi, mov)</span>
        <input
          ref={fileInput}
          type="file"
          accept="video/*,.mkv,.avi,.ts,.m2ts"
          multiple
          hidden
          onChange={(e) => {
            if (e.target.files?.length) void uploadFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      <div className="row row--between" style={{ margin: "28px 0 18px" }}>
        <div className="segmented" role="radiogroup" aria-label="Что показывать в списке">
          {FILTERS.map((f) => (
            <button
              key={f.value}
              className="segmented__item"
              role="radio"
              aria-checked={filter === f.value}
              onClick={() => setFilter(f.value)}
            >
              {f.label}
            </button>
          ))}
        </div>
        <label className="field" style={{ flex: "0 1 320px", minHeight: 46 }}>
          <Icon name="search" />
          <input
            type="text"
            placeholder="Найти в библиотеке"
            aria-label="Найти в библиотеке"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
      </div>

      <ul className="videos">
        {uploads.map((u) => (
          <li key={`up-${u.name}`} className="video">
            <span className="video__badge">
              <Icon name="upload" />
            </span>
            <div className="video__main">
              <span className="video__title">{u.name}</span>
              <span className="video__meta">Загружаю на сервер, {Math.round(u.progress * 100)}%</span>
              <div className="meter meter--thin">
                <span className="meter__fill" style={{ width: `${u.progress * 100}%` }} />
              </div>
            </div>
          </li>
        ))}

        {shown?.length === 0 && uploads.length === 0 && (
          <li className="videos__empty muted">
            {videos?.length === 0
              ? "Библиотека пуста. Выберите файл на компьютере или вставьте ссылку на YouTube."
              : filter === "cinema" || filter === "live"
                ? "Этот раздел появится в следующей версии."
                : "Ничего не нашлось."}
          </li>
        )}

        {shown?.map((v) => {
          const current = v.id === playingId;
          const loading = v.status === "downloading" || v.status === "pending";
          return (
            <li key={v.id} className={`video ${current ? "video--current" : ""}`}>
              <span className={`video__badge video__badge--${v.source}`}>
                <Icon name={v.source === "youtube" ? "youtube" : "file"} />
              </span>
              <div className="video__main">
                <span className="video__title" title={v.title}>
                  {v.title}
                </span>
                <span className="video__meta">{describe(v, current)}</span>
                {loading && (
                  <div className="meter meter--thin">
                    <span className="meter__fill" style={{ width: `${v.progress * 100}%` }} />
                  </div>
                )}
                {v.status === "failed" && <span className="video__error">{v.error ?? "Не удалось скачать"}</span>}
              </div>
              <div className="video__actions">
                {v.status === "ready" && (
                  <button
                    className="btn btn--primary btn--small"
                    onClick={() => play(v)}
                    disabled={!canPlay || starting !== null}
                    title={canPlay ? undefined : "Телевизор не в сети"}
                  >
                    <Icon name="play" />
                    {starting === v.id ? "Запускаю…" : current ? "Сначала" : "Показать"}
                  </button>
                )}
                {loading ? (
                  <button className="icon-btn" onClick={() => remove(v, false)} aria-label="Отменить загрузку">
                    <Icon name="close" />
                  </button>
                ) : (
                  <button className="icon-btn" onClick={() => remove(v, true)} aria-label={`Удалить ${v.title}`}>
                    <Icon name="trash" />
                  </button>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

export function describe(v: Video, playing = false): string {
  const source = v.source === "youtube" ? "YouTube" : "С компьютера";
  switch (v.status) {
    case "pending":
      return `${source}, в очереди`;
    case "downloading":
      return `${source}, скачиваю ${Math.round(v.progress * 100)}%`;
    case "failed":
      return `${source}, ошибка`;
    default:
      return [source, formatSize(v.size), playing ? "сейчас на экране" : ""].filter(Boolean).join(", ");
  }
}
