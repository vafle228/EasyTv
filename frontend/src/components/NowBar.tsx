import { useState } from "react";
import { api } from "../api";
import { formatTime } from "../format";
import { useNowPlaying } from "../nowPlaying";
import { R } from "../routes";
import { Link } from "../router";
import { Icon } from "./Icons";

/** "Now on screen" strip: what the first busy TV is showing, with pause and a link to its remote. Hidden when nothing plays. */
export function NowBar() {
  const { current, reload } = useNowPlaying();
  const [busy, setBusy] = useState(false);
  if (!current) return null;

  const { tv, playback, video } = current;
  const position = playback.positionS;
  const duration = playback.durationS;
  const percent = duration && position != null ? Math.min(100, (position / duration) * 100) : 0;
  const paused = playback.state === "paused";

  const toggle = async () => {
    setBusy(true);
    try {
      await (paused ? api.resume(tv.id) : api.pause(tv.id));
    } catch {
      /* the next poll shows the real state */
    } finally {
      setBusy(false);
      void reload();
    }
  };

  return (
    <aside className="nowbar" aria-label="Сейчас на экране">
      <Link className="nowbar__tv" to={R.tvOf(tv.id)} aria-label="Открыть телевизор">
        <div className="tv tv--on tv--mini">
          <div className="tv__frame">
            <div className="tv__screen" />
          </div>
        </div>
      </Link>
      <div className="nowbar__main">
        <span className="label" style={{ margin: 0, fontSize: ".72rem" }}>
          Сейчас на экране
        </span>
        <span className="nowbar__title">{video?.title ?? "Видео"}</span>
        <span className="nowbar__meta num">
          {tv.name}, {formatTime(position)} из {formatTime(duration)}
        </span>
        <div className="meter meter--thin">
          <span className="meter__fill" style={{ width: `${percent}%` }} />
        </div>
      </div>
      <div className="nowbar__ctl">
        <button className="round-btn round-btn--sm" aria-label="Назад на 10 секунд" title="Перемотка появится позже" disabled>
          <Icon name="back10" />
        </button>
        <button
          className="round-btn round-btn--sm round-btn--primary"
          aria-label={paused ? "Продолжить" : "Пауза"}
          onClick={toggle}
          disabled={busy}
        >
          <Icon name={paused ? "play" : "pause"} />
        </button>
        <button className="round-btn round-btn--sm" aria-label="Следующая серия" title="Очередь появится позже" disabled>
          <Icon name="next" />
        </button>
      </div>
    </aside>
  );
}
