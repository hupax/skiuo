import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { authAPI } from '../services/api';
import { getToken, setToken, getUser, setUser, clearAuth } from '../utils/storage';
import type { User, AuthResponse } from '../types';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUserState] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is already logged in
    const token = getToken();
    const savedUser = getUser();

    if (token && savedUser) {
      setUserState(savedUser);
    }

    setLoading(false);
  }, []);

  const login = async (username: string, password: string): Promise<void> => {
    try {
      const response: AuthResponse = await authAPI.login(username, password);

      const userData: User = {
        userId: response.userId,
        username: response.username,
        email: response.email,
      };

      setToken(response.token);
      setUser(userData);
      setUserState(userData);
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  };

  const register = async (username: string, email: string, password: string): Promise<void> => {
    try {
      const response: AuthResponse = await authAPI.register(username, email, password);

      const userData: User = {
        userId: response.userId,
        username: response.username,
        email: response.email,
      };

      setToken(response.token);
      setUser(userData);
      setUserState(userData);
    } catch (error) {
      console.error('Registration failed:', error);
      throw error;
    }
  };

  const logout = (): void => {
    clearAuth();
    setUserState(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        login,
        register,
        logout,
        loading,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};
