import { DemoNote, useDemoControls } from "../components/Demo";
import { Icon } from "../components/Icons";
import { R } from "../routes";
import { Link } from "../router";

/** Mockup screen «Catalog» with sample data: the backend for this section isn't built yet. */
export function CatalogPage() {
  const ref = useDemoControls<HTMLElement>();
  return (
    <main className="page" ref={ref}>
      <DemoNote />
      <section className="card">
        <div className="card__head" style={{ marginBottom: "22px" }}>
          <div>
            <h1 className="label">Каталоги</h1>
            <p className="muted">Листайте сайты и сохраняйте к себе. Сохранённое скачается и появится в кинотеатре.</p>
          </div>
          <span className="status status--on">animego отвечает</span>
        </div>
        <div className="row row--between">
          <div className="segmented" role="radiogroup" aria-label="Сайт">
            <button className="segmented__item" role="radio" aria-checked="true"><Icon name="globe" />animego</button>
            <button className="segmented__item" role="radio" aria-checked="false" disabled style={{ opacity: ".5" }}>Кинопоиск, скоро</button>
            <button className="segmented__item" role="radio" aria-checked="false"><Icon name="live" />Телеканалы</button>
          </div>
          <label className="field" style={{ flex: "0 1 420px", minHeight: "48px" }}><Icon name="search" /><input type="text" placeholder="Искать на animego" aria-label="Искать на animego" /></label>
        </div>
        <div className="row row--between" style={{ marginTop: "20px" }}>
          <div className="chips chips--m-scroll">
            <button className="chip" aria-pressed="true">Онгоинги</button>
            <button className="chip" aria-pressed="false">Новые серии</button>
            <button className="chip" aria-pressed="false">Популярное</button>
            <button className="chip" aria-pressed="false">Фильмы</button>
            <button className="chip" aria-pressed="false">Осень 2026</button>
          </div>
          <div className="row">
            <button className="select select--sm"><span className="select__k">Жанры</span><span className="select__v">любые</span><span className="tag">42</span><Icon name="chevron" /></button>
            <button className="select select--sm"><span className="select__k">Год</span><span className="select__v">любой</span><Icon name="chevron" /></button>
          </div>
        </div>
      </section>

      <section className="card">
        <div className="section-head"><h2 className="label">Онгоинги</h2><span className="small muted">Страница 1 из 6</span></div>
        <div className="tiles">
          <div className="tile">
            <Link className="poster" to={R.sourceTitle}><div className="art art--d"><span className="art__word">Дандадан</span></div><span className="poster__badge"><Icon name="check" />В кинотеатре</span></Link>
            <span className="tile__name">Дандадан</span><span className="tile__meta">ТВ, 2 сезон, 9 из 12</span>
            <div className="tile__actions"><Link className="btn btn--small" to={R.sourceTitle}>Открыть</Link></div>
          </div>
          <div className="tile">
            <Link className="poster" to={R.sourceTitle}><div className="art art--a"><span className="art__word">Фрирен</span></div><span className="poster__badge"><Icon name="check" />В кинотеатре</span></Link>
            <span className="tile__name">Фрирен, провожающая в последний путь</span><span className="tile__meta">ТВ, 2 сезон, 4 из 12</span>
            <div className="tile__actions"><Link className="btn btn--small" to={R.sourceTitle}>Открыть</Link></div>
          </div>
          <div className="tile">
            <Link className="poster" to={R.sourceTitle}><div className="art art--c"><span className="art__word">Магическая битва</span></div></Link>
            <span className="tile__name">Магическая битва</span><span className="tile__meta">ТВ, 3 сезон, 2 из 24</span>
            <div className="tile__actions"><button className="btn btn--small"><Icon name="bookmark" />Сохранить</button></div>
          </div>
          <div className="tile">
            <Link className="poster" to={R.sourceTitle}><div className="art art--h"><span className="art__word">Поднятие уровня</span></div></Link>
            <span className="tile__name">Поднятие уровня в одиночку</span><span className="tile__meta">ТВ, 2 сезон, 13 из 13</span>
            <div className="tile__actions"><button className="btn btn--small"><Icon name="bookmark" />Сохранить</button></div>
          </div>
          <div className="tile">
            <Link className="poster" to={R.sourceTitle}><div className="art art--f"><span className="art__word">Человек-бензопила</span></div><span className="poster__badge"><Icon name="download" />Сохраняю</span></Link>
            <span className="tile__name">Человек-бензопила: Резе</span><span className="tile__meta">Фильм, 2025</span>
            <div className="tile__actions"><span className="tag">в очереди загрузок</span></div>
          </div>
          <div className="tile">
            <Link className="poster" to={R.sourceTitle}><div className="art art--c"><span className="art__word">Наруто</span></div><span className="poster__badge">143 из 500</span><span className="poster__bar"><span style={{ width: "28%" }}></span></span></Link>
            <span className="tile__name">Наруто: Ураганные хроники</span><span className="tile__meta">ТВ, 500 серий</span>
            <div className="tile__actions"><Link className="btn btn--small" to={R.sourceTitle}>Продолжить</Link></div>
          </div>
          <div className="tile">
            <Link className="poster" to={R.sourceTitle}><div className="art art--b"><span className="art__word">Ван-Пис</span></div></Link>
            <span className="tile__name">Ван-Пис</span><span className="tile__meta">ТВ, 1100+ серий</span>
            <div className="tile__actions"><button className="btn btn--small"><Icon name="bookmark" />Сохранить</button></div>
          </div>
          <div className="tile">
            <Link className="poster" to={R.sourceTitle}><div className="art art--e"><span className="art__word">Аптекарь</span></div></Link>
            <span className="tile__name">Монолог фармацевта</span><span className="tile__meta">ТВ, 2 сезон, 24 из 24</span>
            <div className="tile__actions"><button className="btn btn--small"><Icon name="bookmark" />Сохранить</button></div>
          </div>
        </div>
        <div className="row" style={{ justifyContent: "center", marginTop: "28px" }}><button className="btn">Загрузить ещё</button></div>
      </section>

      <div className="notice notice--error" role="alert">
        <span className="notice__icon"><Icon name="bell" /></span>
        <div className="notice__body"><strong>Сайт не отвечает как обычно</strong><p>Так выглядит ошибка адаптера: animego мог поменять вёрстку или защиту. Ответ сервера: 403 Forbidden. Сохранённое в кинотеатре не пострадает.</p></div>
        <button className="btn btn--small"><Icon name="refresh" />Повторить</button>
      </div>
    </main>
  );
}
