import React, { useState } from 'react';
import { Link } from 'react-router-dom'; 
import './Auth.css';
import { useAuth } from '../../contexts/AuthContext';

const ForgotPasswordPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const { resetPassword } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    setIsSuccess(false);

    try {
      await resetPassword(email);
      setIsSuccess(true);
    
      
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
              <p>Инструкции по восстановлению пароля отправлены на <strong>{email}</strong></p>
              <p style={{ fontSize: '14px', marginTop: '10px' }}>
                Перейдите по ссылке в письме, чтобы создать новый пароль.
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