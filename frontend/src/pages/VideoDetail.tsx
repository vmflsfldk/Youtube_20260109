import React, { useEffect, useState } from 'react';
import { createClip, getSegments, listClips, Segment, Clip } from '../api/client';
import SegmentTable from '../components/SegmentTable';
import ClipModal from '../components/ClipModal';
import ClipList from '../components/ClipList';

interface VideoDetailProps {
  videoId: string;
  title: string;
  userId: string;
}

export default function VideoDetail({ videoId, title, userId }: VideoDetailProps) {
  const [segments, setSegments] = useState<Segment[]>([]);
  const [clips, setClips] = useState<Clip[]>([]);
  const [selected, setSelected] = useState<Segment | null>(null);

  const loadSegments = async () => {
    const data = await getSegments(videoId);
    setSegments(data);
  };

  const loadClips = async () => {
    const data = await listClips(videoId);
    setClips(data);
  };

  useEffect(() => {
    loadSegments();
    loadClips();
  }, [videoId]);

  const handleSubmitClip = async (payload: {
    title: string;
    visibility: string;
    startSec: number;
    endSec: number;
  }) => {
    if (!selected) {
      return;
    }
    await createClip({
      videoId,
      segmentId: selected.id,
      userId,
      startSec: payload.startSec,
      endSec: payload.endSec,
      title: payload.title,
      visibility: payload.visibility,
    });
    setSelected(null);
    await loadClips();
  };

  return (
    <div className="card">
      <div className="flex">
        <h2>{title}</h2>
        <span className="badge">Video ID: {videoId.slice(0, 6)}</span>
      </div>
      <h3>세그먼트 타임라인</h3>
      <SegmentTable segments={segments} onSelect={setSelected} />

      <h3>클립 리스트</h3>
      <ClipList clips={clips} />

      {selected && (
        <ClipModal
          segment={selected}
          onClose={() => setSelected(null)}
          onSubmit={handleSubmitClip}
        />
      )}
    </div>
  );
}
