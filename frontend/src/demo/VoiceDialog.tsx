import { useEffect } from "react";
import { useDemoControls } from "../components/Demo";
import { Icon } from "../components/Icons";
import { R } from "../routes";
import { Link, useRouter } from "../router";

/** Mockup dialog «Выбор озвучки» over the site title page, with sample data. */
export function VoiceDialog() {
  const ref = useDemoControls<HTMLDivElement>();
  const { navigate } = useRouter();
  const close = () => navigate(R.sourceTitle);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && navigate(R.sourceTitle);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [navigate]);
  return (
    <div className="scrim scrim--overlay" ref={ref} onClick={(e) => e.target === e.currentTarget && close()}>
      <section className="card dialog dialog--wide" role="dialog" aria-modal="true" aria-labelledby="voice-title">
        <div className="row row--between" style={{ alignItems: "flex-start", flexWrap: "nowrap" }}>
          <div className="grow">
            <p className="label">Озвучка</p>
            <h1 id="voice-title" className="title">Наруто: Ураганные хроники</h1>
            <p className="small muted">9 вариантов на сайте. Метка «в списке» значит, что студия в вашем порядке любимых озвучек: по нему выбираю сам, когда у серии нет нужной.</p>
          </div>
          <Link className="icon-btn icon-btn--flat icon-btn--neutral" to={R.sourceTitle} aria-label="Закрыть"><Icon name="close" /></Link>
        </div>
        <div className="row" style={{ margin: "18px 0 16px" }}>
          <label className="field" style={{ minHeight: "48px" }}><Icon name="search" /><input type="text" placeholder="Найти студию" aria-label="Найти студию" /></label>
        </div>
        <div className="chips scroller chips--m-scroll" style={{ marginBottom: "18px" }}>
          <button className="chip" aria-pressed="true">Все 9</button>
          <button className="chip" aria-pressed="false">Многоголосые 5</button>
          <button className="chip" aria-pressed="false">Одноголосые 2</button>
          <button className="chip" aria-pressed="false">Субтитры 2</button>
          <button className="chip" aria-pressed="false">Есть все 500 серий</button>
        </div>
        <ul className="opts opts--scroll" role="radiogroup" aria-label="Озвучка">
          <li><button className="opt" role="radio" aria-checked="true">
            <span className="opt__radio"></span>
            <span className="opt__main"><span className="opt__name">AniDUB <span className="tag tag--blue">1 в списке</span></span><span className="opt__meta">Многоголосая, 498 из 500 серий</span></span>
            <span className="opt__players"><span className="tag">CVH 1080p</span><span className="tag">Kodik 720p</span><span className="tag">Aniboom</span></span>
          </button></li>
          <li><button className="opt" role="radio" aria-checked="false">
            <span className="opt__radio"></span>
            <span className="opt__main"><span className="opt__name">AniLibria <span className="tag tag--blue">2 в списке</span></span><span className="opt__meta">Многоголосая, 500 из 500</span></span>
            <span className="opt__players"><span className="tag">CVH 1080p</span><span className="tag">Kodik 720p</span></span>
          </button></li>
          <li><button className="opt" role="radio" aria-checked="false">
            <span className="opt__radio"></span>
            <span className="opt__main"><span className="opt__name">2x2 <span className="tag tag--blue">3 в списке</span></span><span className="opt__meta">Многоголосая, ТВ-версия, 1–220</span></span>
            <span className="opt__players"><span className="tag">Kodik 720p</span></span>
          </button></li>
          <li><button className="opt" role="radio" aria-checked="false">
            <span className="opt__radio"></span>
            <span className="opt__main"><span className="opt__name">Субтитры, русские <span className="tag tag--blue">4 в списке</span></span><span className="opt__meta">Японская дорожка, 500 из 500</span></span>
            <span className="opt__players"><span className="tag">CVH 1080p</span><span className="tag">Aniboom</span></span>
          </button></li>
          <li><button className="opt" role="radio" aria-checked="false">
            <span className="opt__radio"></span>
            <span className="opt__main"><span className="opt__name">Студийная Банда</span><span className="opt__meta">Многоголосая, 1–96</span></span>
            <span className="opt__players"><span className="tag">CVH 1080p</span><span className="tag">Kodik 720p</span></span>
          </button></li>
          <li><button className="opt" role="radio" aria-checked="false">
            <span className="opt__radio"></span>
            <span className="opt__main"><span className="opt__name">Shiroi Kitsune</span><span className="opt__meta">Многоголосая, 120–180</span></span>
            <span className="opt__players"><span className="tag">CVH 1080p</span></span>
          </button></li>
          <li><button className="opt" role="radio" aria-checked="false">
            <span className="opt__radio"></span>
            <span className="opt__main"><span className="opt__name">Ancord</span><span className="opt__meta">Одноголосая, 1–500</span></span>
            <span className="opt__players"><span className="tag">Kodik 720p</span><span className="tag">Aniboom</span></span>
          </button></li>
        </ul>
        <p className="small muted" style={{ marginTop: "6px" }}>Ещё 2 ниже. Список прокручивается и фильтруется по поиску.</p>
        <div className="dialog__foot">
          <span className="optline"><button className="check" role="checkbox" aria-checked="true" aria-label="Только для этого тайтла"><Icon name="check" /></button><span className="small">Только для этого тайтла</span></span>
          <div className="row">
            <Link className="btn btn--small" to={R.sourceTitle}>Отмена</Link>
            <Link className="btn btn--primary btn--small" to={R.sourceTitle}><Icon name="check" />Выбрать AniDUB</Link>
          </div>
        </div>
      </section>
    </div>
  );
}
