import { api } from "../api";
import { Icon } from "../components/Icons";
import { Library } from "../components/Library";
import { Notice } from "../components/Notice";
import { TvScreen } from "../components/TvScreen";
import { formatTime } from "../format";
import { STATE_LABEL, useRemote } from "../remote";
import { R } from "../routes";
import { Link, useRouter } from "../router";

const LATER = "Появится в следующей версии";

export function TvPage({ tvId }: { tvId: string }) {
  const { navigate } = useRouter();
  const r = useRemote(tvId);

  if (r.tv.error && !r.tv.data) {
    return (
      <main className="page">
        <BackLink />
        <Notice title="Телевизор не найден" text={r.tv.error} />
      </main>
    );
  }

  const info = r.tv.data;
  const online = info?.online ?? false;

  const forget = async () => {
    if (!info || !window.confirm(`Убрать «${info.name}» из списка? Если он найдётся снова, то вернётся.`)) return;
    try {
      await api.forgetTv(tvId);
      navigate(R.main);
    } catch (e) {
      r.setError(e instanceof Error ? e.message : String(e));
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
              <span className="screen-content__state">{info && !online ? "Не в сети" : STATE_LABEL[r.state]}</span>
              {r.active && <span className="screen-content__title">{r.title ?? "Видео"}</span>}
            </div>
          </TvScreen>

          <div className="timeline" aria-hidden={!r.active}>
            <div className="meter">
              <span className="meter__fill" style={{ width: `${r.active ? r.percent : 0}%` }} />
            </div>
            <span className="timeline__time">
              {r.active ? `${formatTime(r.position)} / ${formatTime(r.duration)}` : "–:–– / –:––"}
            </span>
          </div>

          <div className="remote" role="group" aria-label="Управление воспроизведением">
            <button className="round-btn" aria-label="Назад на 10 секунд" title={LATER} disabled>
              <Icon name="back10" />
            </button>
            {r.state === "paused" ? (
              <button
                className="round-btn round-btn--primary"
                onClick={r.resume}
                disabled={r.busy}
                aria-label="Продолжить"
                title="Продолжить"
              >
                <Icon name="play" />
              </button>
            ) : (
              <button
                className="round-btn round-btn--primary"
                onClick={r.pause}
                disabled={r.busy || r.state !== "playing"}
                aria-label="Пауза"
                title="Пауза"
              >
                <Icon name="pause" />
              </button>
            )}
            <button className="round-btn" onClick={r.stop} disabled={r.busy || !r.active} aria-label="Стоп" title="Стоп">
              <Icon name="stop" />
            </button>
            <button className="round-btn" aria-label="Вперёд на 10 секунд" title={LATER} disabled>
              <Icon name="fwd10" />
            </button>
            <button className="round-btn" aria-label="Следующее видео" title={LATER} disabled>
              <Icon name="next" />
            </button>
          </div>
          <div className="volume" style={{ marginTop: 24, opacity: 0.55 }} title={`Громкость: ${LATER.toLowerCase()}`}>
            <Icon name="volume" />
            <div className="meter">
              <span className="meter__fill" style={{ width: "0%" }} />
            </div>
            <span className="timeline__time">–</span>
          </div>
        </section>

        <div className="page">
          <section className="card about">
            <h2 className="label">Телевизор</h2>
            <span className="about__name">{info?.name ?? "Загружаю…"}</span>
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
            <Link className="btn btn--small" to={R.phoneOf(tvId)} style={{ alignSelf: "flex-start" }}>
              <Icon name="phone" />
              Пульт для телефона
            </Link>
            <button className="btn btn--quiet" onClick={forget}>
              <Icon name="trash" />
              Убрать из списка
            </button>
          </section>

          <section className="card">
            <div className="section-head" style={{ marginBottom: 14 }}>
              <h2 className="label">Дальше</h2>
            </div>
            <p className="small muted">
              Очередь появится в следующей версии: можно будет добавить сюда несколько видео, и следующая серия
              включится сама.
            </p>
          </section>
        </div>
      </div>

      {r.error && <Notice title="Не получилось" text={r.error} onClose={() => r.setError(null)} />}

      <Library
        videos={r.videos.data}
        playingId={r.active ? (r.current?.id ?? null) : null}
        canPlay={online}
        onPlay={r.play}
        onChanged={() => {
          r.setError(null);
          void r.videos.reload();
        }}
        onError={r.setError}
      />
    </main>
  );
}

function BackLink() {
  return (
    <Link to={R.main} className="btn btn--small back">
      <Icon name="back" />
      Все телевизоры
    </Link>
  );
}
