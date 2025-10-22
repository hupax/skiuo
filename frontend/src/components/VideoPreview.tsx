import React, { useEffect, useRef } from 'react';

interface VideoPreviewProps {
  stream: MediaStream | null;
}

const VideoPreview: React.FC<VideoPreviewProps> = ({ stream }) => {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream;
    }
  }, [stream]);

  return (
    <div style={{
      width: '100%',
      backgroundColor: '#000',
      borderRadius: '8px',
      overflow: 'hidden',
      position: 'relative'
    }}>
      {stream ? (
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          style={{
            width: '100%',
            height: 'auto',
            display: 'block'
          }}
        />
      ) : (
        <div style={{
          aspectRatio: '16/9',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#666',
          fontSize: '1.2rem'
        }}>
          摄像头未启动
        </div>
      )}
    </div>
  );
};

export default VideoPreview;
