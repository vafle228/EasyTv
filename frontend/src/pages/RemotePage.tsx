import { useEffect } from "react";
import { TabBar } from "../components/AppBar";
import { Icon } from "../components/Icons";
import { TvScreen } from "../components/TvScreen";
import { formatTime } from "../format";
import { useNowPlaying } from "../nowPlaying";
import { STATE_LABEL, useRemote } from "../remote";
import { R } from "../routes";
import { Link, useRouter } from "../router";

const LATER = "Появится в следующей версии";

/** Phone remote for one TV. Without an id it opens the TV that is playing, or the first one online. */
export function RemotePage({ tvId }: { tvId: string | null }) {
  const { navigate } = useRouter();
  const { tvs, current } = useNowPlaying();

  useEffect(() => {
    if (tvId || tvs === null) return;
    const target = current?.tv ?? tvs.find((t) => t.online) ?? tvs[0];
    navigate(target ? R.phoneOf(target.id) : R.main, { replace: true });
  }, [tvId, tvs, current, navigate]);

  if (!tvId) return null;
  return <Remote key={tvId} tvId={tvId} />;
}

function Remote({ tvId }: { tvId: string }) {
  const r = useRemote(tvId);
  const info = r.tv.data;
  const online = info?.online ?? false;

  return (
    <div className="phone phone--page">
      <div className="phone__top">
        <Link to={R.main} className="phone__brand" style={{ color: "inherit", textDecoration: "none" }}>
          Easy <span className="brand__slash">/</span> Tv
        </Link>
        <Link className="tv-pick" to={R.main} style={{ minHeight: 40, fontSize: ".82rem" }}>
          <span className="tv-pick__dot" style={{ width: 26, height: 26 }}>
            <Icon name="tv" />
          </span>
          {info?.name ?? "Телевизор"}
          <Icon name="chevron" />
        </Link>
      </div>
      <div className="phone__body">
        <TvScreen on={online}>
          <div className="screen-content">
            <span className="screen-content__state">{info && !online ? "Не в сети" : STATE_LABEL[r.state]}</span>
            {r.active && (
              <span className="screen-content__title" style={{ fontSize: "1.1rem" }}>
                {r.current?.title ?? "Видео"}
              </span>
            )}
          </div>
        </TvScreen>
        <div>
          <p className="title" style={{ fontSize: "1.05rem" }}>
            {r.active ? (r.current?.title ?? "Видео") : "Ничего не играет"}
          </p>
          <div className="timeline" style={{ marginTop: 12 }}>
            <div className="meter">
              <span className="meter__fill" style={{ width: `${r.active ? r.percent : 0}%` }} />
            </div>
            <span className="timeline__time">
              {r.active ? `${formatTime(r.position)} / ${formatTime(r.duration)}` : "–:–– / –:––"}
            </span>
          </div>
        </div>
        <div className="remote-grid">
          <button className="round-btn" aria-label="Назад на 10 секунд" title={LATER} disabled>
            <Icon name="back10" />
          </button>
          {r.state === "paused" ? (
            <button className="round-btn round-btn--primary" aria-label="Продолжить" onClick={r.resume} disabled={r.busy}>
              <Icon name="play" />
            </button>
          ) : (
            <button
              className="round-btn round-btn--primary"
              aria-label="Пауза"
              onClick={r.pause}
              disabled={r.busy || r.state !== "playing"}
            >
              <Icon name="pause" />
            </button>
          )}
          <button className="round-btn" aria-label="Вперёд на 10 секунд" title={LATER} disabled>
            <Icon name="fwd10" />
          </button>
          <button className="round-btn" aria-label="Предыдущее видео" title={LATER} disabled>
            <Icon name="prev" />
          </button>
          <button className="round-btn" aria-label="Стоп" onClick={r.stop} disabled={r.busy || !r.active}>
            <Icon name="stop" />
          </button>
          <button className="round-btn" aria-label="Следующее видео" title={LATER} disabled>
            <Icon name="next" />
          </button>
        </div>
        <div className="volume" style={{ opacity: 0.55 }} title={`Громкость: ${LATER.toLowerCase()}`}>
          <Icon name="volume" />
          <div className="meter">
            <span className="meter__fill" style={{ width: "0%" }} />
          </div>
          <span className="timeline__time">–</span>
        </div>
        {r.error && <p className="video__error">{r.error}</p>}
        <Link className="btn btn--block" to={R.tvOf(tvId)}>
          <Icon name="list" />
          Библиотека и настройки
        </Link>
      </div>
      <TabBar page={false} />
    </div>
  );
}
