// src/contexts/AuthContext.tsx
import React, { createContext, useState, useContext, useEffect, ReactNode } from 'react';

// Тип для пользователя
export interface User {
  id: string;
  email: string;
  name: string;
}

// Тип для контекста
interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
}

// Создаем контекст с начальным значением undefined
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Хук для использования контекста
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Провайдер контекста
interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // При загрузке приложения проверяем, есть ли сохраненный пользователь
  useEffect(() => {
    const checkAuth = () => {
      try {
        const storedUser = localStorage.getItem('user');
        if (storedUser) {
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

  // Функция входа (пока заглушка)
  const login = async (email: string, password: string): Promise<void> => {
    setIsLoading(true);
    try {
      // TODO: Заменить на реальный запрос к API
      console.log('Попытка входа с:', email, password);
      
      // Моковый пользователь для тестирования
      const mockUser: User = {
        id: '1',
        email: email,
        name: email.split('@')[0], // Имя из email
      };

      // Сохраняем в localStorage
      localStorage.setItem('user', JSON.stringify(mockUser));
      setUser(mockUser);
      
      console.log('Успешный вход:', mockUser);
    } catch (error) {
      console.error('Ошибка входа:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  // Функция выхода
  const logout = () => {
    localStorage.removeItem('user');
    setUser(null);
    console.log('Пользователь вышел из системы');
  };

  // Значение контекста
  const value = {
    user,
    login,
    logout,
    isLoading,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export {}