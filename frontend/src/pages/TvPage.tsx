import { useCallback, useState } from "react";
import { api } from "../api";
import { BackIcon, PauseIcon, PlayIcon, StopIcon, TrashIcon } from "../components/Icons";
import { Library } from "../components/Library";
import { Notice } from "../components/Notice";
import { TvScreen } from "../components/TvScreen";
import { formatTime } from "../format";
import { usePolling } from "../hooks";
import { Link, useRouter } from "../router";
import type { PlaybackState, Video } from "../types";

const STATE_LABEL: Record<PlaybackState, string> = {
  playing: "Играет",
  paused: "На паузе",
  stopped: "Ничего не играет",
  transitioning: "Запускается…",
  no_media: "Ничего не играет",
  unknown: "Телевизор не отвечает",
};

export function TvPage({ tvId }: { tvId: string }) {
  const { navigate } = useRouter();
  const tv = usePolling(() => api.tv(tvId), 10000, tvId);
  const playback = usePolling(() => api.playback(tvId), 2000, tvId);
  const videos = usePolling(api.videos, 2000);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const run = useCallback(
    async (action: () => Promise<unknown>) => {
      setBusy(true);
      setError(null);
      try {
        await action();
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setBusy(false);
        void playback.reload();
      }
    },
    [playback],
  );

  if (tv.error && !tv.data) {
    return (
      <main className="page">
        <BackLink />
        <Notice title="Телевизор не найден" text={tv.error} />
      </main>
    );
  }

  const info = tv.data;
  const online = info?.online ?? false;
  const state = playback.data?.state ?? "unknown";
  const current: Video | undefined = videos.data?.find((v) => v.id === playback.data?.videoId);
  const active = state === "playing" || state === "paused" || state === "transitioning";
  const position = playback.data?.positionS ?? null;
  const duration = playback.data?.durationS ?? null;
  const percent = duration && position != null ? Math.min(100, (position / duration) * 100) : 0;

  const forget = async () => {
    if (!info || !window.confirm(`Убрать «${info.name}» из списка? Если он найдётся снова, то вернётся.`)) return;
    try {
      await api.forgetTv(tvId);
      navigate("/");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <main className="page">
      <BackLink />

      <div className="tv-layout">
        <section className="card now" aria-label="Сейчас на экране">
          <h1 className="label">Сейчас на экране</h1>
          <TvScreen on={online} size="hero">
            <div className="screen-content">
              <span className="screen-content__state">{info && !online ? "Не в сети" : STATE_LABEL[state]}</span>
              {active && <span className="screen-content__title">{current?.title ?? "Видео"}</span>}
            </div>
          </TvScreen>

          <div className="timeline" aria-hidden={!active}>
            <div className="meter">
              <span className="meter__fill" style={{ width: `${active ? percent : 0}%` }} />
            </div>
            <span className="timeline__time">
              {active ? `${formatTime(position)} / ${formatTime(duration)}` : "–:–– / –:––"}
            </span>
          </div>

          <div className="remote" role="group" aria-label="Управление воспроизведением">
            {state === "paused" ? (
              <button
                className="round-btn round-btn--primary"
                onClick={() => run(() => api.resume(tvId))}
                disabled={busy}
                aria-label="Продолжить"
                title="Продолжить"
              >
                <PlayIcon />
              </button>
            ) : (
              <button
                className="round-btn round-btn--primary"
                onClick={() => run(() => api.pause(tvId))}
                disabled={busy || state !== "playing"}
                aria-label="Пауза"
                title="Пауза"
              >
                <PauseIcon />
              </button>
            )}
            <button
              className="round-btn"
              onClick={() => run(() => api.stop(tvId))}
              disabled={busy || !active}
              aria-label="Стоп"
              title="Стоп"
            >
              <StopIcon />
            </button>
          </div>
        </section>

        <section className="card about">
          <h2 className="label">Телевизор</h2>
          <div className="about__name">{info?.name ?? "Загружаю…"}</div>
          <span className={`status ${online ? "status--on" : ""}`}>{online ? "В сети" : "Не в сети"}</span>
          {info && (
            <dl className="facts">
              {info.model && (
                <>
                  <dt>Модель</dt>
                  <dd>{info.model}</dd>
                </>
              )}
              {info.manufacturer && (
                <>
                  <dt>Производитель</dt>
                  <dd>{info.manufacturer}</dd>
                </>
              )}
              <dt>Адрес</dt>
              <dd>{info.ip}</dd>
            </dl>
          )}
          {info && !online && (
            <p className="small muted">
              Телевизор давно не отвечал. Включите его: как только он появится в сети, можно будет запускать видео.
            </p>
          )}
          <button className="btn btn--quiet" onClick={forget}>
            <TrashIcon />
            Убрать из списка
          </button>
        </section>
      </div>

      {error && <Notice title="Команда не прошла" text={error} onClose={() => setError(null)} />}

      <Library
        videos={videos.data}
        playingId={active ? (playback.data?.videoId ?? null) : null}
        canPlay={online}
        onPlay={(video) => run(() => api.play(tvId, video.id))}
        onChanged={() => void videos.reload()}
        onError={setError}
      />
    </main>
  );
}

function BackLink() {
  return (
    <Link to="/" className="btn btn--small back">
      <BackIcon /> Все телевизоры
    </Link>
  );
}
