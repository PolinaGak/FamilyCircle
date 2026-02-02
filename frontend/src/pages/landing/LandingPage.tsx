// src/pages/landing/LandingPage.tsx
import React from 'react';
import { Link } from 'react-router-dom';
import './LandingPage.css';

const LandingPage: React.FC = () => {
  return (
    <div className="landing-page">
      <header className="landing-header">
        <h1>Добро пожаловать в "Семейный круг"!</h1>
        <p>Цифровая платформа для объединения вашей семьи</p>
        <div className="landing-buttons">
          <Link to="/login" className="landing-btn landing-btn-primary">
            Войти
          </Link>
          <Link to="/register" className="landing-btn landing-btn-secondary">
            Зарегистрироваться
          </Link>
        </div>
      </header>

      <section className="features">
        <div className="feature-card">
          <h3> Семейное древо</h3>
          <p>Создайте и визуализируйте ваше семейное древо</p>
        </div>
        <div className="feature-card">
          <h3>Семейный чат</h3>
          <p>Общайтесь в удобном семейном чате</p>
        </div>
        <div className="feature-card">
          <h3>Галерея</h3>
          <p>Делитесь фотографиями и воспоминаниями</p>
        </div>
        <div className="feature-card">
          <h3>Календарь</h3>
          <p>Планируйте совместные события</p>
        </div>
      </section>
    </div>
  );
};

export default LandingPage;
export {}