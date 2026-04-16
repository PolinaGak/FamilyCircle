// src/layouts/Sidebar.tsx
import React from 'react';
import { Menu } from 'antd';
import { 
  HomeOutlined, 
  TeamOutlined, 
  MessageOutlined, 
  PictureOutlined, 
  CalendarOutlined, 
  SettingOutlined,
  UserAddOutlined
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import './MainLayout.css';

const Sidebar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const getSelectedKey = () => {
    const path = location.pathname;
    if (path === '/') return '1';
    if (path.includes('tree')) return '2';
    if (path.includes('chat')) return '3';
    if (path.includes('gallery')) return '4';
    if (path.includes('calendar')) return '5';
    if (path.includes('settings')) return '6';
    if (path.includes('join-family')) return '7';
    return '1';
  };

  const menuItems = [
    {
      key: '1',
      icon: <HomeOutlined />,
      label: 'Главная',
      onClick: () => navigate('/dashboard'),
    },
    {
      key: '2',
      icon: <TeamOutlined />,
      label: 'Семейное древо',
      onClick: () => navigate('/tree'),
    },
    {
      key: '3',
      icon: <MessageOutlined />,
      label: 'Чат',
      onClick: () => navigate('/chat'),
    },
    {
      key: '4',
      icon: <PictureOutlined />,
      label: 'Галерея',
      onClick: () => navigate('/gallery'),
    },
    {
      key: '5',
      icon: <CalendarOutlined />,
      label: 'Календарь',
      onClick: () => navigate('/calendar'),
    },
    {
      key: '6',
      icon: <SettingOutlined />,
      label: 'Настройки',
      onClick: () => navigate('/settings'),
    },
    {
      key: '7',
      icon: <UserAddOutlined />,
      label: 'Присоединиться к семье',
      onClick: () => navigate('/join-family'),
    },
  ];

  return (
    <Menu
      theme="light" 
      mode="inline"
      selectedKeys={[getSelectedKey()]}
      items={menuItems}
      style={{
        background: 'transparent',
        border: 'none',
      }}
    />
  );
};

export default Sidebar;