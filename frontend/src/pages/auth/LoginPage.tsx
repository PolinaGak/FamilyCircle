import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import './Auth.css'; 

const LoginPage: React.FC = () => {

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log('Email:', email);
    console.log('Password:', password);
  };

  return (
    <div className="auth-page">
      <div className="auth-container">
        <h1 className="auth-title">Вход в Семейный круг</h1>
        
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

          <div className="form-group">
            <label htmlFor="password" className="form-label">
              Пароль
            </label>
            <input
              type="password"
              id="password"
              className="form-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Введите пароль"
              required
            />
          </div>

          <button type="submit" className="auth-button">
            Войти
          </button>
        </form>

        <div className="auth-links">
          <Link to="/register" className="auth-link">
            Нет аккаунта? Зарегистрироваться
          </Link>
          <Link to="/forgot-password" className="auth-link">
            Забыли пароль?
          </Link>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;