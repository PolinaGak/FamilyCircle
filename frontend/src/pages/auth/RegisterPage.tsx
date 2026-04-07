// src/pages/auth/RegisterPage.tsx
import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import './Auth.css';
import { useAuth } from '../../contexts/AuthContext';

const RegisterPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    // 1. Пароли совпадают?
    if (password !== confirmPassword) {
      setError('Пароли не совпадают');
      setIsLoading(false);
      return;
    }

    // 2. Пароль достаточно сложный?
    const passwordValidationError = validatePassword(password);
    if (passwordValidationError) {
      setError(passwordValidationError);
      setIsLoading(false);
      return;
    }

    // 3. Все проверки пройдены - регистрируем
    try {
      await register(name, email, password);
      localStorage.setItem('pendingEmail', email);
      navigate('/verify-pending');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка регистрации');
      console.error('Ошибка регистрации:', err);
    } finally {
      setIsLoading(false);
    }
  };

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

  return (
    <div className="auth-page">
      <div className="auth-container">
        <h1 className="auth-title">Регистрация</h1>
        
        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label htmlFor="name" className="form-label">
              Имя
            </label>
            <input
              type="text"
              id="name"
              className="form-input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Ваше имя"
              required
              disabled={isLoading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="email" className="form-label">
              Email
            </label>
            <input
              type="email"
              id="email"
              className="form-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="ваш@email.com"
              required
              disabled={isLoading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="password" className="form-label">
                Пароль
            </label>
            <div className="password-input-wrapper">
                <input
                type={showPassword ? "text" : "password"}  // Меняем тип в зависимости от состояния
                id="password"
                className="form-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Придумайте пароль"
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
            
            {/* Подсказки для пароля (оставляем как есть) */}
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
                type={showConfirmPassword ? "text" : "password"}  // Меняем тип в зависимости от состояния
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
            {isLoading ? 'Регистрация...' : 'Зарегистрироваться'}
          </button>
        </form>

        <div className="auth-links">
          <Link to="/login" className="auth-link">
            Уже есть аккаунт? Войти
          </Link>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;