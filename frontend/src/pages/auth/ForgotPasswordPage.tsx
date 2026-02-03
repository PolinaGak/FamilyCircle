// src/pages/auth/ForgotPasswordPage.tsx
import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import './Auth.css';
import { useAuth } from '../../contexts/AuthContext';

const ForgotPasswordPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const { resetPassword } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    setIsSuccess(false);

    try {
      await resetPassword(email);
      setIsSuccess(true);
      
      // Автоматический редирект через 10 секунд
      setTimeout(() => {
        navigate('/login');
      }, 10000);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка восстановления пароля');
      console.error('Ошибка:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-container">
        <h1 className="auth-title">Восстановление пароля</h1>
        <p className="auth-subtitle">
          Введите email, указанный при регистрации
        </p>
        
        <form onSubmit={handleSubmit} className="auth-form">
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
              disabled={isLoading || isSuccess}
            />
          </div>

          {isSuccess && (
            <div className="auth-success">
              <p>Инструкции по восстановлению пароля отправлены на {email}</p>
              <p style={{ fontSize: '14px', opacity: 0.8 }}>
                Вы будете перенаправлены на страницу входа через 10 секунд...
              </p>
            </div>
          )}

          {error && (
            <div className="auth-error">
              {error}
            </div>
          )}

          <button 
            type="submit" 
            className="auth-button"
            disabled={isLoading || isSuccess}
          >
            {isLoading ? 'Отправка...' : 'Отправить инструкции'}
          </button>
        </form>

        <div className="auth-links">
          <Link to="/login" className="auth-link">
            Вернуться ко входу
          </Link>
          <Link to="/" className="auth-link">
            На главную
          </Link>
        </div>
      </div>
    </div>
  );
};

export default ForgotPasswordPage;