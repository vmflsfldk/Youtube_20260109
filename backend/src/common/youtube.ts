import { fetch } from 'undici';

export interface YoutubeMeta {
  videoId: string;
}

export interface YoutubeVideoDetails {
  videoId: string;
  channelId: string;
  title: string;
  publishedAt: Date | null;
  durationSec: number | null;
}

export function parseYoutubeUrl(url: string): YoutubeMeta | null {
  try {
    const parsed = new URL(url);
    if (parsed.hostname.includes('youtu.be')) {
      const videoId = parsed.pathname.replace('/', '');
      return videoId ? { videoId } : null;
    }
    if (parsed.searchParams.has('v')) {
      const videoId = parsed.searchParams.get('v');
      return videoId ? { videoId } : null;
    }
    return null;
  } catch {
    return null;
  }
}

export async function fetchYoutubeVideoDetails(videoId: string): Promise<YoutubeVideoDetails | null> {
  const apiKey = process.env.YOUTUBE_API_KEY;
  if (!apiKey) {
    throw new Error('YOUTUBE_API_KEY is required');
  }
  const baseUrl = process.env.YOUTUBE_API_BASE_URL ?? 'https://www.googleapis.com/youtube/v3';
  const url = new URL(`${baseUrl}/videos`);
  url.searchParams.set('part', 'snippet,contentDetails');
  url.searchParams.set('id', videoId);
  url.searchParams.set('key', apiKey);

  const response = await fetch(url.toString());
  if (!response.ok) {
    throw new Error(`YouTube API error ${response.status}`);
  }

  const payload = (await response.json()) as {
    items?: Array<{
      id: string;
      snippet?: { channelId?: string; title?: string; publishedAt?: string };
      contentDetails?: { duration?: string };
    }>;
  };

  const item = payload.items?.[0];
  if (!item?.snippet?.channelId || !item.snippet.title) {
    return null;
  }

  return {
    videoId: item.id,
    channelId: item.snippet.channelId,
    title: item.snippet.title,
    publishedAt: item.snippet.publishedAt ? new Date(item.snippet.publishedAt) : null,
    durationSec: item.contentDetails?.duration
      ? parseIsoDuration(item.contentDetails.duration)
      : null,
  };
}

export function parseIsoDuration(duration: string): number | null {
  const match = duration.match(
    /^P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?$/,
  );
  if (!match) {
    return null;
  }
  const days = Number(match[1] ?? 0);
  const hours = Number(match[2] ?? 0);
  const minutes = Number(match[3] ?? 0);
  const seconds = Number(match[4] ?? 0);
  return (((days * 24 + hours) * 60 + minutes) * 60 + seconds) || 0;
}
