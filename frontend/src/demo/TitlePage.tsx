import { DemoNote, useDemoControls } from "../components/Demo";
import { Icon } from "../components/Icons";
import { NowBar } from "../components/NowBar";
import { R } from "../routes";
import { Link } from "../router";

/** Mockup screen «Title» with sample data: the backend for this section isn't built yet. */
export function TitlePage() {
  const ref = useDemoControls<HTMLElement>();
  return (
    <main className="page" ref={ref}>
      <DemoNote />
      <Link className="btn btn--small back" to={R.cinema}><Icon name="back" />Кинотеатр</Link>

      <section className="card">
        <div className="hero">
          <div className="poster"><div className="art art--a"><span className="art__word">Фрирен</span></div></div>
          <div>
            <p className="label">Аниме</p>
            <h1 className="hero__title">Фрирен, провожающая в последний путь</h1>
            <p className="hero__orig">Sousou no Frieren, 2023</p>
            <div className="chips">
              <span className="chip chip--static">Фэнтези</span>
              <span className="chip chip--static">Приключения</span>
              <span className="chip chip--static">Драма</span>
              <span className="tag tag--blue" style={{ minHeight: "36px", padding: "0 14px" }}>Смотрю, 7 из 28</span>
            </div>
            <p className="hero__text">Эльфийка-маг пережила своих спутников по отряду, который победил Короля демонов, и отправляется в новое путешествие, чтобы понять людей, с которыми прошла полжизни.</p>
            <dl className="facts facts--wide" style={{ maxWidth: "640px", marginTop: "20px" }}>
              <dt>Студия</dt><dd>Madhouse</dd>
              <dt>Серий</dt><dd>28, по 24 мин</dd>
              <dt>Оценка</dt><dd><Icon name="star" /> 9.1, Shikimori</dd>
              <dt>На диске</dt><dd>9 серий, ещё 3 скачиваю</dd>
            </dl>
            <div className="hero__actions">
              <Link className="btn btn--primary" to={R.tv}><Icon name="play" />Смотреть 8 серию с 12:40</Link>
              <Link className="tv-pick" to={R.pick}><span className="tv-pick__dot"><Icon name="tv" /></span><span>на [TV] Samsung LED40</span><Icon name="chevron" /></Link>
            </div>
            <div className="row" style={{ marginTop: "16px" }}>
              <Link className="btn btn--small" to={R.torrent}><Icon name="magnet" />Докачать серии</Link>
              <button className="btn btn--small"><Icon name="edit" />Изменить данные</button>
              <span className="small muted">Описание и постер: Shikimori, обновлено 25 октября</span>
            </div>
          </div>
        </div>
      </section>

      <section className="card">
        <div className="section-head">
          <h2 className="label">Серии</h2>
          <div className="row">
            <span className="optline small"><button className="check" role="checkbox" aria-checked="true" aria-label="Включать следующую серию"><Icon name="check" /></button>Включать следующую серию</span>
            <button className="btn btn--small"><Icon name="check" />Отметить сезон</button>
          </div>
        </div>
        <div className="eptools">
          <div className="segmented scroller" role="radiogroup" aria-label="Сезон">
            <button className="segmented__item" role="radio" aria-checked="true">1 сезон, 28</button>
            <button className="segmented__item" role="radio" aria-checked="false">2 сезон, 4 из 12</button>
            <button className="segmented__item" role="radio" aria-checked="false">Фильмы и спешлы, 2</button>
          </div>
          <div className="row">
            <button className="select select--sm"><span className="select__k">Звук</span><span className="select__v">Русский, AniLibria</span><span className="tag">3</span><Icon name="chevron" /></button>
            <button className="select select--sm"><span className="select__k">Субтитры</span><span className="select__v">Выкл</span><span className="tag">2</span><Icon name="chevron" /></button>
          </div>
        </div>
        <ul className="eps">
          <li className="eps__more" style={{ padding: "0 0 4px" }}><button className="btn btn--quiet" style={{ alignSelf: "auto" }}>Показать 1–6 серии, просмотрены</button></li>
          <li className="video ep ep--watched">
            <Link className="shot shot--watched shot--f3" to={R.tv} aria-label="7 серия"><div className="art art--a"></div><span className="shot__no"><Icon name="check" />7</span><span className="shot__dur">24:10</span></Link>
            <div className="video__main"><span className="video__title">Как в сказке</span><span className="video__meta">7 серия, просмотрено вчера</span></div>
            <div className="video__actions"><button className="btn btn--small">Ещё раз</button></div>
          </li>
          <li className="video video--current ep">
            <Link className="shot shot--current shot--f1" to={R.tv} aria-label="Продолжить 8 серию"><div className="art art--a"></div><span className="shot__no">8</span><span className="shot__play"><Icon name="play" /></span><span className="shot__dur">осталось 11:30</span><span className="poster__bar"><span style={{ width: "52%" }}></span></span></Link>
            <div className="video__main"><span className="video__title">Фрирен-убийца</span><span className="video__meta num">8 серия, 12:40 из 24:10, сейчас на [TV] Samsung LED40</span></div>
            <div className="video__actions"><button className="btn btn--primary btn--small"><Icon name="play" />Продолжить</button><button className="icon-btn icon-btn--neutral" aria-label="Отметить просмотренной"><Icon name="check" /></button></div>
          </li>
          <li className="video ep">
            <Link className="shot shot--f2" to={R.tv} aria-label="9 серия"><div className="art art--a"></div><span className="shot__no">9</span><span className="shot__dur">24:10</span></Link>
            <div className="video__main"><span className="video__title">Аура Гильотина</span><span className="video__meta">9 серия, 1080p, H.264, 3 звуковые дорожки</span></div>
            <div className="video__actions"><button className="btn btn--small"><Icon name="play" />Показать</button><button className="icon-btn icon-btn--neutral" aria-label="Отметить просмотренной"><Icon name="check" /></button></div>
          </li>
          <li className="video ep">
            <span className="shot shot--f5"><div className="art art--a"></div><span className="shot__no">10</span><span className="shot__dur">24:10</span></span>
            <div className="video__main"><span className="video__title">Сильный маг</span><span className="video__meta">10 серия, перекодирую в H.264, 38%</span><div className="meter meter--thin"><span className="meter__fill" style={{ width: "38%" }}></span></div></div>
            <div className="video__actions"><span className="tag">скоро</span></div>
          </li>
          <li className="video ep">
            <span className="shot shot--none"><b>11</b><small>кадр после загрузки</small></span>
            <div className="video__main"><span className="video__title">Зима в северных землях</span><span className="video__meta">11 серия, скачиваю из торрента, 64%</span><div className="meter meter--thin"><span className="meter__fill" style={{ width: "64%" }}></span></div></div>
            <div className="video__actions"><span className="tag">скоро</span></div>
          </li>
          <li className="video ep ep--missing">
            <span className="shot shot--none"><b>13</b><small>нет на диске</small></span>
            <div className="video__main"><span className="video__title">Неприязнь к своим</span><span className="video__meta">13 серия, нет на диске</span></div>
            <div className="video__actions"><Link className="btn btn--small" to={R.sourceTitle}><Icon name="globe" />Взять с animego</Link><button className="btn btn--small"><Icon name="search" />Торрент</button></div>
          </li>
          <li className="eps__more"><button className="btn btn--quiet" style={{ alignSelf: "auto" }}>Показать ещё 15 серий</button></li>
        </ul>
        <p className="small muted" style={{ marginTop: "14px" }}>Кадр для серии беру из самого файла через ffmpeg, на пятой минуте, чтобы не попасть в заставку. Пока файла нет, вместо кадра номер.</p>
      </section>

      <NowBar />
    </main>
  );
}
