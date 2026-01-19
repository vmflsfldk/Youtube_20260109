export interface YoutubeMeta {
  videoId: string;
  channelId?: string;
  title?: string;
}

export function parseYoutubeUrl(url: string): YoutubeMeta | null {
  try {
    const parsed = new URL(url);
    const channelId =
      parsed.searchParams.get('channelId') ??
      parsed.searchParams.get('channel') ??
      undefined;
    if (parsed.hostname.includes('youtu.be')) {
      const videoId = parsed.pathname.replace('/', '');
      return videoId ? { videoId, channelId } : null;
    }
    if (parsed.searchParams.has('v')) {
      const videoId = parsed.searchParams.get('v');
      return videoId ? { videoId, channelId } : null;
    }
    if (parsed.pathname.startsWith('/channel/')) {
      const id = parsed.pathname.split('/channel/')[1];
      return id ? { videoId: id, channelId } : null;
    }
    return null;
  } catch {
    return null;
  }
}
