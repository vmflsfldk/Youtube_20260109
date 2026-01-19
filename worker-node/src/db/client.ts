import { Pool } from 'pg';

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});

export async function withClient<T>(fn: (client: Pool) => Promise<T>): Promise<T> {
  return fn(pool);
}

export async function updateJobStatus(jobId: string, status: string, progress: number, errorMessage?: string) {
  await pool.query(
    'UPDATE analysis_jobs SET status = $1, progress = $2, error_message = $3, updated_at = NOW() WHERE id = $4',
    [status, progress, errorMessage ?? null, jobId],
  );
}

export async function insertSegments(
  videoId: string,
  segments: Array<{ songId: string; startSec: number; endSec: number; confidence: number; evidence?: Record<string, unknown> }>,
) {
  const queries = segments.map((segment) =>
    pool.query(
      'INSERT INTO video_song_segments (video_id, song_id, start_sec, end_sec, confidence, evidence) VALUES ($1, $2, $3, $4, $5, $6)',
      [videoId, segment.songId, segment.startSec, segment.endSec, segment.confidence, segment.evidence ?? null],
    ),
  );
  await Promise.all(queries);
}

export async function getFallbackSongId(): Promise<string | null> {
  const result = await pool.query('SELECT id FROM songs ORDER BY title ASC LIMIT 1');
  return result.rows[0]?.id ?? null;
}
