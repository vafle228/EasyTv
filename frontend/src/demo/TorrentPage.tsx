import { DemoNote, useDemoControls } from "../components/Demo";
import { Icon } from "../components/Icons";
import { R } from "../routes";
import { Link } from "../router";

/** Mockup screen «Torrent» with sample data: the backend for this section isn't built yet. */
export function TorrentPage() {
  const ref = useDemoControls<HTMLElement>();
  return (
    <main className="page" ref={ref}>
      <DemoNote />
      <Link className="btn btn--small back" to={R.add}><Icon name="back" />Добавить</Link>

      <section className="card">
        <div className="card__head">
          <div className="row" style={{ alignItems: "flex-start", gap: "18px" }}>
            <span className="video__badge video__badge--torrent" style={{ width: "56px", height: "56px" }}><Icon name="magnet" /></span>
            <div>
              <p className="label">Торрент-раздача</p>
              <h1 className="title">Frieren.S01.1080p.WEB-DL.HEVC</h1>
              <p className="muted">28 файлов, 38.6 ГБ, 412 раздающих</p>
            </div>
          </div>
          <span className="tag tag--blue"><Icon name="check" />Список файлов получен</span>
        </div>

        <div className="notice notice--info">
          <span className="notice__icon"><Icon name="bell" /></span>
          <div className="notice__body"><strong>Видео в HEVC</strong><p>[TV] Samsung LED40 (2013) его не покажет. После загрузки перекодирую в H.264, на серию уходит около 6 минут.</p></div>
        </div>

        <h2 className="label">Куда положить</h2>
        <dl className="facts facts--wide" style={{ marginTop: "12px" }}>
          <dt>Карточка</dt><dd>Фрирен, провожающая в последний путь <span className="tag" style={{ marginLeft: "6px" }}>нашёл сам</span></dd>
          <dt>Сезон</dt><dd>1 сезон</dd>
          <dt>Серии</dt><dd>по номеру в имени файла</dd>
          <dt>Субтитры</dt><dd>подключу к серии с тем же номером</dd>
        </dl>
        <div className="row" style={{ marginTop: "14px" }}>
          <button className="btn btn--small"><Icon name="edit" />Выбрать другую карточку</button>
          <button className="btn btn--small"><Icon name="plus" />Новая карточка</button>
        </div>
      </section>

      <section className="card">
        <div className="section-head">
          <div className="row">
            <span className="optline"><button className="check" role="checkbox" aria-checked="mixed" aria-label="Выбрать все"><Icon name="minus" /></button>Выбрать все</span>
            <div className="chips chips--m-scroll">
              <button className="chip" aria-pressed="true">Видео 24</button>
              <button className="chip" aria-pressed="true">Субтитры 4</button>
              <button className="chip" aria-pressed="false">Папка Extras 6</button>
            </div>
          </div>
          <span className="num"><strong>Выбрано 12 из 28</strong> <span className="muted">16.4 ГБ</span></span>
        </div>
        <div className="row" style={{ marginBottom: "18px" }}>
          <label className="field" style={{ flex: "0 1 420px", minHeight: "46px" }}><Icon name="search" /><input type="text" placeholder="Найти файл, например 13 или NCOP" aria-label="Найти файл" /></label>
          <button className="btn btn--small">Выбрать серии 1–12</button>
        </div>
        <ul className="files">
          <li className="file">
            <button className="check" role="checkbox" aria-checked="true" aria-label="Скачать файл"><Icon name="check" /></button>
            <div className="video__main"><span className="video__title">Frieren - 01 [1080p].mkv</span><span className="video__meta">1.4 ГБ, MKV, HEVC</span></div>
            <div className="file__map"><span className="tag">перекодирую</span><span className="tag tag--blue">1 серия</span></div>
          </li>
          <li className="file">
            <button className="check" role="checkbox" aria-checked="true" aria-label="Скачать файл"><Icon name="check" /></button>
            <div className="video__main"><span className="video__title">Frieren - 02 [1080p].mkv</span><span className="video__meta">1.4 ГБ, MKV, HEVC</span></div>
            <div className="file__map"><span className="tag">перекодирую</span><span className="tag tag--blue">2 серия</span></div>
          </li>
          <li className="file">
            <button className="check" role="checkbox" aria-checked="true" aria-label="Скачать файл"><Icon name="check" /></button>
            <div className="video__main"><span className="video__title">Frieren - 03 [1080p].mkv</span><span className="video__meta">1.3 ГБ, MKV, HEVC</span></div>
            <div className="file__map"><span className="tag">перекодирую</span><span className="tag tag--blue">3 серия</span></div>
          </li>
          <li className="file">
            <button className="check" role="checkbox" aria-checked="true" aria-label="Скачать файл"><Icon name="check" /></button>
            <div className="video__main"><span className="video__title">Subs/Frieren - 01.rus.ass</span><span className="video__meta">48 КБ, субтитры, русские</span></div>
            <div className="file__map"><span className="tag tag--blue"><Icon name="subs" />к 1 серии</span></div>
          </li>
          <li className="file file--off">
            <button className="check" role="checkbox" aria-checked="false" aria-label="Скачать файл"><Icon name="check" /></button>
            <div className="video__main"><span className="video__title">Frieren - 13 [1080p].mkv</span><span className="video__meta">1.4 ГБ, MKV, HEVC</span></div>
            <div className="file__map"><span className="tag">13 серия</span></div>
          </li>
          <li className="file file--off">
            <button className="check" role="checkbox" aria-checked="false" aria-label="Скачать файл"><Icon name="check" /></button>
            <div className="video__main"><span className="video__title">Extras/NCOP.mkv</span><span className="video__meta">210 МБ, MKV, HEVC</span></div>
            <div className="file__map"><span className="tag">не серия, пропущу</span></div>
          </li>
        </ul>
        <p className="eps__more"><button className="btn btn--quiet" style={{ alignSelf: "auto" }}>Показать ещё 22 файла</button></p>
      </section>

      <section className="card">
        <h2 className="label">Настройки загрузки</h2>
        <div className="stack" style={{ marginTop: "18px" }}>
          <div className="row row--between">
            <span className="optline">Раздавать после загрузки</span>
            <div className="segmented" role="radiogroup" aria-label="Раздача">
              <button className="segmented__item" role="radio" aria-checked="false">Нет</button>
              <button className="segmented__item" role="radio" aria-checked="true">До 1 : 1</button>
              <button className="segmented__item" role="radio" aria-checked="false">Всегда</button>
            </div>
          </div>
          <div className="row row--between">
            <span className="optline">После просмотра</span>
            <div className="segmented" role="radiogroup" aria-label="После просмотра">
              <button className="segmented__item" role="radio" aria-checked="true">Оставить файлы</button>
              <button className="segmented__item" role="radio" aria-checked="false">Удалить через 7 дней</button>
            </div>
          </div>
          <div className="row row--between">
            <span className="optline"><button className="check" role="checkbox" aria-checked="true" aria-label="Качать по порядку"><Icon name="check" /></button>Качать серии по порядку, чтобы первую можно было смотреть раньше</span>
          </div>
        </div>
        <hr className="divider" />
        <div className="row row--between">
          <div className="grow" style={{ maxWidth: "420px" }}>
            <span className="small muted num">На диске свободно 212 ГБ из 931 ГБ, после загрузки останется 196 ГБ</span>
            <div className="meter" style={{ height: "10px", marginTop: "8px" }}><span className="meter__fill" style={{ width: "77%", inset: "2px auto 2px 2px" }}></span></div>
          </div>
          <div className="row">
            <button className="btn">Отмена</button>
            <Link className="btn btn--primary" to={R.downloads}><Icon name="download" />Скачать 12 файлов</Link>
          </div>
        </div>
      </section>
    </main>
  );
}
