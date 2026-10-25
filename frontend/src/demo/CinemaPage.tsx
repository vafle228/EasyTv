import { DemoNote, useDemoControls } from "../components/Demo";
import { Icon } from "../components/Icons";
import { NowBar } from "../components/NowBar";
import { R } from "../routes";
import { Link } from "../router";

/** Mockup screen «Cinema» with sample data: the backend for this section isn't built yet. */
export function CinemaPage() {
  const ref = useDemoControls<HTMLElement>();
  return (
    <main className="page" ref={ref}>
      <DemoNote />
      <section className="card">
        <div className="card__head" style={{ marginBottom: "22px" }}>
          <div>
            <h1 className="label">Кинотеатр</h1>
            <p className="muted">24 тайтла: 9 фильмов, 4 сериала, 11 аниме</p>
          </div>
          <div className="row">
            <Link className="btn" to={R.catalog}><Icon name="globe" />Найти на сайтах</Link>
            <Link className="btn" to={R.add}><Icon name="plus" />Добавить</Link>
          </div>
        </div>
        <div className="row row--between">
          <div className="segmented" role="radiogroup" aria-label="Тип">
            <button className="segmented__item" role="radio" aria-checked="true">Всё</button>
            <button className="segmented__item" role="radio" aria-checked="false">Фильмы</button>
            <button className="segmented__item" role="radio" aria-checked="false">Сериалы</button>
            <button className="segmented__item" role="radio" aria-checked="false">Аниме</button>
          </div>
          <label className="field" style={{ flex: "0 1 380px", minHeight: "48px" }}><Icon name="search" /><input type="text" placeholder="Найти в кинотеатре" aria-label="Найти в кинотеатре" /></label>
        </div>
        <div className="row row--between" style={{ marginTop: "20px" }}>
          <div className="chips chips--m-scroll">
            <button className="chip" aria-pressed="false">Смотрю</button>
            <button className="chip" aria-pressed="false">Не начато</button>
            <button className="chip" aria-pressed="false">Просмотрено</button>
            <button className="chip" aria-pressed="true">Фэнтези</button>
            <button className="chip" aria-pressed="false">Фантастика</button>
            <button className="chip" aria-pressed="false">Драма</button>
            <button className="chip" aria-pressed="false">Комедия</button>
            <button className="chip" aria-pressed="false">Все жанры, 18 <Icon name="chevron" /></button>
          </div>
          <button className="select select--sm"><span className="select__k">Порядок</span><span className="select__v">недавно добавленные</span><Icon name="chevron" /></button>
        </div>
      </section>

      <section className="card">
        <div className="section-head"><h2 className="label">Продолжить просмотр</h2></div>
        <div className="rail">
          <Link className="resume" to={R.title}>
            <div className="thumb"><div className="art art--a"></div><span className="thumb__play"><Icon name="play" /></span><span className="poster__bar"><span style={{ width: "52%" }}></span></span></div>
            <span className="resume__text"><span className="resume__title">Фрирен, провожающая в последний путь</span><span className="resume__meta">8 серия, осталось 11 мин</span></span>
          </Link>
          <Link className="resume" to={R.film}>
            <div className="thumb"><div className="art art--e"></div><span className="thumb__play"><Icon name="play" /></span><span className="poster__bar"><span style={{ width: "44%" }}></span></span></div>
            <span className="resume__text"><span className="resume__title">Дюна: Часть вторая</span><span className="resume__meta">1:12:40 из 2:46:00</span></span>
          </Link>
          <Link className="resume" to={R.title}>
            <div className="thumb"><div className="art art--h"></div><span className="thumb__play"><Icon name="play" /></span><span className="poster__bar"><span style={{ width: "8%" }}></span></span></div>
            <span className="resume__text"><span className="resume__title">Одни из нас</span><span className="resume__meta">Сериал, 1 сезон, 3 серия</span></span>
          </Link>
        </div>
      </section>

      <section className="card">
        <div className="section-head"><h2 className="label">Аниме</h2><Link className="link" to={R.cinema}>Все 11</Link></div>
        <div className="tiles">
          <Link className="tile" to={R.title}>
            <div className="poster"><div className="art art--a"><span className="art__word">Фрирен</span></div><span className="poster__badge">8 из 28</span><span className="poster__bar"><span style={{ width: "27%" }}></span></span></div>
            <span className="tile__name">Фрирен, провожающая в последний путь</span><span className="tile__meta">2023, 28 серий</span>
          </Link>
          <Link className="tile" to={R.title}>
            <div className="poster"><div className="art art--c"><span className="art__word">Магическая битва</span></div><span className="poster__badge">Новая серия</span></div>
            <span className="tile__name">Магическая битва</span><span className="tile__meta">2020, 2 сезона</span>
          </Link>
          <Link className="tile" to={R.title}>
            <div className="poster"><div className="art art--d"><span className="art__word">Дандадан</span></div><span className="poster__badge"><Icon name="download" />72%</span></div>
            <span className="tile__name">Дандадан</span><span className="tile__meta">2024, 3 из 12 на диске</span>
          </Link>
          <Link className="tile" to={R.title}>
            <div className="poster"><div className="art art--f"><span className="art__word">Человек-бензопила</span></div></div>
            <span className="tile__name">Человек-бензопила</span><span className="tile__meta">2022, 12 серий</span>
          </Link>
          <Link className="tile" to={R.film}>
            <div className="poster"><div className="art art--g"><span className="art__word">Твоё имя</span></div><span className="poster__badge"><Icon name="check" />Просмотрено</span></div>
            <span className="tile__name">Твоё имя</span><span className="tile__meta">Фильм, 2016</span>
          </Link>
          <Link className="tile tile--add" to={R.catalog}>
            <div className="poster"><span><Icon name="plus" />Найти аниме на animego</span></div>
          </Link>
        </div>
      </section>

      <section className="card">
        <div className="section-head"><h2 className="label">Фильмы</h2><Link className="link" to={R.cinema}>Все 9</Link></div>
        <div className="tiles">
          <Link className="tile" to={R.film}>
            <div className="poster"><div className="art art--e"><span className="art__word">Дюна: Часть вторая</span></div><span className="poster__bar"><span style={{ width: "44%" }}></span></span></div>
            <span className="tile__name">Дюна: Часть вторая</span><span className="tile__meta">2024, 2 ч 46 мин</span>
          </Link>
          <Link className="tile" to={R.film}>
            <div className="poster"><div className="art art--b"><span className="art__word">Интерстеллар</span></div><span className="poster__badge">Нет файла</span></div>
            <span className="tile__name">Интерстеллар</span><span className="tile__meta">2014, 2 ч 49 мин</span>
          </Link>
          <Link className="tile" to={R.film}>
            <div className="poster"><div className="art art--h"><span className="art__word">Бегущий по лезвию 2049</span></div></div>
            <span className="tile__name">Бегущий по лезвию 2049</span><span className="tile__meta">2017, 2 ч 43 мин</span>
          </Link>
          <Link className="tile" to={R.film}>
            <div className="poster"><div className="art art--c"><span className="art__word">Паразиты</span></div><span className="poster__badge"><Icon name="check" />Просмотрено</span></div>
            <span className="tile__name">Паразиты</span><span className="tile__meta">2019, 2 ч 12 мин</span>
          </Link>
          <Link className="tile" to={R.film}>
            <div className="poster"><div className="art art--d"><span className="art__word">Мастер и Маргарита</span></div></div>
            <span className="tile__name">Мастер и Маргарита</span><span className="tile__meta">2024, 2 ч 37 мин</span>
          </Link>
          <Link className="tile" to={R.film}>
            <div className="poster"><div className="art art--b"><span className="art__word">Начало</span></div></div>
            <span className="tile__name">Начало</span><span className="tile__meta">2010, 2 ч 28 мин</span>
          </Link>
        </div>
      </section>

      <NowBar />
    </main>
  );
}
