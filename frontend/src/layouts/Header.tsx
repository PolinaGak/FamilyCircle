// src/layouts/Header.tsx
import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import './MainLayout.css';

const Header: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

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
        {user ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
            <span style={{ color: '#7b68ee' }}>
              {user.name}
            </span>
            <button 
              onClick={handleLogout}
              style={{
                background: '#ff6b6b',
                color: 'white',
                padding: '8px 16px',
                borderRadius: '6px',
                border: 'none',
                cursor: 'pointer',
                fontWeight: '500',
              }}
            >
              Выйти
            </button>
          </div>
        ) : (
          <button 
            onClick={() => navigate('/login')}
            style={{
              background: '#7b68ee',
              color: 'white',
              padding: '8px 16px',
              borderRadius: '6px',
              border: 'none',
              cursor: 'pointer',
              fontWeight: '500',
            }}
          >
            Войти
          </button>
        )}
      </div>
    </div>
  );
};

export default Header;