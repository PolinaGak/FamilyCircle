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

  // При загрузке проверяем сохраненного пользователя
  useEffect(() => {
    const checkAuth = () => {
      try {
        const storedUser = localStorage.getItem('user');
        const storedToken = localStorage.getItem('token');
        
        if (storedUser && storedToken) {
          setUser(JSON.parse(storedUser));
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
      // Отправляем запрос к бэкенду
      const response = await authAPI.login(email, password);
      
      // Извлекаем данные из ответа
      const { access_token, user: apiUser } = response.data;
      
      // Сохраняем токен в localStorage
      localStorage.setItem('token', access_token);
      localStorage.setItem('user', JSON.stringify(apiUser));
      
      // Обновляем состояние
      setUser(apiUser);
      
      console.log('Успешный вход:', apiUser);
    } catch (error: any) {
      console.error('Ошибка входа:', error);
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
      // Отправляем запрос к бэкенду
      const response = await authAPI.register(name, email, password);
      
      // Извлекаем данные из ответа
      const { access_token, user: apiUser } = response.data;
      
      // Сохраняем токен и пользователя
      localStorage.setItem('token', access_token);
      localStorage.setItem('user', JSON.stringify(apiUser));
      
      // Обновляем состояние
      setUser(apiUser);
      
      console.log('Успешная регистрация:', apiUser);
    } catch (error: any) {
      console.error('Ошибка регистрации:', error);
      
      // Обрабатываем ошибку от бэкенда
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