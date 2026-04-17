import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Typography, Input, Button, message, Form } from 'antd';
import { invitationAPI } from '../api/invitation';
import { useAuth } from '../contexts/AuthContext';

const { Title, Text } = Typography;

const JoinFamilyPage: React.FC = () => {
  const [code, setCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const { loadUserFamilies } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!code.trim()) {
      message.warning('Введите код приглашения');
      return;
    }
    
    setIsLoading(true);
    try {
      const response = await invitationAPI.claimInvitation(code.trim());

      if (response.data.success) {
        message.success(`Вы присоединились к семье "${response.data.family_name}"!`);
        await loadUserFamilies();
        
        if (response.data.member_id) {
          localStorage.setItem('pendingMemberId', String(response.data.member_id));
          console.log('member_id из ответа:', response.data.member_id);
          console.log('Тип member_id:', typeof response.data.member_id);
          console.log('requires_profile_completion:', response.data.requires_profile_completion);
        }
        
        if (response.data.requires_profile_completion) {
          navigate('/edit-profile');
        } else {
          navigate('/dashboard');
        }
      }
    } catch (error: any) {
      console.error('Ошибка присоединения:', error);
      message.error(error.response?.data?.message || 'Неверный код приглашения');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '80vh' }}>
      <Card style={{ width: 450, textAlign: 'center' }}>
        <Title level={2}>Присоединиться к семье</Title>
        <Text type="secondary">
          Введите код приглашения, который вам отправил администратор семьи
        </Text>
        
        <form onSubmit={handleSubmit} style={{ marginTop: '24px' }}>
          <Form.Item>
            <Input
              size="large"
              placeholder="Введите код приглашения"
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              style={{ textAlign: 'center', fontFamily: 'monospace', fontSize: '16px' }}
              disabled={isLoading}
            />
          </Form.Item>
          
          <Button 
            type="primary" 
            htmlType="submit" 
            loading={isLoading}
            style={{ width: '100%', background: '#7b68ee' }}
          >
            Присоединиться
          </Button>
        </form>
      </Card>
    </div>
  );
};

export default JoinFamilyPage;