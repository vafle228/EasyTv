import { DemoNote, useDemoControls } from "../components/Demo";
import { Icon } from "../components/Icons";
import { R } from "../routes";
import { Link } from "../router";

/** Mockup screen «SourceTitle» with sample data: the backend for this section isn't built yet. */
export function SourceTitlePage() {
  const ref = useDemoControls<HTMLElement>();
  return (
    <main className="page" ref={ref}>
      <DemoNote />
      <Link className="btn btn--small back" to={R.catalog}><Icon name="back" />Каталог animego</Link>

      <section className="card">
        <div className="hero">
          <div className="poster"><div className="art art--c"><span className="art__word">Наруто</span></div></div>
          <div>
            <p className="label"><Icon name="globe" /> animego</p>
            <h1 className="hero__title">Наруто: Ураганные хроники</h1>
            <p className="hero__orig">Naruto: Shippuuden, 2007, ТВ</p>
            <div className="chips">
              <span className="chip chip--static">Экшен</span>
              <span className="chip chip--static">Приключения</span>
              <span className="chip chip--static">Сёнэн</span>
            </div>
            <p className="hero__text">Наруто возвращается в Деревню Листа после двух лет тренировок, а организация «Акацуки» начинает охоту на хвостатых зверей.</p>
            <dl className="facts facts--wide" style={{ maxWidth: "640px", marginTop: "20px" }}>
              <dt>Серий</dt><dd>500 из 500</dd>
              <dt>Озвучки</dt><dd>9 вариантов, 3 плеера</dd>
              <dt>Качество</dt><dd>до 1080p, MP4</dd>
              <dt>У вас</dt><dd>142 просмотрено, 3 на диске</dd>
            </dl>
            <div className="hero__actions">
              <Link className="btn btn--primary" to={R.tv}><Icon name="play" />Смотреть 143 серию</Link>
              <button className="btn"><Icon name="bookmark" />Сохранить 143–152</button>
              <Link className="tv-pick" to={R.pick}><span className="tv-pick__dot"><Icon name="tv" /></span><span>на [TV] Samsung LED40</span><Icon name="chevron" /></Link>
            </div>
            <p className="small muted" style={{ marginTop: "12px" }}>«Смотреть» пускает поток через сервер без скачивания. Все 500 серий сразу не предлагаю: это около 200 ГБ. Сохраняю по 10 вперёд от того места, где вы остановились.</p>
          </div>
        </div>
      </section>

      <section className="card">
        <h2 className="label">Озвучка и качество</h2>
        <div className="optgrid">
          <span className="optline">Озвучка</span>
          <Link className="select" to={R.voice}><span className="select__v">AniDUB, многоголосая</span><span className="tag">ещё 8</span><Icon name="chevron" /></Link>
          <span className="small muted hint">Если у серии нет AniDUB, возьму следующую из вашего списка: AniLibria, потом 2x2, потом субтитры. Список общий для всех тайтлов.</span>
          <span className="optline">Плеер</span>
          <button className="select"><span className="select__v">Авто: CVH, потом Kodik, потом Aniboom</span><span className="tag">3</span><Icon name="chevron" /></button>
          <span className="small muted hint">CVH и Kodik отдают готовый MP4, Aniboom только HLS: его перепаковываю для телевизора.</span>
          <span className="optline">Качество</span>
          <div className="segmented" role="radiogroup" aria-label="Качество">
            <button className="segmented__item" role="radio" aria-checked="false">480p</button>
            <button className="segmented__item" role="radio" aria-checked="false">720p</button>
            <button className="segmented__item" role="radio" aria-checked="true">1080p, если есть</button>
          </div>
        </div>
        <hr className="divider" />
        <span className="optline"><button className="check" role="checkbox" aria-checked="true" aria-label="Сохранять вперёд"><Icon name="check" /></button>Держать на диске 10 серий вперёд, просмотренные удалять через 7 дней</span>
      </section>

      <section className="card">
        <div className="section-head">
          <h2 className="label">Серии на сайте</h2>
          <span className="small muted">Озвучка AniDUB, 1080p. Кадры из плеера CVH.</span>
        </div>
        <div className="eptools">
          <div className="segmented scroller" role="radiogroup" aria-label="Диапазон серий">
            <button className="segmented__item" role="radio" aria-checked="false">1–100</button>
            <button className="segmented__item" role="radio" aria-checked="true">101–200</button>
            <button className="segmented__item" role="radio" aria-checked="false">201–300</button>
            <button className="segmented__item" role="radio" aria-checked="false">301–400</button>
            <button className="segmented__item" role="radio" aria-checked="false">401–500</button>
          </div>
          <div className="jump">
            <label className="field"><Icon name="search" /><input type="text" inputMode="numeric" placeholder="Серия №" aria-label="Перейти к серии" /></label>
          </div>
        </div>
        <ul className="eps">
          <li className="eps__more" style={{ padding: "0 0 4px" }}><button className="btn btn--quiet" style={{ alignSelf: "auto" }}>Показать 101–141, просмотрены</button></li>
          <li className="video ep ep--watched">
            <span className="shot shot--watched shot--f4"><div className="art art--c"></div><span className="shot__no"><Icon name="check" />142</span><span className="shot__dur">23:20</span></span>
            <div className="video__main"><span className="video__title">142 серия</span><span className="video__meta">Просмотрено 23 октября</span></div>
            <div className="video__actions"><span className="tag">удалю с диска 30 октября</span></div>
          </li>
          <li className="video video--current ep">
            <Link className="shot shot--current shot--f1" to={R.tv} aria-label="Продолжить 143 серию"><div className="art art--c"></div><span className="shot__no">143</span><span className="shot__play"><Icon name="play" /></span><span className="shot__dur">осталось 15:10</span><span className="poster__bar"><span style={{ width: "35%" }}></span></span></Link>
            <div className="video__main"><span className="video__title">143 серия</span><span className="video__meta">На диске, 8:10 из 23:20</span></div>
            <div className="video__actions"><button className="btn btn--primary btn--small"><Icon name="play" />Продолжить</button></div>
          </li>
          <li className="video ep">
            <span className="shot shot--f5"><div className="art art--c"></div><span className="shot__no">144</span><span className="shot__dur">23:20</span></span>
            <div className="video__main"><span className="video__title">144 серия</span><span className="video__meta">Сохраняю, 72%</span><div className="meter meter--thin"><span className="meter__fill" style={{ width: "72%" }}></span></div></div>
            <div className="video__actions"><button className="icon-btn" aria-label="Отменить"><Icon name="close" /></button></div>
          </li>
          <li className="video ep">
            <span className="shot shot--f2"><div className="art art--c"></div><span className="shot__no">145</span><span className="shot__dur">23:20</span></span>
            <div className="video__main"><span className="video__title">145 серия</span><span className="video__meta">На сайте. AniDUB нет, будет AniLibria</span></div>
            <div className="video__actions"><button className="btn btn--small"><Icon name="play" />Смотреть</button><button className="icon-btn icon-btn--neutral" aria-label="Сохранить серию"><Icon name="download" /></button></div>
          </li>
          <li className="video ep">
            <span className="shot shot--f6"><div className="art art--c"></div><span className="shot__no">146</span><span className="shot__dur">23:20</span></span>
            <div className="video__main"><span className="video__title">146 серия</span><span className="video__meta">На сайте, AniDUB</span></div>
            <div className="video__actions"><button className="btn btn--small"><Icon name="play" />Смотреть</button><button className="icon-btn icon-btn--neutral" aria-label="Сохранить серию"><Icon name="download" /></button></div>
          </li>
          <li className="video ep">
            <span className="shot shot--none"><b>147</b><small>кадр загружается</small></span>
            <div className="video__main"><span className="video__title">147 серия</span><span className="video__meta">На сайте, только субтитры и Aniboom</span></div>
            <div className="video__actions"><button className="btn btn--small"><Icon name="play" />Смотреть</button><button className="icon-btn icon-btn--neutral" aria-label="Сохранить серию"><Icon name="download" /></button></div>
          </li>
          <li className="eps__more"><button className="btn btn--quiet" style={{ alignSelf: "auto" }}>Показать ещё 53 серии, до 200</button></li>
        </ul>
      </section>
    </main>
  );
}
