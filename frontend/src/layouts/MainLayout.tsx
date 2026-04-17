// src/layouts/MainLayout.tsx
import React from 'react';
import { Outlet } from 'react-router-dom';
import { Layout } from 'antd';
import Header from './Header';
import Sidebar from './Sidebar';
import './MainLayout.css';

const { Content, Sider } = Layout;

const MainLayout: React.FC = () => {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header />
      
      <Layout>
        <Sider 
          width={250}
          style={{
            background: 'linear-gradient(180deg, #f0e9ff, #e2d6ff)',
            borderRight: '2px solid #d8c8ff',
          }}
        >
          <Sidebar />
        </Sider>
        
        <Layout>
          <Content style={{ padding: '24px' }}>
            <div className="site-layout-background" style={{ minHeight: '100%', padding: '24px', borderRadius: '8px' }}>
              <Outlet />
            </div>
          </Content>
        </Layout>
      </Layout>
    </Layout>
  );
};

export default MainLayout;