import { useEffect, useState } from "react";
import { api } from "../api";
import { Icon } from "../components/Icons";
import { TvScreen } from "../components/TvScreen";
import { isActive, useNowPlaying } from "../nowPlaying";
import { R } from "../routes";
import { useRouter } from "../router";
import type { StreamRef } from "../types";

const HERE = "browser";

/** An episode from a site to show: where it is, how to call it and which dub it is in. */
export interface StreamTarget {
  ref: StreamRef;
  title: string;
  translation: string | null;
}

/**
 * "Где показать": pick a TV or this browser for a library video or an episode from a site.
 * With neither it still lists the real TVs and just opens the chosen one.
 */
export function PickDialog({
  videoId,
  stream,
  onClose,
}: {
  videoId: string | null;
  stream?: StreamTarget;
  onClose: () => void;
}) {
  const { navigate } = useRouter();
  const { tvs, videos, playback } = useNowPlaying();
  const video = videoId ? videos?.find((v) => v.id === videoId) : undefined;
  const [choice, setChoice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selected = choice ?? tvs?.find((t) => t.online)?.id ?? HERE;

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const show = async () => {
    if (selected === HERE) {
      navigate(stream ? R.watchStream(stream.ref) : videoId ? R.watchOf(videoId) : R.watch);
      return;
    }
    if (!videoId && !stream) {
      navigate(R.tvOf(selected));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      if (stream) await api.playStream(selected, stream.ref, stream.title, stream.translation);
      else if (videoId) await api.play(selected, videoId);
      navigate(R.tvOf(selected));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setBusy(false);
    }
  };

  return (
    <div className="scrim scrim--overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <section className="card dialog" role="dialog" aria-modal="true" aria-labelledby="pick-title">
        <div className="row row--between" style={{ alignItems: "flex-start" }}>
          <div>
            <p className="label">Где показать</p>
            <h1 id="pick-title" className="title">
              {stream?.title ?? video?.title ?? (videoId ? "Видео" : "Выберите экран")}
            </h1>
            {stream?.translation && <p className="small muted">Озвучка {stream.translation}</p>}
          </div>
          <button className="icon-btn icon-btn--flat icon-btn--neutral" aria-label="Закрыть" onClick={onClose}>
            <Icon name="close" />
          </button>
        </div>
        <ul className="picks" role="radiogroup" aria-label="Устройство">
          {tvs?.map((tv) => {
            const p = playback[tv.id];
            const same =
              isActive(p) &&
              (stream
                ? p.stream?.titleId === stream.ref.titleId && p.stream?.episode === stream.ref.episode
                : p.videoId === videoId);
            return (
              <li key={tv.id}>
                <button
                  className="pick"
                  role="radio"
                  aria-checked={selected === tv.id}
                  disabled={!tv.online}
                  onClick={() => setChoice(tv.id)}
                >
                  <TvScreen on={tv.online} size="mini">
                    {tv.online ? (
                      <span className="tv__brand">{tv.manufacturer?.split(" ")[0] ?? "TV"}</span>
                    ) : (
                      <span className="tv__hint">нет сигнала</span>
                    )}
                  </TvScreen>
                  <span className="grow">
                    <span className="pick__name">{tv.name}</span>
                    <span className="pick__meta">
                      {!tv.online
                        ? "Не в сети. Включите телевизор."
                        : same
                          ? "В сети, сейчас показывает это же видео"
                          : isActive(p)
                            ? "В сети, сейчас показывает другое видео"
                            : "В сети"}
                    </span>
                  </span>
                </button>
              </li>
            );
          })}
          <li>
            <button className="pick" role="radio" aria-checked={selected === HERE} onClick={() => setChoice(HERE)}>
              <span className="pick__icon">
                <Icon name="phone" />
              </span>
              <span className="grow">
                <span className="pick__name">Этот браузер</span>
                <span className="pick__meta">Смотреть здесь, без телевизора</span>
              </span>
            </button>
          </li>
        </ul>
        {error && (
          <p className="video__error" style={{ marginTop: 14 }}>
            {error}
          </p>
        )}
        <div className="dialog__foot">
          <span className="small muted">{tvs === null ? "Ищу телевизоры…" : ""}</span>
          <div className="row">
            <button className="btn btn--small" onClick={onClose}>
              Отмена
            </button>
            <button className="btn btn--primary btn--small" onClick={show} disabled={busy}>
              <Icon name="play" />
              {busy ? (stream ? "Ищу видео…" : "Запускаю…") : "Показать"}
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
