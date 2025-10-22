import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { sessionAPI } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import type { Session } from '../types';

const HistoryPage: React.FC = () => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const { logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      setLoading(true);
      const data = await sessionAPI.list();
      setSessions(data);
    } catch (err: any) {
      setError(err.response?.data?.message || err.message || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('zh-CN');
  };

  const formatDuration = (seconds?: number) => {
    if (!seconds) return '未知';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}分${secs}秒`;
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
        <h1 style={{ margin: 0, color: '#333' }}>历史记录</h1>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <button
            onClick={() => navigate('/')}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#4CAF50',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            返回录制
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

      {/* Content */}
      <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: '#666' }}>
            加载中...
          </div>
        ) : error ? (
          <div style={{
            padding: '1rem',
            backgroundColor: '#ffebee',
            color: '#c62828',
            borderRadius: '4px',
            textAlign: 'center'
          }}>
            {error}
          </div>
        ) : sessions.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: '#666' }}>
            暂无录制记录
          </div>
        ) : (
          <div style={{ display: 'grid', gap: '1rem' }}>
            {sessions.map((session) => (
              <div
                key={session.id}
                style={{
                  backgroundColor: 'white',
                  padding: '1.5rem',
                  borderRadius: '8px',
                  boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                  <div style={{ flex: 1 }}>
                    <h3 style={{ margin: '0 0 0.5rem 0', color: '#333' }}>
                      {session.title || '未命名会话'}
                    </h3>
                    {session.description && (
                      <p style={{ margin: '0 0 0.5rem 0', color: '#666' }}>
                        {session.description}
                      </p>
                    )}
                    <div style={{ fontSize: '0.9rem', color: '#999' }}>
                      <div>会话ID: {session.id}</div>
                      <div>开始时间: {formatDate(session.startTime)}</div>
                      {session.endTime && (
                        <div>结束时间: {formatDate(session.endTime)}</div>
                      )}
                      {session.durationSeconds !== undefined && (
                        <div>时长: {formatDuration(session.durationSeconds)}</div>
                      )}
                    </div>
                  </div>

                  <div style={{
                    padding: '0.5rem 1rem',
                    borderRadius: '4px',
                    fontSize: '0.9rem',
                    fontWeight: 'bold',
                    ...getStatusStyle(session.status)
                  }}>
                    {getStatusText(session.status)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

const getStatusStyle = (status: string) => {
  switch (status) {
    case 'ACTIVE':
      return { backgroundColor: '#e8f5e9', color: '#4CAF50' };
    case 'COMPLETED':
      return { backgroundColor: '#e3f2fd', color: '#2196F3' };
    case 'ERROR':
      return { backgroundColor: '#ffebee', color: '#f44336' };
    default:
      return { backgroundColor: '#f5f5f5', color: '#666' };
  }
};

const getStatusText = (status: string) => {
  switch (status) {
    case 'CREATED': return '已创建';
    case 'ACTIVE': return '进行中';
    case 'STOPPED': return '已停止';
    case 'COMPLETED': return '已完成';
    case 'ERROR': return '错误';
    default: return status;
  }
};

export default HistoryPage;
