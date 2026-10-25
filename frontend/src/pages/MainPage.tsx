import { useState } from "react";
import type { FormEvent } from "react";
import { api } from "../api";
import { Icon } from "../components/Icons";
import { Notice } from "../components/Notice";
import { NowBar } from "../components/NowBar";
import { TvScreen } from "../components/TvScreen";
import { tvSubtitle } from "../format";
import { isActive, useNowPlaying } from "../nowPlaying";
import { R } from "../routes";
import { Link } from "../router";

const PLAYBACK_LABEL = { playing: "Играет", paused: "На паузе", transitioning: "Запускается…" } as const;

export function MainPage() {
  const { tvs, videos, playback, error, reload } = useNowPlaying();
  const [searching, setSearching] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [address, setAddress] = useState("");
  const [adding, setAdding] = useState(false);

  const searchNow = async () => {
    setSearching(true);
    setProblem(null);
    try {
      await api.refreshTvs();
      await reload();
    } catch (e) {
      setProblem(e instanceof Error ? e.message : String(e));
    } finally {
      setSearching(false);
    }
  };

  const addTv = async (e: FormEvent) => {
    e.preventDefault();
    if (!address.trim()) return;
    setAdding(true);
    setProblem(null);
    try {
      await api.addTv(address.trim());
      setAddress("");
      await reload();
    } catch (err) {
      setProblem(err instanceof Error ? err.message : String(err));
    } finally {
      setAdding(false);
    }
  };

  const online = tvs?.filter((t) => t.online).length ?? 0;

  return (
    <main className="page">
      <section className="card">
        <div className="card__head">
          <div>
            <h1 className="label">Телевизоры</h1>
            <p className="muted">
              {tvs === null
                ? "Загружаю список…"
                : tvs.length === 0
                  ? "Ищу телевизоры в сети каждые 15 секунд."
                  : `В сети ${online} из ${tvs.length}. Выберите, на каком показать видео.`}
            </p>
          </div>
          <button className="btn" onClick={searchNow} disabled={searching}>
            <span className={searching ? "spin" : undefined} style={{ display: "inline-flex" }}>
              <Icon name="refresh" />
            </span>
            {searching ? "Ищу…" : "Искать сейчас"}
          </button>
        </div>

        {(problem || error) && (
          <Notice
            title={problem ? "Не получилось" : "Нет связи с сервером"}
            text={problem ?? error}
            onClose={problem ? () => setProblem(null) : undefined}
          />
        )}

        {tvs && tvs.length === 0 && (
          <div className="empty" style={{ marginBottom: 28 }}>
            <TvScreen on={false}>
              <span className="tv__hint">нет сигнала</span>
            </TvScreen>
            <div>
              <h2 className="title">Телевизоров пока не видно</h2>
              <p className="muted">
                Включите телевизор и проверьте, что он подключён к тому же роутеру, что и этот компьютер. Если поиск
                его не находит, добавьте телевизор по адресу ниже.
              </p>
            </div>
          </div>
        )}

        {tvs && (
          <ul className="tv-grid">
            {tvs.map((tv) => {
              const p = playback[tv.id];
              const title = videos?.find((v) => v.id === p?.videoId)?.title;
              return (
                <li key={tv.id}>
                  <Link to={R.tvOf(tv.id)} className="tv-card">
                    <TvScreen on={tv.online}>
                      {!tv.online ? (
                        <span className="tv__hint">нет сигнала</span>
                      ) : isActive(p) ? (
                        <div className="screen-content">
                          <span className="screen-content__state">
                            {PLAYBACK_LABEL[p.state as keyof typeof PLAYBACK_LABEL]}
                          </span>
                          <span className="tv-card__playing">{title ?? "Видео"}</span>
                        </div>
                      ) : (
                        <span className="tv__brand">{tv.manufacturer?.split(" ")[0] ?? "TV"}</span>
                      )}
                    </TvScreen>
                    <span className="tv-card__name">{tv.name}</span>
                    <span className="tv-card__meta">
                      <span className={`status ${tv.online ? "status--on" : ""}`}>
                        {tv.online ? "В сети" : "Не в сети"}
                      </span>
                      <span>{tvSubtitle(tv.manufacturer, tv.model, tv.ip)}</span>
                    </span>
                  </Link>
                </li>
              );
            })}
            <li>
              <Link className="tv-card tv-card--here" to={R.watch}>
                <div className="tv">
                  <div className="tv__frame">
                    <Icon name="phone" />
                  </div>
                  <div className="tv__stand" style={{ visibility: "hidden" }} />
                </div>
                <span className="tv-card__name">Этот браузер</span>
                <span className="tv-card__meta">
                  <span>Смотреть здесь, на телефоне или ноутбуке</span>
                </span>
              </Link>
            </li>
          </ul>
        )}
      </section>

      <ContinueWatching />

      <section className="card">
        <h2 className="label">Добавить по адресу</h2>
        <p className="muted">
          Если телевизор не находится сам, укажите его IP (например, 192.168.0.72) или адрес описания устройства, который
          показывает <code>./run.sh discover</code>.
        </p>
        <form className="field-row" onSubmit={addTv}>
          <label className="field">
            <Icon name="link" />
            <input
              placeholder="192.168.0.72 или http://…"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              aria-label="IP или адрес телевизора"
            />
          </label>
          <button className="btn btn--primary" type="submit" disabled={adding || !address.trim()}>
            <Icon name="plus" />
            {adding ? "Ищу телевизор…" : "Добавить"}
          </button>
        </form>
      </section>

      <NowBar />
    </main>
  );
}

/** Positions aren't stored yet, so this shelf shows the mockup's sample until the cinema backend lands. */
function ContinueWatching() {
  return (
    <section className="card">
      <div className="section-head">
        <h2 className="label">
          Продолжить просмотр <span className="tag">пример</span>
        </h2>
        <Link className="link" to={R.cinema}>
          Весь кинотеатр
        </Link>
      </div>
      <div className="rail">
        <Link className="resume" to={R.title}>
          <div className="thumb">
            <div className="art art--a" />
            <span className="thumb__play">
              <Icon name="play" />
            </span>
            <span className="poster__bar">
              <span style={{ width: "52%" }} />
            </span>
          </div>
          <span className="resume__text">
            <span className="resume__title">Фрирен, провожающая в последний путь</span>
            <span className="resume__meta">Аниме, 8 серия, осталось 11 мин</span>
          </span>
        </Link>
        <Link className="resume" to={R.film}>
          <div className="thumb">
            <div className="art art--e" />
            <span className="thumb__play">
              <Icon name="play" />
            </span>
            <span className="poster__bar">
              <span style={{ width: "44%" }} />
            </span>
          </div>
          <span className="resume__text">
            <span className="resume__title">Дюна: Часть вторая</span>
            <span className="resume__meta">Фильм, остановились на 1:12:40</span>
          </span>
        </Link>
        <Link className="resume" to={R.tv}>
          <div className="thumb">
            <div className="art art--g" />
            <span className="thumb__play">
              <Icon name="play" />
            </span>
            <span className="poster__bar">
              <span style={{ width: "18%" }} />
            </span>
          </div>
          <span className="resume__text">
            <span className="resume__title">Как приготовить идеальный рамен дома</span>
            <span className="resume__meta">YouTube, 3:05 из 17:20</span>
          </span>
        </Link>
      </div>
    </section>
  );
}
