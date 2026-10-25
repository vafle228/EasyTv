import { DemoNote, useDemoControls } from "../components/Demo";
import { Icon } from "../components/Icons";

/** Mockup screen «Live» with sample data: the backend for this section isn't built yet. */
export function LivePage() {
  const ref = useDemoControls<HTMLElement>();
  return (
    <main className="page" ref={ref}>
      <DemoNote />
      <div className="tv-layout">
        <section className="card now">
          <h1 className="label">Сейчас на экране</h1>
          <div className="tv tv--hero tv--on"><div className="tv__frame"><div className="tv__screen"><div className="screen-content"><span className="screen-content__state screen-live">В эфире</span><span className="screen-content__title">Новости 24</span><span className="screen-content__state" style={{ letterSpacing: ".08em", textTransform: "none", fontSize: ".95rem" }}>Плейлист «Дом», канал 3</span></div></div></div><div className="tv__stand"></div></div>
          <div className="liveline">
            <div className="liveline__track" aria-hidden="true"></div>
            <span className="tag tag--live">прямой эфир</span>
          </div>
          <div className="remote">
            <button className="round-btn" aria-label="Предыдущий канал"><Icon name="prev" /></button>
            <button className="round-btn round-btn--primary" aria-label="Стоп"><Icon name="stop" /></button>
            <button className="round-btn" aria-label="Следующий канал"><Icon name="next" /></button>
          </div>
          <p className="small muted" style={{ textAlign: "center", marginTop: "14px" }}>У эфира нет длительности и перемотки, поэтому вместо паузы здесь стоп и переключение каналов.</p>
        </section>

        <section className="card about">
          <h2 className="label">Поток</h2>
          <span className="about__name">Новости 24</span>
          <span className="status status--on">Идёт, 34 мин</span>
          <dl className="facts">
            <dt>Источник</dt><dd>m3u8, плейлист «Дом»</dd>
            <dt>Для ТВ</dt><dd>перепаковываю в MPEG-TS</dd>
            <dt>Качество</dt><dd>720p, 2.4 Мбит/с</dd>
            <dt>Телевизор</dt><dd>[TV] Samsung LED40</dd>
          </dl>
          <button className="btn btn--small"><Icon name="phone" />Смотреть в браузере</button>
        </section>
      </div>

      <section className="card">
        <div className="card__head" style={{ marginBottom: "22px" }}>
          <div>
            <h2 className="label">Каналы</h2>
            <p className="muted">51 канал в двух плейлистах. Недоступные проверяю раз в час.</p>
          </div>
          <div className="segmented" role="radiogroup" aria-label="Плейлист">
            <button className="segmented__item" role="radio" aria-checked="true">Дом, 48</button>
            <button className="segmented__item" role="radio" aria-checked="false">Добавленные, 3</button>
            <button className="segmented__item" role="radio" aria-checked="false">Избранное</button>
          </div>
        </div>
        <div className="add" style={{ marginBottom: "18px" }}>
          <label className="field"><Icon name="link" /><input type="text" placeholder="Ссылка на поток .m3u8 или плейлист .m3u" aria-label="Ссылка на поток или плейлист" /></label>
          <button className="btn btn--primary"><Icon name="plus" />Добавить</button>
        </div>
        <div className="row row--between" style={{ marginBottom: "24px" }}>
          <label className="field" style={{ flex: "0 1 340px", minHeight: "46px" }}><Icon name="search" /><input type="text" placeholder="Найти канал" aria-label="Найти канал" /></label>
          <div className="chips chips--m-scroll">
            <button className="chip" aria-pressed="true">Все 48</button>
            <button className="chip" aria-pressed="false">Новости 6</button>
            <button className="chip" aria-pressed="false">Кино 9</button>
            <button className="chip" aria-pressed="false">Документальное 7</button>
            <button className="chip" aria-pressed="false">Спорт 5</button>
            <button className="chip" aria-pressed="false">Ещё 6 групп <Icon name="chevron" /></button>
          </div>
        </div>
        <div className="channels">
          <button className="channel channel--current">
            <div className="tv tv--on tv--mini"><div className="tv__frame"><div className="tv__screen"><span className="tv__brand">Новости 24</span></div></div></div>
            <span className="channel__name">Новости 24</span><span className="channel__meta">Новости, сейчас на ТВ</span>
          </button>
          <button className="channel">
            <div className="tv tv--on tv--mini"><div className="tv__frame"><div className="tv__screen"><span className="tv__brand">Кино HD</span></div></div></div>
            <span className="channel__name">Кино HD</span><span className="channel__meta">Фильмы, 1080p</span>
          </button>
          <button className="channel">
            <div className="tv tv--on tv--mini"><div className="tv__frame"><div className="tv__screen"><span className="tv__brand">Природа</span></div></div></div>
            <span className="channel__name">Природа</span><span className="channel__meta">Документальное, 720p</span>
          </button>
          <button className="channel">
            <div className="tv tv--on tv--mini"><div className="tv__frame"><div className="tv__screen"><span className="tv__brand">Музыка</span></div></div></div>
            <span className="channel__name">Музыка</span><span className="channel__meta">Клипы, 720p</span>
          </button>
          <button className="channel">
            <div className="tv tv--on tv--mini"><div className="tv__frame"><div className="tv__screen"><span className="tv__brand">Детский</span></div></div></div>
            <span className="channel__name">Детский</span><span className="channel__meta">Мультфильмы, 576p</span>
          </button>
          <button className="channel">
            <div className="tv tv--on tv--mini"><div className="tv__frame"><div className="tv__screen"><span className="tv__brand">Спорт</span></div></div></div>
            <span className="channel__name">Спорт</span><span className="channel__meta">Трансляции, 1080p</span>
          </button>
          <button className="channel" disabled style={{ opacity: ".6" }}>
            <div className="tv tv--off tv--mini"><div className="tv__frame"><div className="tv__screen"><span className="tv__hint">нет сигнала</span></div></div></div>
            <span className="channel__name">Наука</span><span className="channel__meta danger">Недоступен, 404</span>
          </button>
          <button className="channel">
            <div className="tv tv--on tv--mini"><div className="tv__frame"><div className="tv__screen"><span className="tv__brand">Путешествия</span></div></div></div>
            <span className="channel__name">Путешествия</span><span className="channel__meta">Документальное, 720p</span>
          </button>
        </div>
        <div className="row" style={{ justifyContent: "center", marginTop: "24px" }}><button className="btn">Показать ещё 40 каналов</button></div>
        <p className="small muted" style={{ textAlign: "center", marginTop: "10px" }}>Группы беру из group-title в плейлисте. В больших плейлистах бывают тысячи каналов, поэтому показываю по 8 и ищу по названию.</p>
      </section>
    </main>
  );
}
