import React from 'react';
import { Card, Typography, Row, Col } from 'antd';
import { Link } from 'react-router-dom';

const { Title, Paragraph } = Typography;
const features = [
  {
    id: 1,
    title: 'Семейное древо',
    emoji: '🌳',
    description: 'Создайте и визуализируйте ваше семейное древо',
    color: '#7b68ee',
    path: '/tree'
  },
  {
    id: 2,
    title: 'Семейный чат',
    emoji: '💬',
    description: 'Общайтесь в удобном семейном чате',
    color: '#ff6b6b',
    path: '/chat'
  },
  {
    id: 3,
    title: 'Галерея',
    emoji: '🖼️',
    description: 'Делитесь фотографиями и воспоминаниями',
    color: '#4ecdc4',
    path: '/gallery'
  },
  {
    id: 4,
    title: 'Календарь',
    emoji: '📅',
    description: 'Планируйте совместные события',
    color: '#45b7d1',
    path: '/calendar'
  }
];

const HomePage: React.FC = () => {
  return (
    <Card 
      style={{ 
        borderRadius: '12px',
        boxShadow: '0 4px 12px rgba(123, 104, 238, 0.15)',
        border: 'none',
        backgroundColor: 'white'
      }}
    >
      {}
      <Title 
        level={2} 
        style={{ 
          background: 'linear-gradient(45deg, #7b68ee, #ff6b6b)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          textAlign: 'center',
          marginBottom: '40px',
          fontWeight: 700,
          fontSize: '32px'
        }}
      >
        Добро пожаловать в "Семейный круг"!
      </Title>
      
      {}
      <Paragraph style={{ 
        fontSize: '18px', 
        lineHeight: '1.6',
        textAlign: 'center',
        marginBottom: '40px',
        color: '#2d3436'
      }}>
        Цифровая платформа для объединения вашей семьи. 
        Сохраняйте воспоминания, общайтесь и планируйте вместе!
      </Paragraph>
      
      {}
      <Row gutter={[24, 24]} style={{ marginBottom: '40px' }}>
        {features.map((feature) => (
          <Col xs={24} sm={12} md={12} lg={6} key={feature.id}>
            <Link to={feature.path} style={{ textDecoration: 'none' }}>
              <div 
                style={{
                  padding: '25px 20px',
                  background: `linear-gradient(135deg, ${feature.color}20, ${feature.color}10)`,
                  borderRadius: '12px',
                  textAlign: 'center',
                  height: '100%',
                  transition: 'all 0.3s ease',
                  border: `2px solid ${feature.color}30`,
                  cursor: 'pointer'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'translateY(-5px)';
                  e.currentTarget.style.boxShadow = `0 10px 20px ${feature.color}30`;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              >
                <div style={{ 
                  fontSize: '48px', 
                  marginBottom: '15px',
                  filter: 'drop-shadow(2px 2px 4px rgba(0,0,0,0.1))'
                }}>
                  {feature.emoji}
                </div>
                <h3 style={{ 
                  color: feature.color,
                  marginBottom: '10px',
                  fontSize: '20px',
                  fontWeight: 600
                }}>
                  {feature.title}
                </h3>
                <p style={{ 
                  color: '#636e72',
                  fontSize: '14px',
                  lineHeight: '1.4',
                  margin: 0
                }}>
                  {feature.description}
                </p>
              </div>
            </Link>
          </Col>
        ))}
      </Row>
      
      {}
      <div style={{
        padding: '20px',
        background: 'linear-gradient(135deg, #f8f9fa, #e9ecef)',
        borderRadius: '8px',
        textAlign: 'center',
      }}>
        <Paragraph style={{ 
          fontSize: '16px', 
          margin: 0,
          fontWeight: 500 
        }}>
        Выберите раздел выше или используйте меню слева.
        </Paragraph>
      </div>
    </Card>
  );
};

export default HomePage;