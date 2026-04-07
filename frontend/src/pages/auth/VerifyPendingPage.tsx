// src/pages/auth/VerifyPendingPage.tsx
import React from 'react';
import { Link } from 'react-router-dom';
import './Auth.css';

const VerifyPendingPage: React.FC = () => {
  const email = localStorage.getItem('pendingEmail') || 'ваш email';

  return (
    <div className="auth-page">
      <div className="auth-container">
        <h1 className="auth-title">Проверьте почту</h1>
        
        <div className="auth-success">
          <p>✉️ Мы отправили письмо на <strong>{email}</strong></p>
          <p>Перейдите по ссылке в письме, чтобы подтвердить регистрацию.</p>
          <p style={{ fontSize: '14px', marginTop: '20px' }}>
            После подтверждения вы сможете войти в систему.
          </p>
        </div>

        <div className="auth-links">
          <Link to="/login" className="auth-link">
            Вернуться ко входу
          </Link>
          <Link to="/register" className="auth-link">
            Зарегистрироваться с другим email
          </Link>
        </div>
      </div>
    </div>
  );
};

export default VerifyPendingPage;