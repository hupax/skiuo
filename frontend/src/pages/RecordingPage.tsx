import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { sessionAPI } from '../services/api';
import VideoRecorderService from '../services/video-recorder';
import AnalysisWebSocket from '../services/websocket';
import VideoPreview from '../components/VideoPreview';
import AnalysisDisplay from '../components/AnalysisDisplay';
import { useAuth } from '../contexts/AuthContext';
import type { Session } from '../types';

const RecordingPage: React.FC = () => {
  const [session, setSession] = useState<Session | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [tokens, setTokens] = useState<string[]>([]);
  const [error, setError] = useState('');
  const [localStream, setLocalStream] = useState<MediaStream | null>(null);
  const [uploadedSegments, setUploadedSegments] = useState<number>(0);

  const videoRecorderService = useRef<VideoRecorderService | null>(null);
  const wsClient = useRef<AnalysisWebSocket | null>(null);

  const { user, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    return () => {
      // Cleanup on unmount
      stopRecording();
    };
  }, []);

  const startRecording = async () => {
    try {
      setError('');
      setTokens([]);
      setUploadedSegments(0);

      // 1. Create session via API
      const newSession = await sessionAPI.start('录制会话', 'AI视频分析');
      setSession(newSession);

      // 2. Get user media (camera + microphone)
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          frameRate: { ideal: 30 }
        },
        audio: false  // 暂时禁用音频
      });
      setLocalStream(stream);

      // 3. Initialize video recorder service
      videoRecorderService.current = new VideoRecorderService();
      await videoRecorderService.current.initialize(stream, {
        sessionId: newSession.id,
        segmentDuration: 30000,  // 30 秒一个片段
        onUploadSuccess: (response) => {
          console.log('Segment uploaded:', response);
          setUploadedSegments(prev => prev + 1);
        },
        onUploadError: (error) => {
          console.error('Upload error:', error);
          setError(`视频上传失败: ${error.message}`);
        },
        onSegmentRecorded: (segmentIndex) => {
          console.log('Segment recorded:', segmentIndex);
        }
      });

      videoRecorderService.current.startRecording();

      // 4. Connect WebSocket for analysis tokens
      wsClient.current = new AnalysisWebSocket();
      wsClient.current.connect(
        newSession.id,
        (token) => {
          setTokens(prev => [...prev, token]);
        },
        (err) => console.error('WebSocket error:', err)
      );

      setIsRecording(true);
      console.log('Recording started:', newSession.id);

    } catch (err: any) {
      console.error('Failed to start recording:', err);
      setError(err.response?.data?.message || err.message || '启动录制失败');
    }
  };

  const stopRecording = async () => {
    try {
      // 1. Stop video recorder
      if (videoRecorderService.current) {
        videoRecorderService.current.stopRecording();
        videoRecorderService.current.close();
        videoRecorderService.current = null;
      }

      // 2. Stop local stream
      if (localStream) {
        localStream.getTracks().forEach(track => track.stop());
        setLocalStream(null);
      }

      // 3. Stop session via API (but keep WebSocket open for remaining analysis)
      if (session) {
        await sessionAPI.stop(session.id);
        console.log('Recording stopped:', session.id);
        console.log('WebSocket remains open to receive remaining analysis results...');
      }

      setIsRecording(false);

      // 4. Delay closing WebSocket to allow remaining tasks to complete
      // WebSocket will be closed when user navigates away or after a timeout
      setTimeout(() => {
        if (wsClient.current) {
          console.log('Closing WebSocket after timeout');
          wsClient.current.close();
          wsClient.current = null;
        }
      }, 60000); // Keep open for 1 minute to receive remaining analysis

    } catch (err: any) {
      console.error('Failed to stop recording:', err);
      setError(err.response?.data?.message || err.message || '停止录制失败');
    }
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f5f5f5' }}>
      {/* Header */}
      <header style={{
        backgroundColor: 'white',
        padding: '1rem 2rem',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <h1 style={{ margin: 0, color: '#333' }}>StreamMind</h1>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <span style={{ color: '#666' }}>欢迎, {user?.username}</span>
          <button
            onClick={() => navigate('/history')}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#2196F3',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            历史记录
          </button>
          <button
            onClick={logout}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#f44336',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            退出登录
          </button>
        </div>
      </header>

      {/* Main Content */}
      <div style={{ padding: '2rem', maxWidth: '1400px', margin: '0 auto' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
          {/* Left: Video Preview */}
          <div>
            <h2 style={{ marginBottom: '1rem', color: '#333' }}>视频预览</h2>
            <VideoPreview stream={localStream} />

            {/* Controls */}
            <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'center', gap: '1rem' }}>
              {!isRecording ? (
                <button
                  onClick={startRecording}
                  style={{
                    padding: '1rem 2rem',
                    backgroundColor: '#4CAF50',
                    color: 'white',
                    border: 'none',
                    borderRadius: '8px',
                    fontSize: '1.1rem',
                    fontWeight: 'bold',
                    cursor: 'pointer',
                    boxShadow: '0 2px 8px rgba(76, 175, 80, 0.3)'
                  }}
                >
                  开始录制
                </button>
              ) : (
                <button
                  onClick={stopRecording}
                  style={{
                    padding: '1rem 2rem',
                    backgroundColor: '#f44336',
                    color: 'white',
                    border: 'none',
                    borderRadius: '8px',
                    fontSize: '1.1rem',
                    fontWeight: 'bold',
                    cursor: 'pointer',
                    boxShadow: '0 2px 8px rgba(244, 67, 54, 0.3)'
                  }}
                >
                  停止录制
                </button>
              )}
            </div>

            {/* Status */}
            {session && (
              <div style={{
                marginTop: '1rem',
                padding: '1rem',
                backgroundColor: isRecording ? '#e8f5e9' : '#fff3e0',
                borderRadius: '4px',
                textAlign: 'center'
              }}>
                <div style={{ color: '#666' }}>会话ID: {session.id}</div>
                <div style={{ color: isRecording ? '#4CAF50' : '#FF9800', fontWeight: 'bold', marginTop: '0.5rem' }}>
                  {isRecording ? '● 录制中' : '○ 已停止'}
                </div>
                {uploadedSegments > 0 && (
                  <div style={{ color: '#666', fontSize: '0.9rem', marginTop: '0.5rem' }}>
                    已上传片段: {uploadedSegments}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Right: AI Analysis */}
          <div>
            <h2 style={{ marginBottom: '1rem', color: '#333' }}>AI 实时分析</h2>
            <AnalysisDisplay tokens={tokens} />

            <div style={{ marginTop: '1rem', color: '#666', fontSize: '0.9rem' }}>
              已接收 Token: {tokens.length}
            </div>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div style={{
            marginTop: '1rem',
            padding: '1rem',
            backgroundColor: '#ffebee',
            color: '#c62828',
            borderRadius: '4px',
            textAlign: 'center'
          }}>
            错误: {error}
          </div>
        )}
      </div>
    </div>
  );
};

export default RecordingPage;
