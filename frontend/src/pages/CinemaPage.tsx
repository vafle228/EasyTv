import { useState } from "react";
import { api } from "../api";
import { Icon } from "../components/Icons";
import { describe } from "../components/Library";
import { Notice } from "../components/Notice";
import { NowBar } from "../components/NowBar";
import { PosterArt } from "../components/Poster";
import { useLoad } from "../hooks";
import { useNowPlaying } from "../nowPlaying";
import { R } from "../routes";
import { Link } from "../router";
import type { SavedTitle, Video } from "../types";
import { plural } from "./VoiceDialog";

type Kind = "all" | "series" | "movie";

const KINDS: { value: Kind; label: string }[] = [
  { value: "all", label: "Всё" },
  { value: "series", label: "Сериалы" },
  { value: "movie", label: "Фильмы" },
];

export function progressOf(t: SavedTitle): string {
  if (t.kind === "movie") return t.lastEpisode !== null ? "Фильм, начинали смотреть" : "Фильм";
  if (t.lastEpisode === null) return t.episodesTotal ? `${t.episodesTotal} ${plural(t.episodesTotal, "серия", "серии", "серий")}` : "Сериал";
  return [`${t.lastEpisode} серия`, t.translation].filter(Boolean).join(", ");
}

/** Cinema: titles kept from sites with where you stopped, plus the videos already on this server. */
export function CinemaPage() {
  const saved = useLoad(api.cinema, "cinema");
  const { videos } = useNowPlaying();
  const [kind, setKind] = useState<Kind>("all");
  const [query, setQuery] = useState("");

  const q = query.trim().toLowerCase();
  const titles = (saved.data ?? []).filter(
    (t) =>
      (kind === "all" || t.kind === kind) &&
      (!q || t.title.toLowerCase().includes(q) || t.originalTitle?.toLowerCase().includes(q)),
  );
  const resume = (saved.data ?? []).filter((t) => t.lastEpisode !== null).slice(0, 6);
  const files = (videos ?? []).filter((v) => v.status === "ready" && (!q || v.title.toLowerCase().includes(q)));
  const counts = saved.data
    ? `${saved.data.length} ${plural(saved.data.length, "тайтл", "тайтла", "тайтлов")}, ${(videos ?? []).filter((v) => v.status === "ready").length} видео на сервере`
    : "Загружаю…";

  return (
    <main className="page">
      <section className="card">
        <div className="card__head" style={{ marginBottom: 22 }}>
          <div>
            <h1 className="label">Кинотеатр</h1>
            <p className="muted">{counts}</p>
          </div>
          <div className="row">
            <Link className="btn" to={R.catalog}>
              <Icon name="globe" />
              Найти на сайтах
            </Link>
            <Link className="btn" to={R.downloads}>
              <Icon name="download" />
              Загрузки
            </Link>
          </div>
        </div>
        <div className="row row--between">
          <div className="segmented" role="radiogroup" aria-label="Тип">
            {KINDS.map((k) => (
              <button key={k.value} className="segmented__item" role="radio" aria-checked={kind === k.value} onClick={() => setKind(k.value)}>
                {k.label}
              </button>
            ))}
          </div>
          <label className="field" style={{ flex: "0 1 380px", minHeight: 48 }}>
            <Icon name="search" />
            <input
              type="text"
              placeholder="Найти в кинотеатре"
              aria-label="Найти в кинотеатре"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
        </div>
      </section>

      {saved.error && <Notice title="Не загрузился кинотеатр" text={saved.error} onClose={() => void saved.reload()} />}

      {resume.length > 0 && !q && (
        <section className="card">
          <div className="section-head">
            <h2 className="label">Продолжить просмотр</h2>
          </div>
          <ResumeRail titles={resume} />
        </section>
      )}

      <section className="card">
        <div className="section-head">
          <h2 className="label">Сохранено с сайтов</h2>
          {saved.data && saved.data.length > 0 && <span className="small muted">animego</span>}
        </div>
        <div className="tiles">
          {titles.map((t) => {
            const total = t.episodesTotal ?? 0;
            const share = total ? Math.min(100, (t.watched.length / total) * 100) : 0;
            return (
              <Link className="tile" key={t.id} to={R.catalogTitle(t.id)}>
                <div className="poster">
                  <PosterArt id={t.id} title={t.title} src={t.poster} />
                  {t.kind === "series" && t.watched.length > 0 && total > 0 && (
                    <span className="poster__badge">
                      {t.watched.length} из {total}
                    </span>
                  )}
                  {share > 0 && (
                    <span className="poster__bar">
                      <span style={{ width: `${share}%` }} />
                    </span>
                  )}
                </div>
                <span className="tile__name">{t.title}</span>
                <span className="tile__meta">{[t.year, progressOf(t)].filter(Boolean).join(", ")}</span>
              </Link>
            );
          })}
          {saved.data && titles.length === 0 && q && <p className="muted">Ничего не нашлось.</p>}
          {!q && (
            <Link className="tile tile--add" to={R.catalog}>
              <div className="poster">
                <span>
                  <Icon name="plus" />
                  Найти аниме на animego
                </span>
              </div>
            </Link>
          )}
        </div>
      </section>

      <section className="card">
        <div className="section-head">
          <h2 className="label">Видео на сервере</h2>
          <Link className="link" to={R.downloads}>
            Загрузки
          </Link>
        </div>
        <ul className="videos">
          {videos !== null && files.length === 0 && (
            <li className="videos__empty muted">
              {q ? "Ничего не нашлось." : "Пока пусто. Скачайте серию со страницы тайтла, ролик с YouTube или добавьте файл на странице телевизора."}
            </li>
          )}
          {files.map((v) => (
            <FileRow key={v.id} video={v} />
          ))}
        </ul>
      </section>

      <NowBar />
    </main>
  );
}

export function ResumeRail({ titles }: { titles: SavedTitle[] }) {
  return (
    <div className="rail">
      {titles.map((t) => (
        <Link className="resume" key={t.id} to={R.catalogTitle(t.id)}>
          <div className="thumb">
            <PosterArt id={t.id} title="" src={t.poster} />
            <span className="thumb__play">
              <Icon name="play" />
            </span>
          </div>
          <span className="resume__text">
            <span className="resume__title">{t.title}</span>
            <span className="resume__meta">{progressOf(t)}</span>
          </span>
        </Link>
      ))}
    </div>
  );
}

function FileRow({ video: v }: { video: Video }) {
  return (
    <li className="video">
      <span className={`video__badge video__badge--${v.source === "animego" ? "site" : v.source}`}>
        <Icon name={v.source === "youtube" ? "youtube" : v.source === "animego" ? "globe" : "file"} />
      </span>
      <div className="video__main">
        <span className="video__title" title={v.title}>
          {v.title}
        </span>
        <span className="video__meta">{describe(v)}</span>
      </div>
      <div className="video__actions">
        <Link className="btn btn--small" to={R.watchOf(v.id)}>
          Здесь
        </Link>
        <Link className="btn btn--primary btn--small" to={R.pickFor(v.id)}>
          <Icon name="play" />
          Показать
        </Link>
      </div>
    </li>
  );
}
