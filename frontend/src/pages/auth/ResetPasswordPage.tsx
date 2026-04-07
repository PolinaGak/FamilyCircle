// src/pages/auth/ResetPasswordPage.tsx
import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { apiClient } from '../../api/client';
import './Auth.css';

const ResetPasswordPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  
  const navigate = useNavigate();

  // Функция валидации пароля (та же, что и в RegisterPage)
  const validatePassword = (pass: string): string | null => {
    // 1. Минимум 8 символов
    if (pass.length < 8) {
      return 'Пароль должен быть не менее 8 символов';
    }
    
    // 2. Хотя бы одна цифра
    if (!/\d/.test(pass)) {
      return 'Пароль должен содержать хотя бы одну цифру (0-9)';
    }
    
    // 3. Хотя бы одна заглавная буква
    if (!/[A-Z]/.test(pass)) {
      return 'Пароль должен содержать хотя бы одну заглавную букву (A-Z)';
    }
    
    // 4. Хотя бы один спецсимвол
    if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(pass)) {
      return 'Пароль должен содержать хотя бы один специальный символ (!@#$%^&* и т.д.)';
    }
    
    return null;
  };

  // Проверяем наличие токена в URL
  useEffect(() => {
    if (!token) {
      setError('Отсутствует токен сброса пароля');
    }
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    
    // 1. Проверка совпадения паролей
    if (password !== confirmPassword) {
        setError('Пароли не совпадают');
        return;
    }
    
    // 2. Валидация сложности пароля
    const passwordError = validatePassword(password);
    if (passwordError) {
        setError(passwordError);
        return;
    }
    
    setIsLoading(true);
    
    try {
        await apiClient.post('/auth/password-reset', {
        token: token,
        new_password: password,
        });
        
        setIsSuccess(true);
        
        // Через 3 секунды перенаправляем на страницу входа
        setTimeout(() => {
        navigate('/login');
        }, 3000);
        
    } catch (err: any) {
        setError(err.response?.data?.detail || 'Ошибка сброса пароля');
    } finally {
        setIsLoading(false);
    }
  };

  if (!token && !isSuccess) {
    return (
      <div className="auth-page">
        <div className="auth-container">
          <h1 className="auth-title">Ошибка</h1>
          <div className="auth-error">
            <p>Недействительная ссылка для сброса пароля</p>
          </div>
          <div className="auth-links">
            <Link to="/forgot-password" className="auth-link">
              Запросить сброс пароля заново
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (isSuccess) {
    return (
      <div className="auth-page">
        <div className="auth-container">
          <h1 className="auth-title">Пароль изменен! </h1>
          <div className="auth-success">
            <p>Ваш пароль успешно изменен.</p>
            <p>Вы будете перенаправлены на страницу входа через 3 секунды...</p>
          </div>
          <div className="auth-links">
            <Link to="/login" className="auth-link">
              Перейти ко входу
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <div className="auth-container">
        <h1 className="auth-title">Создание нового пароля</h1>
        
        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label htmlFor="password" className="form-label">
              Новый пароль
            </label>
            <div className="password-input-wrapper">
              <input
                type={showPassword ? "text" : "password"}
                id="password"
                className="form-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Введите новый пароль"
                required
                disabled={isLoading}
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword(!showPassword)}
                disabled={isLoading}
                aria-label={showPassword ? "Скрыть пароль" : "Показать пароль"}
              >
                {showPassword ? '👁️' : '👁️‍🗨️'}
              </button>
            </div>
            
            {/* Подсказки для пароля */}
            <div className="password-hints">
              <div className={`hint ${password.length >= 8 ? 'hint-valid' : 'hint-invalid'}`}>
                {password.length >= 8 ? '✓' : '○'} Не менее 8 символов
              </div>
              <div className={`hint ${/\d/.test(password) ? 'hint-valid' : 'hint-invalid'}`}>
                {/\d/.test(password) ? '✓' : '○'} Хотя бы одна цифра
              </div>
              <div className={`hint ${/[A-Z]/.test(password) ? 'hint-valid' : 'hint-invalid'}`}>
                {/[A-Z]/.test(password) ? '✓' : '○'} Хотя бы одна заглавная буква
              </div>
              <div className={`hint ${/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password) ? 'hint-valid' : 'hint-invalid'}`}>
                {/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password) ? '✓' : '○'} Хотя бы один спецсимвол
              </div>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="confirmPassword" className="form-label">
              Подтвердите пароль
            </label>
            <div className="password-input-wrapper">
              <input
                type={showConfirmPassword ? "text" : "password"}
                id="confirmPassword"
                className="form-input"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Повторите пароль"
                required
                disabled={isLoading}
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                disabled={isLoading}
                aria-label={showConfirmPassword ? "Скрыть пароль" : "Показать пароль"}
              >
                {showConfirmPassword ? '👁️' : '👁️‍🗨️'}
              </button>
            </div>
          </div>

          {error && (
            <div className="auth-error">
              {error}
            </div>
          )}

          <button 
            type="submit" 
            className="auth-button"
            disabled={isLoading}
          >
            {isLoading ? 'Сохранение...' : 'Сохранить новый пароль'}
          </button>
        </form>

        <div className="auth-links">
          <Link to="/login" className="auth-link">
            Вернуться ко входу
          </Link>
        </div>
      </div>
    </div>
  );
};

export default ResetPasswordPage;