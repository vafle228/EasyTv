import { useState } from "react";
import type { FormEvent } from "react";
import { api } from "../api";
import { Icon } from "../components/Icons";
import { Notice } from "../components/Notice";
import { NowBar } from "../components/NowBar";
import { TvScreen } from "../components/TvScreen";
import { tvSubtitle } from "../format";
import { useLoad } from "../hooks";
import { isActive, useNowPlaying } from "../nowPlaying";
import { R } from "../routes";
import { Link } from "../router";
import { ResumeRail } from "./CinemaPage";

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
              const title = videos?.find((v) => v.id === p?.videoId)?.title ?? p?.title;
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

/** Titles from the cinema the user has started, newest first. Hidden until there is one. */
function ContinueWatching() {
  const saved = useLoad(api.cinema, "cinema");
  const started = (saved.data ?? []).filter((t) => t.lastEpisode !== null).slice(0, 6);
  if (started.length === 0) return null;
  return (
    <section className="card">
      <div className="section-head">
        <h2 className="label">Продолжить просмотр</h2>
        <Link className="link" to={R.cinema}>
          Весь кинотеатр
        </Link>
      </div>
      <ResumeRail titles={started} />
    </section>
  );
}
