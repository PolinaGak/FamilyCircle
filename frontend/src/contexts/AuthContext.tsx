// src/contexts/AuthContext.tsx
import React, { createContext, useState, useContext, useEffect, ReactNode } from 'react';
import { authAPI, User as APIUser, LoginResponse } from '../api/auth';

export interface User {
  id: string;
  email: string;
  name: string;
}


interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // При загрузке приложения проверяем, есть ли сохраненный пользователь
useEffect(() => {
  const checkAuth = async () => {
    try {
      const storedUser = localStorage.getItem('user');
      const token = localStorage.getItem('token');
      
      if (storedUser && token) {
        // Пробуем получить актуальные данные с сервера
        try {
          const userResponse = await authAPI.getMe();
          setUser(userResponse.data);
          // Обновляем localStorage актуальными данными
          localStorage.setItem('user', JSON.stringify(userResponse.data));
        } catch {
          localStorage.removeItem('token');
          localStorage.removeItem('user');
          setUser(null);
        }
      }
    } catch (error) {
      console.error('Ошибка при проверке аутентификации:', error);
    } finally {
      setIsLoading(false);
    }
  };

  checkAuth();
}, []);

  // Функция входа 
  const login = async (email: string, password: string): Promise<void> => {
    setIsLoading(true);
    try {
      const response = await authAPI.login(email, password);
      const { access_token, user } = response.data;  
      
      localStorage.setItem('token', access_token);
      localStorage.setItem('user', JSON.stringify(user));
      setUser(user);
      
      console.log('Успешный вход:', user);
    } catch (error: any) {
      console.error('Ошибка входа:', error);
      localStorage.removeItem('token');
      
      if (error.response?.data?.detail) {
        throw new Error(error.response.data.detail);
      }
      throw new Error('Ошибка соединения с сервером');
    } finally {
      setIsLoading(false);
    }
  };
  // Функция регистрации
    const register = async (name: string, email: string, password: string): Promise<void> => {
    setIsLoading(true);
    try {
      const response = await authAPI.register(name, email, password);
      console.log('Регистрация успешна, требуется подтверждение email');
      
    } catch (error: any) {
      console.error('Ошибка регистрации:', error);
      if (error.response?.data?.detail) {
        throw new Error(error.response.data.detail);
      }
      throw new Error('Ошибка соединения с сервером');
    } finally {
      setIsLoading(false);
    }
  };
  // Функция восстановления пароля 
  const resetPassword = async (email: string): Promise<void> => {
    setIsLoading(true);
    try {
      // Отправляем запрос к бэкенду
      await authAPI.resetPassword(email);
      
      console.log('Инструкции отправлены на:', email);
    } catch (error: any) {
      console.error('Ошибка восстановления пароля:', error);
      
      if (error.response?.data?.detail) {
        throw new Error(error.response.data.detail);
      }
      throw new Error('Ошибка соединения с сервером');
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
    console.log('Пользователь вышел из системы');
  };


  const value: AuthContextType = {
    user,
    login,
    register,
    resetPassword,
    logout,
    isLoading,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};