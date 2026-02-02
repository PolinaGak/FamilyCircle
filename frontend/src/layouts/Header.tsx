// src/layouts/Header.tsx
import React from 'react';
import { Link } from 'react-router-dom';
import './MainLayout.css';

const Header: React.FC = () => {
  return (
    <div className="site-layout-background" style={{ 
      padding: '0 24px', 
      height: '64px', 
      display: 'flex', 
      alignItems: 'center',
      justifyContent: 'space-between',
      borderBottom: '2px solid #d8c8ff'
    }}>
      <div className="logo" style={{ border: 'none', background: 'transparent' }}>
        <h1 style={{ margin: 0, color: '#7b68ee', fontSize: '24px' }}>Семейный круг</h1>
      </div>
      
      <div>
        {/* Кнопка входа - показываем, если пользователь не авторизован */}
        <Link 
          to="/login" 
          style={{
            background: '#7b68ee',
            color: 'white',
            padding: '8px 16px',
            borderRadius: '6px',
            textDecoration: 'none',
            fontWeight: '500',
          }}
        >
          Войти
        </Link>
      </div>
    </div>
  );
};

export default Header;