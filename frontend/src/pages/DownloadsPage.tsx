import { useState } from "react";
import { api } from "../api";
import { DemoNote, useDemoControls } from "../components/Demo";
import { Icon } from "../components/Icons";
import { describe } from "../components/Library";
import { Notice } from "../components/Notice";
import { useNowPlaying } from "../nowPlaying";
import { R } from "../routes";
import { Link } from "../router";
import type { Video } from "../types";

/** Downloads: YouTube is real (the library's pending/downloading/failed items); torrents and sites are a sample. */
export function DownloadsPage() {
  const { videos, reload } = useNowPlaying();
  const [error, setError] = useState<string | null>(null);

  const active = videos?.filter((v) => v.status === "downloading" || v.status === "pending") ?? [];
  const failed = videos?.filter((v) => v.status === "failed") ?? [];
  const done = videos?.filter((v) => v.status === "ready" && v.source === "youtube") ?? [];
  const downloading = active.filter((v) => v.status === "downloading").length;

  const remove = async (v: Video) => {
    try {
      await api.deleteVideo(v.id);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <main className="page">
      <section className="card">
        <div className="card__head">
          <div>
            <h1 className="label">Загрузки</h1>
            <p className="muted">Торренты, YouTube и сайты в одном месте. Готовое само попадает в библиотеку.</p>
          </div>
          <Link className="btn" to={R.add}>
            <Icon name="plus" />
            Добавить
          </Link>
        </div>
        <div className="stats">
          <div className="stat">
            <span className="stat__v">{downloading}</span>
            <span className="stat__k">Скачиваю сейчас</span>
          </div>
          <div className="stat">
            <span className="stat__v">{active.length - downloading}</span>
            <span className="stat__k">В очереди</span>
          </div>
          <div className="stat">
            <span className="stat__v">{done.length}</span>
            <span className="stat__k">Готово с YouTube</span>
          </div>
          <div className="stat">
            <span className="stat__v">{failed.length}</span>
            <span className="stat__k">С ошибкой</span>
          </div>
        </div>
      </section>

      {error && <Notice title="Не получилось" text={error} onClose={() => setError(null)} />}

      <section className="card">
        <div className="section-head">
          <h2 className="label">Сейчас</h2>
        </div>
        <ul className="videos">
          {videos !== null && active.length + failed.length === 0 && (
            <li className="videos__empty muted">Ничего не скачивается. Вставьте ссылку на YouTube в поле «Добавить».</li>
          )}
          {[...active, ...failed].map((v) => (
            <li key={v.id} className="video">
              <span className="video__badge video__badge--youtube">
                <Icon name="youtube" />
              </span>
              <div className="video__main">
                <span className="video__title" title={v.title}>
                  {v.title}
                </span>
                <span className="video__meta num">{describe(v)}</span>
                {v.status !== "failed" && (
                  <div className="meter meter--thin" style={{ width: "min(520px,100%)" }}>
                    <span className="meter__fill" style={{ width: `${v.progress * 100}%` }} />
                  </div>
                )}
                {v.status === "failed" && <span className="video__error">{v.error ?? "Не удалось скачать"}</span>}
              </div>
              <div className="video__actions">
                <button
                  className="icon-btn"
                  aria-label={v.status === "failed" ? "Удалить" : "Отменить"}
                  onClick={() => remove(v)}
                >
                  <Icon name={v.status === "failed" ? "trash" : "close"} />
                </button>
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section className="card">
        <div className="section-head">
          <h2 className="label">Готово</h2>
        </div>
        <ul className="videos">
          {videos !== null && done.length === 0 && <li className="videos__empty muted">Пока ничего не скачано.</li>}
          {done.slice(0, 10).map((v) => (
            <li key={v.id} className="video">
              <span className="video__badge video__badge--youtube">
                <Icon name="youtube" />
              </span>
              <div className="video__main">
                <span className="video__title" title={v.title}>
                  {v.title}
                </span>
                <span className="video__meta">{describe(v)}, в библиотеке</span>
              </div>
              <div className="video__actions">
                <Link className="btn btn--primary btn--small" to={R.pickFor(v.id)}>
                  <Icon name="play" />
                  Показать
                </Link>
              </div>
            </li>
          ))}
        </ul>
      </section>

      <TorrentsSample />
    </main>
  );
}

function TorrentsSample() {
  const ref = useDemoControls<HTMLElement>();
  return (
    <section className="card" ref={ref}>
      <div className="section-head">
        <h2 className="label">Торренты и сайты</h2>
      </div>
      <DemoNote>Торренты, сайты и перекодирование появятся позже. Так это будет выглядеть.</DemoNote>
      <ul className="videos" style={{ marginTop: 18 }}>
        <li className="video">
          <span className="video__badge video__badge--torrent">
            <Icon name="magnet" />
          </span>
          <div className="video__main">
            <span className="video__title">Фрирен, провожающая в последний путь, 1 сезон</span>
            <span className="video__meta num">Торрент, 12 серий, 10.5 из 16.4 ГБ, 16 МБ/с, осталось 6 мин</span>
            <div className="meter meter--thin" style={{ width: "min(520px,100%)" }}>
              <span className="meter__fill" style={{ width: "64%" }} />
            </div>
            <span className="video__meta" style={{ marginTop: 6 }}>
              Готовы к просмотру: 1–9 серии
            </span>
          </div>
          <div className="video__actions">
            <Link className="btn btn--small" to={R.title}>
              Карточка
            </Link>
            <button className="icon-btn icon-btn--neutral" aria-label="Пауза">
              <Icon name="pause" />
            </button>
            <button className="icon-btn" aria-label="Отменить">
              <Icon name="close" />
            </button>
          </div>
        </li>
        <li className="video">
          <span className="video__badge video__badge--cinema">
            <Icon name="cog" />
          </span>
          <div className="video__main">
            <span className="video__title">Фрирен, 10 серия</span>
            <span className="video__meta num">Перекодирую HEVC → H.264, 38%, осталось 4 мин</span>
            <div className="meter meter--thin">
              <span className="meter__fill" style={{ width: "38%" }} />
            </div>
          </div>
          <div className="video__actions">
            <button className="icon-btn" aria-label="Отменить">
              <Icon name="close" />
            </button>
          </div>
        </li>
        <li className="video">
          <span className="video__badge video__badge--site">
            <Icon name="globe" />
          </span>
          <div className="video__main">
            <span className="video__title">Дандадан, 3 серия</span>
            <span className="video__meta num">animego, озвучка AniLibria, 720p, 72%</span>
            <div className="meter meter--thin">
              <span className="meter__fill" style={{ width: "72%" }} />
            </div>
          </div>
          <div className="video__actions">
            <button className="icon-btn icon-btn--neutral" aria-label="Пауза">
              <Icon name="pause" />
            </button>
            <button className="icon-btn" aria-label="Отменить">
              <Icon name="close" />
            </button>
          </div>
        </li>
        <li className="video">
          <span className="video__badge video__badge--torrent">
            <Icon name="magnet" />
          </span>
          <div className="video__main">
            <span className="video__title">Дюна: Часть вторая</span>
            <span className="video__meta">
              Торрент, 12.8 ГБ, в кинотеатре <span className="tag tag--live">раздаю, 0.6 : 1</span>
            </span>
          </div>
          <div className="video__actions">
            <Link className="btn btn--primary btn--small" to={R.film}>
              <Icon name="play" />
              Смотреть
            </Link>
            <button className="btn btn--small">Не раздавать</button>
          </div>
        </li>
      </ul>
    </section>
  );
}
