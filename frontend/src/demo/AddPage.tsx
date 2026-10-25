import { useState } from "react";
import { AddField } from "../components/AddField";
import { DemoNote, useDemoControls } from "../components/Demo";
import { Icon } from "../components/Icons";
import { R } from "../routes";
import { Notice } from "../components/Notice";
import { Link, useRouter } from "../router";

/** The single "Добавить" field (YouTube works) and, below it, the mockup's examples of what else it will recognise. */
export function AddPage() {
  const ref = useDemoControls<HTMLElement>();
  const { navigate } = useRouter();
  const [problem, setProblem] = useState<string | null>(null);
  return (
    <main className="page" ref={ref}>
      <section className="card">
        <h1 className="label">Добавить</h1>
        <p className="lead">Одно поле на все источники. Вставьте ссылку, я сам пойму, что это, и предложу, что сделать.</p>
        <div style={{ marginTop: "20px" }}>
          <AddField
            onAdded={() => navigate(R.downloads)}
            onError={(text) => setProblem(text)}
          />
        </div>
        <p className="small muted" style={{ marginTop: "14px" }}>
          Сейчас скачиваются ролики с YouTube. Файл с компьютера можно загрузить на <Link to={R.tv}>странице телевизора</Link>.
        </p>
      </section>

      {problem && <Notice title="Пока не умею" text={problem} onClose={() => setProblem(null)} />}

      <DemoNote>Ниже пример подсказок из макетов: торренты, эфир и animego появятся позже.</DemoNote>
      <section className="card">
        <div className="section-head">
          <h2 className="label">Что я распознаю</h2>
          <span className="small muted">Под полем появляется одна такая подсказка</span>
        </div>
        <div className="detects">
          <div className="detect">
            <span className="video__badge video__badge--youtube"><Icon name="youtube" /></span>
            <div className="detect__body">
              <span className="detect__input">https://youtu.be/dQw4w9WgXcQ</span>
              <span className="detect__title">Ролик YouTube</span>
              <span className="detect__text">Скачаю в 1080p, H.264. Это видео играет на всех ваших телевизорах.</span>
              <div className="detect__actions"><button className="btn btn--primary btn--small"><Icon name="download" />Скачать</button></div>
            </div>
          </div>
          <div className="detect" style={{ boxShadow: "var(--raise-sm), inset 0 0 0 2px var(--blue)" }}>
            <span className="video__badge video__badge--torrent"><Icon name="magnet" /></span>
            <div className="detect__body">
              <span className="detect__input">magnet:?xt=urn:btih:9f3c2a…&amp;dn=Frieren.S01.1080p</span>
              <span className="detect__title">Торрент-раздача</span>
              <span className="detect__text">Прочитаю список файлов и покажу его. Похоже на «Фрирен», 1 сезон, разложу по сериям.</span>
              <div className="detect__actions"><Link className="btn btn--primary btn--small" to={R.torrent}><Icon name="list" />Выбрать файлы</Link></div>
            </div>
          </div>
          <div className="detect">
            <span className="video__badge video__badge--live"><Icon name="live" /></span>
            <div className="detect__body">
              <span className="detect__input">https://example.tv/live/news/index.m3u8</span>
              <span className="detect__title">Прямой поток</span>
              <span className="detect__text">Буду показывать как эфир: без перемотки и длительности. Для телевизора перепакую в MPEG-TS.</span>
              <div className="detect__actions"><Link className="btn btn--primary btn--small" to={R.live}><Icon name="play" />Включить на ТВ</Link><button className="btn btn--small">Сохранить канал</button></div>
            </div>
          </div>
          <div className="detect">
            <span className="video__badge video__badge--live"><Icon name="list" /></span>
            <div className="detect__body">
              <span className="detect__input">https://example.org/playlist/home.m3u</span>
              <span className="detect__title">Плейлист каналов M3U</span>
              <span className="detect__text">48 каналов. Добавлю их в «Эфир» отдельным плейлистом.</span>
              <div className="detect__actions"><button className="btn btn--primary btn--small"><Icon name="plus" />Добавить каналы</button></div>
            </div>
          </div>
          <div className="detect">
            <span className="video__badge video__badge--site"><Icon name="globe" /></span>
            <div className="detect__body">
              <span className="detect__input">https://animego.me/anime/dandadan-…</span>
              <span className="detect__title">Страница на animego</span>
              <span className="detect__text">Открою тайтл в каталоге: там можно выбрать озвучку, смотреть сразу или сохранить себе.</span>
              <div className="detect__actions"><Link className="btn btn--primary btn--small" to={R.catalog}><Icon name="globe" />Открыть в каталоге</Link></div>
            </div>
          </div>
          <div className="detect">
            <span className="video__badge video__badge--upload"><Icon name="file" /></span>
            <div className="detect__body">
              <span className="detect__input">Dune.Part.Two.2024.1080p.mkv, 12.8 ГБ</span>
              <span className="detect__title">Файл с компьютера</span>
              <span className="detect__text">Похоже на фильм «Дюна: Часть вторая» (2024). Положу в кинотеатр с описанием и постером.</span>
              <div className="detect__actions"><Link className="btn btn--primary btn--small" to={R.cinema}><Icon name="upload" />Загрузить в кинотеатр</Link><button className="btn btn--small">Просто в библиотеку</button></div>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
