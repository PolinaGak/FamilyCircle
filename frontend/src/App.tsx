import React from 'react';
import { Button, Card, Layout, Menu } from 'antd';
import './App.css';

const { Header, Sider, Content } = Layout;

function App() {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider theme="dark">
        <div style={{ color: 'white', textAlign: 'center', padding: '16px' }}>
          <h3>Семейный круг</h3>
        </div>
        <Menu theme="dark" mode="inline">
          <Menu.Item key="1">Главная</Menu.Item>
          <Menu.Item key="2">Дерево</Menu.Item>
          <Menu.Item key="3">Чат</Menu.Item>
        </Menu>
      </Sider>
      <Layout>
        <Header style={{ background: '#fff', padding: '0 20px' }}>
          <h2>Веб-приложение "Семейный круг"</h2>
        </Header>
        <Content style={{ margin: '20px' }}>
          <Card title="Тест компонентов">
            <p>Ant Design работает: ✅</p>
            <p>Refine установлен: ✅</p>
            <Button type="primary" onClick={() => alert('Всё работает!')}>
              Проверить Ant Design
            </Button>
          </Card>
        </Content>
      </Layout>
    </Layout>
  );
}

export default App;