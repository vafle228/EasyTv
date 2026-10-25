import { DemoNote, useDemoControls } from "../components/Demo";
import { Icon } from "../components/Icons";
import { R } from "../routes";
import { Link } from "../router";

/** Mockup screen «Film» with sample data: the backend for this section isn't built yet. */
export function FilmPage() {
  const ref = useDemoControls<HTMLElement>();
  return (
    <main className="page" ref={ref}>
      <DemoNote />
      <Link className="btn btn--small back" to={R.cinema}><Icon name="back" />Кинотеатр</Link>

      <section className="card">
        <div className="hero">
          <div className="poster"><div className="art art--e"><span className="art__word">Дюна: Часть вторая</span></div></div>
          <div>
            <p className="label">Фильм</p>
            <h1 className="hero__title">Дюна: Часть вторая</h1>
            <p className="hero__orig">Dune: Part Two, 2024</p>
            <div className="chips">
              <span className="chip chip--static">Фантастика</span>
              <span className="chip chip--static">Приключения</span>
              <span className="chip chip--static">Драма</span>
            </div>
            <p className="hero__text">Пол Атрейдес объединяется с фрименами, чтобы отомстить заговорщикам, уничтожившим его семью, и пытается не допустить будущего, которое видит в своих видениях.</p>
            <dl className="facts facts--wide" style={{ maxWidth: "640px", marginTop: "20px" }}>
              <dt>Режиссёр</dt><dd>Дени Вильнёв</dd>
              <dt>Длительность</dt><dd>2 ч 46 мин</dd>
              <dt>Оценка</dt><dd><Icon name="star" /> 8.5, IMDb</dd>
              <dt>Страна</dt><dd>США, Канада</dd>
            </dl>
            <div className="resume-line">
              <div className="meter"><span className="meter__fill" style={{ width: "44%" }}></span></div>
              <span className="timeline__time">1:12:40 / 2:46:00</span>
            </div>
            <div className="hero__actions">
              <Link className="btn btn--primary" to={R.tv}><Icon name="play" />Продолжить с 1:12:40</Link>
              <button className="btn">Сначала</button>
              <Link className="tv-pick" to={R.pick}><span className="tv-pick__dot"><Icon name="tv" /></span><span>на [TV] Samsung LED40</span><Icon name="chevron" /></Link>
            </div>
          </div>
        </div>
      </section>

      <div className="tv-layout" style={{ gridTemplateColumns: "minmax(0,1fr) minmax(0,1fr)" }}>
        <section className="card">
          <h2 className="label">Файл</h2>
          <dl className="facts" style={{ marginTop: "14px" }}>
            <dt>Имя</dt><dd>Dune.Part.Two.2024.1080p.mkv</dd>
            <dt>Размер</dt><dd>12.8 ГБ</dd>
            <dt>Видео</dt><dd>1080p, H.264, играет без перекодирования</dd>
            <dt>Звук</dt><dd>6 дорожек: русские, английская, комментарии</dd>
            <dt>Субтитры</dt><dd>9 дорожек</dd>
            <dt>Источник</dt><dd>торрент, раздаю до 1 : 1</dd>
          </dl>
          <div className="optgrid" style={{ gridTemplateColumns: "max-content minmax(0,1fr)", gap: "12px 16px" }}>
            <span className="optline small">Звук</span>
            <button className="select select--sm"><span className="select__v">Русский, дубляж, AAC 5.1</span><span className="tag">ещё 5</span><Icon name="chevron" /></button>
            <span className="optline small">Субтитры</span>
            <button className="select select--sm"><span className="select__v">Выкл</span><span className="tag">9</span><Icon name="chevron" /></button>
            <span className="small muted hint">Телевизор играет одну дорожку: выбранную оставляю в потоке при отдаче, остальные отрезаю.</span>
          </div>
          <div className="row" style={{ marginTop: "16px" }}>
            <button className="btn btn--small"><Icon name="folder" />Заменить файл</button>
            <button className="btn btn--quiet" style={{ alignSelf: "auto" }}><Icon name="trash" />Удалить файл</button>
          </div>
        </section>

        <section className="card">
          <h2 className="label">Описание и постер</h2>
          <p className="muted" style={{ marginTop: "6px" }}>Заполнено автоматически: нашёл в TMDB по имени файла. Если ошибся, выберите другой вариант или впишите вручную.</p>
          <ul className="videos" style={{ marginTop: "18px" }}>
            <li className="video video--current">
              <div className="poster" style={{ width: "46px", flex: "none", borderRadius: "10px" }}><div className="art art--e" style={{ borderRadius: "10px" }}></div></div>
              <div className="video__main"><span className="video__title">Дюна: Часть вторая</span><span className="video__meta">2024, Дени Вильнёв, выбрано</span></div>
            </li>
            <li className="video">
              <div className="poster" style={{ width: "46px", flex: "none", borderRadius: "10px" }}><div className="art art--b" style={{ borderRadius: "10px" }}></div></div>
              <div className="video__main"><span className="video__title">Дюна</span><span className="video__meta">2021, Дени Вильнёв</span></div>
              <div className="video__actions"><button className="btn btn--small">Выбрать</button></div>
            </li>
          </ul>
          <div className="row" style={{ marginTop: "16px" }}>
            <button className="btn btn--small"><Icon name="refresh" />Обновить из TMDB</button>
            <button className="btn btn--small"><Icon name="edit" />Изменить вручную</button>
          </div>
        </section>
      </div>
    </main>
  );
}
