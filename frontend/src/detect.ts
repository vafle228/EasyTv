/** What the single "Добавить" field recognises in a pasted link. Only YouTube has a backend so far. */
export type SourceKind = "youtube" | "torrent" | "stream" | "playlist" | "site" | "unknown";

export function detectSource(input: string): SourceKind {
  const s = input.trim().toLowerCase();
  if (!s) return "unknown";
  if (s.startsWith("magnet:") || s.endsWith(".torrent")) return "torrent";
  if (/^https?:\/\/([a-z0-9-]+\.)*(youtube\.com|youtu\.be)\//.test(s)) return "youtube";
  if (/\.m3u8(\?|$)/.test(s)) return "stream";
  if (/\.m3u(\?|$)/.test(s)) return "playlist";
  if (/^https?:\/\/([a-z0-9-]+\.)*animego\./.test(s)) return "site";
  return "unknown";
}

export const NOT_YET: Record<Exclude<SourceKind, "youtube">, string> = {
  torrent: "Торренты появятся в следующей версии. Пока можно добавить ролик с YouTube или файл с компьютера.",
  stream: "Прямые потоки (эфир) появятся в следующей версии.",
  playlist: "Плейлисты каналов M3U появятся в следующей версии.",
  site: "Каталог animego появится в следующей версии.",
  unknown: "Поддерживаются ссылки на YouTube. Торренты, потоки m3u8, плейлисты M3U и animego появятся позже.",
};
