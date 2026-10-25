const ARTS = ["a", "b", "c", "d", "e", "f", "g", "h"];

/** Placeholder artwork picked by id, so a title keeps the same colours everywhere. */
export function artFor(id: string): string {
  let h = 0;
  for (const ch of id) h = (h * 31 + ch.charCodeAt(0)) | 0;
  return `art art--${ARTS[Math.abs(h) % ARTS.length]}`;
}

/** Poster from the site when there is one, the system's placeholder art otherwise (and while it loads). */
export function PosterArt({ id, title, src }: { id: string; title: string; src: string | null }) {
  return (
    <>
      <div className={artFor(id)}>
        <span className="art__word">{title}</span>
      </div>
      {src && (
        <img
          className="poster__img"
          src={src}
          alt=""
          loading="lazy"
          referrerPolicy="no-referrer"
          onError={(e) => (e.currentTarget.style.display = "none")}
        />
      )}
    </>
  );
}
