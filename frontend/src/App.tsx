import React, { useMemo, useState } from 'react';
import Home from './pages/Home';
import VideoDetail from './pages/VideoDetail';

function getOrCreateGuestId(): string {
  const stored = window.localStorage.getItem('guestId');
  if (stored) {
    return stored;
  }
  const value = `guest_${crypto.randomUUID()}`;
  window.localStorage.setItem('guestId', value);
  return value;
}

export default function App() {
  const [currentVideo, setCurrentVideo] = useState<{ id: string; title: string } | null>(null);
  const guestId = useMemo(() => getOrCreateGuestId(), []);

  return (
    <div className="app">
      <header>
        <h1>VTuber Live Analyzer MVP</h1>
        <span className="badge">Guest: {guestId.slice(0, 8)}</span>
      </header>

      <Home
        onVideoReady={(id, title) => {
          setCurrentVideo({ id, title });
        }}
      />

      {currentVideo && (
        <VideoDetail videoId={currentVideo.id} title={currentVideo.title} userId={guestId} />
      )}
    </div>
  );
}
