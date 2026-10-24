export interface Tv {
  id: string;
  name: string;
  ip: string;
  manufacturer: string | null;
  model: string | null;
  online: boolean;
  lastSeen: string | null;
}

export type VideoSource = "upload" | "youtube";
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
}
