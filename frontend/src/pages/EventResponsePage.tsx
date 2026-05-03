import React, { useEffect, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { Card, Typography, Spin, Button, Result } from 'antd';
import { eventAPI } from '../api/event';
import { CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

const EventResponsePage: React.FC = () => {
  const { event_id } = useParams<{ event_id: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');

  useEffect(() => {
    const action = searchParams.get('action');
    const eventId = event_id;

    if (!eventId || !action || (action !== 'accept' && action !== 'decline')) {
      setStatus('error');
      setMessage('Неверная ссылка для ответа на приглашение');
      return;
    }

    const respondToInvitation = async () => {
      try {
        await eventAPI.respondToInvitation(Number(eventId), action === 'accept');
        setStatus('success');
        setMessage(action === 'accept' 
          ? 'Вы успешно приняли приглашение на событие' 
          : 'Вы отклонили приглашение на событие');
      } catch (error: any) {
        setStatus('error');
        setMessage(error.response?.data?.detail || 'Ошибка при ответе на приглашение');
      }
    };

    respondToInvitation();
  }, [event_id, searchParams]);

  if (status === 'loading') {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" tip="Обработка вашего ответа..." />
      </div>
    );
  }

  if (status === 'success') {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Card style={{ textAlign: 'center', maxWidth: 500 }}>
          <Result
            icon={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
            title="Ответ принят"
            subTitle={message}
            extra={[
              <Button type="primary" key="calendar" onClick={() => navigate('/calendar')}>
                Перейти в календарь
              </Button>,
              <Button key="home" onClick={() => navigate('/')}>
                На главную
              </Button>,
            ]}
          />
        </Card>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
      <Card style={{ textAlign: 'center', maxWidth: 500 }}>
        <Result
          icon={<CloseCircleOutlined style={{ color: '#ff4d4f' }} />}
          title="Ошибка"
          subTitle={message}
          extra={[
            <Button type="primary" key="login" style={{ background: '#7b68ee' }}
            onClick={() => navigate('/login')}>
              Войти
            </Button>,
            <Button key="home" onClick={() => navigate('/')}>
              На главную
            </Button>,
          ]}
        />
      </Card>
    </div>
  );
};

export default EventResponsePage;