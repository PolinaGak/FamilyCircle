// src/pages/auth/ForgotPasswordPage.tsx
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import './Auth.css';

const ForgotPasswordPage: React.FC = () => {
  const [email, setEmail] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log('Восстановление пароля для:', email);
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
            />
          </div>

          <button type="submit" className="auth-button">
            Отправить инструкции
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

export default ForgotPasswordPage;  // Важно: export default