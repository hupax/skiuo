// Type definitions for StreamMind frontend

export interface User {
  userId: string;
  username: string;
  email: string;
}

export interface AuthResponse {
  userId: string;
  username: string;
  email: string;
  token: string;
}

export interface Session {
  id: string;
  userId: string;
  status: 'CREATED' | 'ACTIVE' | 'STOPPED' | 'COMPLETED' | 'ERROR';
  startTime: string;
  endTime?: string;
  durationSeconds?: number;
  title?: string;
  description?: string;
  signalingUrl?: string;
}

export interface AnalysisRecord {
  id: number;
  sessionId: string;
  content: string;
  tokenIndex: number;
  timestamp: number;
}
