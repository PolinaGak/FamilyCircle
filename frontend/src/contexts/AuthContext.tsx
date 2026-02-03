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
  register: (name: string, email: string, password: string) => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
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

  // Функция регистрации (ДОБАВЛЕНО)
  const register = async (name: string, email: string, password: string): Promise<void> => {
    setIsLoading(true);
    try {
      // TODO: Заменить на реальный запрос к API
      console.log('Попытка регистрации:', { name, email });
      
      // Базовая валидация на клиенте
      if (!name || !email || !password) {
        throw new Error('Все поля обязательны');
      }
      if (!/\d/.test(password)) {
        throw new Error('Пароль должен содержать хотя бы одну цифру (0-9)');
      }

      if (!/[A-Z]/.test(password)) {
        throw new Error('Пароль должен содержать хотя бы одну заглавную букву (A-Z)');
      }
      if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) {
        throw new Error('Пароль должен содержать хотя бы один специальный символ (!@#$%^&* и т.д.)');
      }
      
      if (password.length < 8) {
        throw new Error('Пароль должен быть не менее 8 символов');
      }

      // Проверка email (простая)
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(email)) {
        throw new Error('Введите корректный email');
      }

      // Моковый пользователь (будет создан на сервере)
      const mockUser: User = {
        id: Date.now().toString(), // Генерируем уникальный ID
        email: email,
        name: name,
      };

      // Сохраняем в localStorage (имитируем успешную регистрацию и вход)
      localStorage.setItem('user', JSON.stringify(mockUser));
      setUser(mockUser);
      
      console.log('Успешная регистрация и вход:', mockUser);
    } catch (error) {
      console.error('Ошибка регистрации:', error);
      throw error; // Пробрасываем ошибку дальше, чтобы обработать в компоненте
    } finally {
      setIsLoading(false);
    }
  };
    // Функция восстановления пароля (ДОБАВЛЯЕМ)
    const resetPassword = async (email: string): Promise<void> => {
    setIsLoading(true);
    try {
        // TODO: Заменить на реальный запрос к API
        console.log('Запрос на восстановление пароля для:', email);
        
        // Валидация email
        if (!email) {
        throw new Error('Введите email');
        }
        
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email)) {
        throw new Error('Введите корректный email');
        }

        // Имитация успешной отправки
        // В реальности здесь будет запрос к бэкенду
        console.log('Инструкции по восстановлению пароля отправлены на:', email);
        
        // Можно добавить задержку для имитации запроса
        await new Promise(resolve => setTimeout(resolve, 1000));
        
    } catch (error) {
        console.error('Ошибка восстановления пароля:', error);
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

  // Значение контекста (обновлено - добавлен register)
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

export {}