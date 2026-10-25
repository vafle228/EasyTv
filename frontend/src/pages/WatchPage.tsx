import { useEffect, useState } from "react";
import { api } from "../api";
import { TabBar } from "../components/AppBar";
import { Icon } from "../components/Icons";
import { describe } from "../components/Library";
import { useLoad } from "../hooks";
import { useNowPlaying } from "../nowPlaying";
import { R } from "../routes";
import { Link } from "../router";
import type { Resolved, StreamRef } from "../types";
import { PickDialog } from "./PickDialog";

/** Watch right in this browser: a library video from /media/<id>, or an episode from a site through /stream/…. */
export function WatchPage({ videoId, stream }: { videoId: string | null; stream?: StreamRef }) {
  const { videos } = useNowPlaying();
  const ready = videos?.filter((v) => v.status === "ready") ?? [];
  const video = videoId ? videos?.find((v) => v.id === videoId) : undefined;
  const site = useSiteEpisode(stream);
  const [pick, setPick] = useState(false);

  const heading = stream ? (site.name ?? "Загружаю…") : (video?.title ?? (videoId ? "Видео не найдено" : "Выберите видео из библиотеки"));

  return (
    <div className="phone phone--page">
      <div className="phone__top">
        {stream ? (
          <Link className="btn btn--small back" to={R.catalogTitle(stream.titleId)} style={{ padding: "0 14px" }}>
            <Icon name="back" />К тайтлу
          </Link>
        ) : (
          <Link className="btn btn--small back" to={R.main} style={{ padding: "0 14px" }}>
            <Icon name="back" />
            Телевизоры
          </Link>
        )}
        <Link className="tv-pick" to={video ? R.pickFor(video.id) : R.pick} style={{ minHeight: 40, fontSize: ".82rem" }}>
          <span className="tv-pick__dot" style={{ width: 26, height: 26 }}>
            <Icon name="phone" />
          </span>
          Этот браузер
          <Icon name="chevron" />
        </Link>
      </div>
      <div className="phone__body">
        <div className="player">
          {stream && site.ready ? (
            <video key={site.ready.url} src={site.ready.url} controls autoPlay playsInline />
          ) : !stream && video?.status === "ready" ? (
            <video key={video.id} src={`/media/${encodeURIComponent(video.id)}`} controls autoPlay playsInline />
          ) : (
            <div className="art art--a" />
          )}
        </div>
        <div>
          <p className="label" style={{ fontSize: ".72rem" }}>
            {stream
              ? site.ready
                ? `animego, ${site.ready.provider.toUpperCase()}${site.ready.quality ? `, ${site.ready.quality}p` : ""}`
                : "animego"
              : video
                ? describe(video)
                : "Смотреть здесь"}
          </p>
          <h1 className="title" style={{ fontSize: "1.15rem" }}>
            {heading}
          </h1>
          <p className="small muted">
            {stream
              ? site.error
                ? site.error
                : site.ready
                  ? "Видео идёт с сайта через этот сервер, без скачивания."
                  : "Получаю свежую ссылку на видео с сайта…"
              : video
                ? "Играет в браузере. Если файл в формате, который браузер не понимает (например, mkv с HEVC), покажите его на телевизоре."
                : "Ролики с YouTube, файлы с компьютера и серии с сайтов можно смотреть прямо здесь, без телевизора."}
          </p>
        </div>
        {stream && (
          <div className="row">
            {stream.episode > 1 && (
              <Link className="btn btn--small" to={R.watchStream({ ...stream, episode: stream.episode - 1 })}>
                <Icon name="prev" />
                {stream.episode - 1} серия
              </Link>
            )}
            {stream.episode > 0 && (site.total === null || stream.episode < site.total) && (
              <Link className="btn btn--small" to={R.watchStream({ ...stream, episode: stream.episode + 1 })}>
                {stream.episode + 1} серия
                <Icon name="next" />
              </Link>
            )}
          </div>
        )}
        {(video || (stream && site.ready)) && (
          <button
            className="btn btn--primary btn--block"
            onClick={() => setPick(true)}
          >
            <Icon name="tv" />
            Перенести на телевизор
          </button>
        )}
        {!stream && (
          <div>
            <p className="label" style={{ fontSize: ".72rem", marginBottom: 12 }}>
              Библиотека
            </p>
            <ul className="videos" style={{ gap: 12 }}>
              {videos !== null && ready.length === 0 && (
                <li className="videos__empty muted">Готовых видео пока нет. Добавьте ролик на странице телевизора.</li>
              )}
              {ready.map((v) => (
                <li key={v.id}>
                  <Link
                    className={`video ${v.id === videoId ? "video--current" : ""}`}
                    to={R.watchOf(v.id)}
                    style={{ padding: "10px 14px", color: "inherit", textDecoration: "none" }}
                    aria-current={v.id === videoId ? "true" : undefined}
                  >
                    <span className={`video__badge video__badge--${v.source === "animego" ? "site" : v.source}`}>
                      <Icon name={v.source === "youtube" ? "youtube" : v.source === "animego" ? "globe" : "file"} />
                    </span>
                    <span className="video__main">
                      <span className="video__title" title={v.title}>
                        {v.title}
                      </span>
                      <span className="video__meta">{v.id === videoId ? "Сейчас" : describe(v)}</span>
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
      <TabBar page={false} />
      {pick && stream && site.name && (
        <PickDialog
          videoId={null}
          stream={{ ref: stream, title: site.name, translation: site.translation }}
          onClose={() => setPick(false)}
        />
      )}
      {pick && !stream && video && <PickDialog videoId={video.id} onClose={() => setPick(false)} />}
    </div>
  );
}

/** Title of a site episode and a playable address for it (resolving also records progress in the cinema). */
function useSiteEpisode(stream: StreamRef | undefined) {
  const key = stream ? `${stream.titleId}/${stream.episode}/${stream.translationId}/${stream.provider ?? "auto"}` : "";
  const title = useLoad(async () => (stream ? api.title(stream.titleId) : null), stream?.titleId ?? "");
  const [ready, setReady] = useState<Resolved | null>(null);
  const [translation, setTranslation] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!stream) return;
    let alive = true;
    setReady(null);
    setError(null);
    (async () => {
      const dubs = await api.variants(stream.titleId, stream.episode);
      const dub = dubs.find((d) => d.translationId === stream.translationId);
      if (!dub) throw new Error("У этой серии нет выбранной озвучки. Вернитесь к тайтлу и выберите другую.");
      if (alive) setTranslation(dub.translation);
      const r = await api.resolve(stream, dub.translation);
      if (alive) setReady(r);
    })().catch((e) => alive && setError(e instanceof Error ? e.message : String(e)));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const t = title.data;
  const name = t ? (stream && stream.episode > 0 ? `${t.title}, ${stream.episode} серия` : t.title) : null;
  return { name, ready, translation, error: error ?? title.error, total: t?.episodesTotal ?? null };
}
