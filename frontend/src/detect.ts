/** Route pasted URLs to YouTube, direct-file detection on the server, or a source hint. */
export type SourceKind = "youtube" | "direct" | "torrent" | "stream" | "playlist" | "unknown";

const YOUTUBE = /^(?:(?:(?:www|m|music)\.)?youtube\.com\/(?:watch\?|shorts\/|live\/|embed\/)|youtu\.be\/).+/i;

export function detectSource(input: string): SourceKind {
  const s = input.trim();
  if (/^magnet:/i.test(s)) return "torrent";
  if (!/^https?:\/\//i.test(s)) return "unknown";

  try {
    const { hostname, pathname, search } = new URL(s);
    const path = pathname.toLowerCase();
    if (path.endsWith(".torrent")) return "torrent";
    if (path.endsWith(".m3u8")) return "stream";
    if (path.endsWith(".m3u")) return "playlist";
    return YOUTUBE.test(hostname + pathname + search) ? "youtube" : "direct";
  } catch {
    return "unknown";
  }
}

export const NOT_YET: Record<Exclude<SourceKind, "youtube" | "direct">, string> = {
  torrent: "Торренты появятся в следующей версии. Пока можно добавить ролик с YouTube или видеофайл.",
  stream: "Прямые потоки (эфир) появятся в следующей версии.",
  playlist: "Плейлисты каналов M3U появятся в следующей версии.",
  unknown: "Вставьте полную ссылку на YouTube или видеофайл, начиная с http:// или https://.",
};
