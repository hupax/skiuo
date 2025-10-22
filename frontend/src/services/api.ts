import axios, { AxiosInstance } from 'axios';
import type { AuthResponse, Session } from '../types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: async (username: string, password: string): Promise<AuthResponse> => {
    const response = await api.post<AuthResponse>('/api/auth/login', { username, password });
    return response.data;
  },

  register: async (username: string, email: string, password: string): Promise<AuthResponse> => {
    const response = await api.post<AuthResponse>('/api/auth/register', { username, email, password });
    return response.data;
  },
};

// Session API
export const sessionAPI = {
  start: async (title?: string, description?: string): Promise<Session> => {
    const response = await api.post<Session>('/api/sessions/start', { title, description });
    return response.data;
  },

  stop: async (sessionId: string): Promise<Session> => {
    const response = await api.post<Session>(`/api/sessions/${sessionId}/stop`);
    return response.data;
  },

  getSession: async (sessionId: string): Promise<Session> => {
    const response = await api.get<Session>(`/api/sessions/${sessionId}`);
    return response.data;
  },

  getStatus: async (sessionId: string): Promise<Session> => {
    const response = await api.get<Session>(`/api/sessions/${sessionId}/status`);
    return response.data;
  },

  list: async (): Promise<Session[]> => {
    const response = await api.get<Session[]>('/api/sessions');
    return response.data;
  },
};

export default api;
