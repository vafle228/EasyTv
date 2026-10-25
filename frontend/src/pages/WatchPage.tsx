import { TabBar } from "../components/AppBar";
import { Icon } from "../components/Icons";
import { describe } from "../components/Library";
import { useNowPlaying } from "../nowPlaying";
import { R } from "../routes";
import { Link } from "../router";

/** Watch a library video right in this browser: the server streams /media/<id> with Range support. */
export function WatchPage({ videoId }: { videoId: string | null }) {
  const { videos } = useNowPlaying();
  const ready = videos?.filter((v) => v.status === "ready") ?? [];
  const video = videoId ? videos?.find((v) => v.id === videoId) : undefined;

  return (
    <div className="phone phone--page">
      <div className="phone__top">
        <Link className="btn btn--small back" to={R.main} style={{ padding: "0 14px" }}>
          <Icon name="back" />
          Телевизоры
        </Link>
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
          {video?.status === "ready" ? (
            <video key={video.id} src={`/media/${encodeURIComponent(video.id)}`} controls autoPlay playsInline />
          ) : (
            <div className="art art--a" />
          )}
        </div>
        <div>
          <p className="label" style={{ fontSize: ".72rem" }}>
            {video ? describe(video) : "Смотреть здесь"}
          </p>
          <h1 className="title" style={{ fontSize: "1.15rem" }}>
            {video?.title ?? (videoId ? "Видео не найдено" : "Выберите видео из библиотеки")}
          </h1>
          <p className="small muted">
            {video
              ? "Играет в браузере. Если файл в формате, который браузер не понимает (например, mkv с HEVC), покажите его на телевизоре."
              : "Ролики с YouTube и файлы с компьютера можно смотреть прямо здесь, без телевизора."}
          </p>
        </div>
        {video && (
          <Link className="btn btn--primary btn--block" to={R.pickFor(video.id)}>
            <Icon name="tv" />
            Перенести на телевизор
          </Link>
        )}
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
                  <span className={`video__badge video__badge--${v.source}`}>
                    <Icon name={v.source === "youtube" ? "youtube" : "file"} />
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
      </div>
      <TabBar page={false} />
    </div>
  );
}
