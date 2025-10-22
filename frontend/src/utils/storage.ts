/**
 * LocalStorage utility functions
 */

import type { User } from '../types';

// Auth token
export const getToken = (): string | null => {
  return localStorage.getItem('token');
};

export const setToken = (token: string): void => {
  localStorage.setItem('token', token);
};

export const removeToken = (): void => {
  localStorage.removeItem('token');
};

// User info
export const getUser = (): User | null => {
  const user = localStorage.getItem('user');
  return user ? JSON.parse(user) : null;
};

export const setUser = (user: User): void => {
  localStorage.setItem('user', JSON.stringify(user));
};

export const removeUser = (): void => {
  localStorage.removeItem('user');
};

// Clear all auth data
export const clearAuth = (): void => {
  removeToken();
  removeUser();
};

// Check if user is authenticated
export const isAuthenticated = (): boolean => {
  return !!getToken();
};
