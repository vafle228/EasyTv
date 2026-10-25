import type {
  CatalogTitle,
  Collection,
  Episode,
  Playback,
  Resolved,
  SavedTitle,
  StreamRef,
  TitleDetails,
  Tv,
  Variant,
  Video,
} from "./types";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

function errorMessage(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((d) => (d && typeof d === "object" && "msg" in d ? String(d.msg) : String(d))).join("; ");
    }
  }
  return fallback;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      ...init,
      headers: init?.body ? { "Content-Type": "application/json", ...init.headers } : init?.headers,
    });
  } catch {
    throw new ApiError("Сервер EasyTv не отвечает. Проверьте, что он запущен.", 0);
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(errorMessage(body, `Ошибка ${response.status}`), response.status);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

const tvPath = (id: string) => `/api/tvs/${encodeURIComponent(id)}`;
const titlePath = (id: string) => `/api/catalog/titles/${encodeURIComponent(id)}`;
const post = (body: unknown): RequestInit => ({ method: "POST", body: JSON.stringify(body) });

export const api = {
  tvs: () => request<Tv[]>("/api/tvs"),
  refreshTvs: () => request<Tv[]>("/api/tvs/refresh", { method: "POST" }),
  addTv: (address: string) => request<Tv>("/api/tvs", { method: "POST", body: JSON.stringify({ address }) }),
  forgetTv: (id: string) => request<void>(tvPath(id), { method: "DELETE" }),
  tv: (id: string) => request<Tv>(tvPath(id)),
  playback: (id: string) => request<Playback>(`${tvPath(id)}/playback`),
  play: (id: string, videoId: string) =>
    request<Playback>(`${tvPath(id)}/play`, { method: "POST", body: JSON.stringify({ videoId }) }),
  pause: (id: string) => request<void>(`${tvPath(id)}/pause`, { method: "POST" }),
  resume: (id: string) => request<void>(`${tvPath(id)}/resume`, { method: "POST" }),
  stop: (id: string) => request<void>(`${tvPath(id)}/stop`, { method: "POST" }),

  playStream: (id: string, ref: StreamRef, title: string, translation: string | null) =>
    request<Playback>(`${tvPath(id)}/play-stream`, post({ ...ref, title, translation })),

  search: (q: string) => request<CatalogTitle[]>(`/api/catalog/search?q=${encodeURIComponent(q)}`),
  collections: () => request<Collection[]>("/api/catalog/collections"),
  collection: (id: string, page: number) =>
    request<CatalogTitle[]>(`/api/catalog/collections/${encodeURIComponent(id)}?page=${page}`),
  title: (id: string) => request<TitleDetails>(titlePath(id)),
  episodes: (id: string) => request<Episode[]>(`${titlePath(id)}/episodes`),
  variants: (id: string, episode: number) => request<Variant[]>(`${titlePath(id)}/variants?episode=${episode}`),
  /** Finds a fresh link for the browser player and remembers where the user is. */
  resolve: (ref: StreamRef, translation: string | null) =>
    request<Resolved>("/api/catalog/resolve", post({ ...ref, translation })),
  downloadEpisode: (ref: StreamRef, title: string) => request<Video>("/api/catalog/download", post({ ...ref, title })),

  cinema: () => request<SavedTitle[]>("/api/cinema"),
  saveTitle: (titleId: string) => request<SavedTitle>("/api/cinema", post({ titleId })),
  unsaveTitle: (titleId: string) => request<void>(`/api/cinema/${encodeURIComponent(titleId)}`, { method: "DELETE" }),

  videos: () => request<Video[]>("/api/videos"),
  addYoutube: (url: string) => request<Video>("/api/videos/youtube", { method: "POST", body: JSON.stringify({ url }) }),
  deleteVideo: (id: string) => request<void>(`/api/videos/${encodeURIComponent(id)}`, { method: "DELETE" }),

  /** Upload with progress reporting (fetch can't report upload progress). */
  upload: (file: File, onProgress: (fraction: number) => void) =>
    new Promise<Video>((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const form = new FormData();
      form.append("file", file);
      xhr.open("POST", "/api/videos/upload");
      xhr.responseType = "json";
      xhr.upload.onprogress = (e) => e.lengthComputable && onProgress(e.loaded / e.total);
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) resolve(xhr.response as Video);
        else reject(new ApiError(errorMessage(xhr.response, `Ошибка ${xhr.status}`), xhr.status));
      };
      xhr.onerror = () => reject(new ApiError("Не удалось отправить файл на сервер.", 0));
      xhr.send(form);
    }),
};
