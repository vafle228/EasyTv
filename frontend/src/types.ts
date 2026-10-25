export interface Tv {
  id: string;
  name: string;
  ip: string;
  manufacturer: string | null;
  model: string | null;
  online: boolean;
  lastSeen: string | null;
}

export type VideoSource = "upload" | "youtube" | "animego";
export type VideoStatus = "pending" | "downloading" | "ready" | "failed";

export interface Video {
  id: string;
  title: string;
  source: VideoSource;
  status: VideoStatus;
  progress: number;
  size: number | null;
  error: string | null;
  originUrl: string | null;
  createdAt: string;
}

export type PlaybackState = "playing" | "paused" | "stopped" | "transitioning" | "no_media" | "unknown";

export interface Playback {
  state: PlaybackState;
  videoId: string | null;
  positionS: number | null;
  durationS: number | null;
  /** Set when the TV shows an episode streamed from a site rather than a library video. */
  title: string | null;
  stream: StreamRef | null;
}

/** An episode on a site: title, episode number (0 for a movie), dub and player ("auto" picks the best). */
export interface StreamRef {
  titleId: string;
  episode: number;
  translationId: string;
  provider?: string;
}

export interface CatalogTitle {
  id: string;
  title: string;
  originalTitle: string | null;
  kind: string | null;
  year: string | null;
  rating: string | null;
  poster: string | null;
  saved: boolean;
}

export type TitleKind = "series" | "movie";

export interface SavedTitle {
  id: string;
  source: string;
  title: string;
  kind: TitleKind;
  poster: string | null;
  originalTitle: string | null;
  year: string | null;
  episodesTotal: number | null;
  genres: string[];
  translationId: string | null;
  translation: string | null;
  lastEpisode: number | null;
  watched: number[];
  addedAt: string;
  updatedAt: string | null;
}

export interface TitleDetails {
  id: string;
  source: string;
  title: string;
  kind: TitleKind;
  url: string | null;
  originalTitle: string | null;
  description: string | null;
  poster: string | null;
  genres: string[];
  year: string | null;
  episodesTotal: number | null;
  rating: number | null;
  studio: string | null;
  saved: SavedTitle | null;
}

export interface Episode {
  number: number;
  title: string | null;
  date: string | null;
}

export interface Variant {
  translationId: string;
  translation: string;
  providers: string[];
}

export interface Resolved {
  url: string;
  provider: string;
  quality: number | null;
}
