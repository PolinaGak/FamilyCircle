// src/pages/auth/VerifyEmailPage.tsx
import React, { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { apiClient } from '../../api/client';
import './Auth.css';

const VerifyEmailPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!token) {
      setStatus('error');
      setError('Отсутствует токен подтверждения');
      return;
    }

    const verifyEmail = async () => {
      try {
        await apiClient.get(`/auth/verify-email?token=${token}`);
        setStatus('success');
        // Очищаем сохраненный email
        localStorage.removeItem('pendingEmail');
      } catch (err: any) {
        setStatus('error');
        setError(err.response?.data?.detail || 'Ошибка подтверждения email');
      }
    };

    verifyEmail();
  }, [token]);

  if (status === 'loading') {
    return (
      <div className="auth-page">
        <div className="auth-container">
          <h1 className="auth-title">Подтверждение email</h1>
          <p>Пожалуйста, подождите...</p>
        </div>
      </div>
    );
  }

  if (status === 'success') {
    return (
      <div className="auth-page">
        <div className="auth-container">
          <h1 className="auth-title">Email подтвержден! </h1>
          <div className="auth-success">
            <p>Ваш email успешно подтвержден.</p>
            <p>Теперь вы можете войти в систему.</p>
          </div>
          <div className="auth-links">
            <Link to="/login" className="auth-button" style={{ textDecoration: 'none' }}>
              Войти
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <div className="auth-container">
        <h1 className="auth-title">Ошибка подтверждения </h1>
        <div className="auth-error">
          <p>{error}</p>
        </div>
        <div className="auth-links">
          <Link to="/login" className="auth-link">
            Вернуться ко входу
          </Link>
        </div>
      </div>
    </div>
  );
};

export default VerifyEmailPage;