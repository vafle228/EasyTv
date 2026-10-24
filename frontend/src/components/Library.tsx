import { useRef, useState } from "react";
import type { DragEvent, FormEvent } from "react";
import { api } from "../api";
import { formatSize } from "../format";
import type { Video } from "../types";
import { FileIcon, PlayIcon, TrashIcon, UploadIcon, YoutubeIcon } from "./Icons";

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

export function Library({ videos, playingId, canPlay, onPlay, onChanged, onError }: Props) {
  const [uploads, setUploads] = useState<UploadState[]>([]);
  const [url, setUrl] = useState("");
  const [adding, setAdding] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [starting, setStarting] = useState<string | null>(null);
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

  const addYoutube = async (e: FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;
    setAdding(true);
    try {
      await api.addYoutube(url.trim());
      setUrl("");
      onChanged();
    } catch (err) {
      onError(err instanceof Error ? err.message : String(err));
    } finally {
      setAdding(false);
    }
  };

  const remove = async (video: Video) => {
    if (!window.confirm(`Удалить «${video.title}» из библиотеки?`)) return;
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

  return (
    <section className="card" aria-labelledby="library-title">
      <h2 id="library-title" className="label">
        Что показать
      </h2>

      <div className="sources">
        <div
          className={`drop ${dragging ? "drop--over" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
        >
          <button className="btn" onClick={() => fileInput.current?.click()}>
            <UploadIcon />
            Выбрать файл на компьютере
          </button>
          <span className="muted small">или перетащите сюда mp4, mkv, avi, mov</span>
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

        <form className="yt" onSubmit={addYoutube}>
          <label className="field">
            <YoutubeIcon />
            <input
              type="url"
              inputMode="url"
              placeholder="Ссылка на ролик YouTube"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              aria-label="Ссылка на ролик YouTube"
            />
          </label>
          <button className="btn btn--primary" type="submit" disabled={adding || !url.trim()}>
            {adding ? "Добавляю…" : "Скачать"}
          </button>
        </form>
      </div>

      <ul className="videos">
        {uploads.map((u) => (
          <li key={`up-${u.name}`} className="video">
            <span className="video__badge">
              <UploadIcon />
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

        {videos?.length === 0 && uploads.length === 0 && (
          <li className="videos__empty muted">
            Библиотека пуста. Выберите файл на компьютере или вставьте ссылку на YouTube.
          </li>
        )}

        {videos?.map((v) => (
          <li key={v.id} className={`video ${v.id === playingId ? "video--current" : ""}`}>
            <span className={`video__badge video__badge--${v.source}`}>
              {v.source === "youtube" ? <YoutubeIcon /> : <FileIcon />}
            </span>
            <div className="video__main">
              <span className="video__title" title={v.title}>
                {v.title}
              </span>
              <span className="video__meta">{describe(v, v.id === playingId)}</span>
              {(v.status === "downloading" || v.status === "pending") && (
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
                  <PlayIcon />
                  {starting === v.id ? "Запускаю…" : v.id === playingId ? "Сначала" : "Показать"}
                </button>
              )}
              <button className="icon-btn" onClick={() => remove(v)} aria-label={`Удалить ${v.title}`}>
                <TrashIcon />
              </button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

function describe(v: Video, playing: boolean): string {
  const source = v.source === "youtube" ? "YouTube" : "С компьютера";
  switch (v.status) {
    case "pending":
      return `${source}, ждёт загрузки`;
    case "downloading":
      return `${source}, скачиваю ${Math.round(v.progress * 100)}%`;
    case "failed":
      return `${source}, ошибка`;
    default:
      return [source, formatSize(v.size), playing ? "сейчас на экране" : ""].filter(Boolean).join(", ");
  }
}
