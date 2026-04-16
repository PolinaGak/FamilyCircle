// frontend/src/pages/SettingsPage.tsx
import React, { useState, useEffect } from 'react';
import { Card, Tabs, Form, Input, Button, message, Spin, Typography, Alert, Space } from 'antd';
import { ArrowLeftOutlined,UserOutlined, LockOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext';
import { authAPI } from '../api/auth';

const { Title, Text } = Typography;

const SettingsPage: React.FC = () => {
  const { user } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [isPasswordLoading, setIsPasswordLoading] = useState(false);
  const [profileForm] = Form.useForm();
  const [passwordForm] = Form.useForm();
  
  // Состояния для показа/скрытия паролей
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Загружаем актуальные данные при открытии
  useEffect(() => {
    const loadProfile = async () => {
      try {
        const response = await authAPI.getMe();
        profileForm.setFieldsValue({ name: response.data.name });
      } catch (error) {
        console.error('Ошибка загрузки профиля:', error);
      }
    };
    loadProfile();
  }, [profileForm]);

  // Обновление имени
  const handleUpdateProfile = async (values: { name: string }) => {
    setIsLoading(true);
    try {
      const response = await authAPI.updateProfile({ name: values.name });
      // Обновляем данные в localStorage
      const storedUser = localStorage.getItem('user');
      if (storedUser) {
        const userData = JSON.parse(storedUser);
        userData.name = values.name;
        localStorage.setItem('user', JSON.stringify(userData));
      }
      message.success('Имя успешно обновлено');
      profileForm.setFieldsValue({ name: values.name });
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Ошибка обновления имени');
    } finally {
      setIsLoading(false);
    }
  };

  // Смена пароля
  const handleChangePassword = async (values: { 
    current_password: string; 
    new_password: string; 
    confirm_password: string 
  }) => {
    if (values.new_password !== values.confirm_password) {
      message.error('Новые пароли не совпадают');
      return;
    }
    
    if (values.new_password.length < 8) {
      message.error('Пароль должен быть не менее 8 символов');
      return;
    }
    
    setIsPasswordLoading(true);
    try {
      await authAPI.changePassword({
        current_password: values.current_password,
        new_password: values.new_password,
      });
      message.success('Пароль успешно изменен');
      passwordForm.resetFields();
      setShowCurrentPassword(false);
      setShowNewPassword(false);
      setShowConfirmPassword(false);
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Ошибка смены пароля');
    } finally {
      setIsPasswordLoading(false);
    }
  };

  const PasswordInput = ({ 
    value, 
    onChange, 
    placeholder, 
    disabled, 
    showPassword, 
    setShowPassword 
  }: { 
    value: string;
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
    placeholder: string;
    disabled: boolean;
    showPassword: boolean;
    setShowPassword: (value: boolean) => void;
  }) => (
    <div className="password-input-wrapper" style={{ position: 'relative', display: 'flex' }}>
      <input
        type={showPassword ? "text" : "password"}
        className="form-input"
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        disabled={disabled}
        style={{ flex: 1, paddingRight: '45px' }}
      />
      <button
        type="button"
        className="password-toggle"
        onClick={() => setShowPassword(!showPassword)}
        disabled={disabled}
        aria-label={showPassword ? "Скрыть пароль" : "Показать пароль"}
        style={{
          position: 'absolute',
          right: '12px',
          top: '50%',
          transform: 'translateY(-50%)',
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          fontSize: '18px',
          padding: '8px',
          color: '#7b68ee',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: '40px',
          height: '40px',
          borderRadius: '4px',
          transition: 'background-color 0.2s'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = 'rgba(123, 104, 238, 0.1)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = 'transparent';
        }}
      >
        {showPassword ? '👁️' : '👁️‍🗨️'}
      </button>
    </div>
  );

  const profileItems = [
    {
      key: 'profile',
      label: (
        <span style={{ fontSize: '16px' }}>
          <UserOutlined /> Профиль
        </span>
      ),
      children: (
        <div style={{ padding: '24px' }}>
          
          
          <Form
            form={profileForm}
            layout="vertical"
            onFinish={handleUpdateProfile}
            initialValues={{ name: user?.name }}
            style={{ maxWidth: 500 }}
          >
            <Form.Item
              label="Email"
              name="email"
              initialValue={user?.email}
              tooltip="Email нельзя изменить. Он используется для входа в систему."
            >
              <Input 
                disabled 
                size="large"
                style={{ background: '#f5f5f5', cursor: 'not-allowed' }}
              />
            </Form.Item>
            
            <Form.Item
              label="Имя"
              name="name"
              rules={[
                { required: true, message: 'Введите имя' },
                { min: 2, message: 'Имя должно содержать не менее 2 символов' },
                { max: 50, message: 'Имя должно содержать не более 50 символов' }
              ]}
              tooltip="Имя будет отображаться в шапке приложения и в семье."
            >
              <Input 
                size="large" 
                placeholder="Ваше имя"
                style={{ fontSize: '16px' }}
              />
            </Form.Item>
            
            <Form.Item>
              <Button 
                type="primary" 
                htmlType="submit" 
                loading={isLoading}
                size="large"
                style={{ background: '#7b68ee', minWidth: '150px' }}
              >
                Сохранить изменения
              </Button>
            </Form.Item>
          </Form>
        </div>
      ),
    },
    {
      key: 'security',
      label: (
        <span style={{ fontSize: '16px' }}>
          <LockOutlined /> Безопасность
        </span>
      ),
      children: (
        <div style={{ padding: '24px' }}>
          
          
          <Form
            form={passwordForm}
            layout="vertical"
            onFinish={handleChangePassword}
            style={{ maxWidth: 500 }}
          >
            <Form.Item
              label="Текущий пароль"
              name="current_password"
              rules={[{ required: true, message: 'Введите текущий пароль' }]}
            >
              <PasswordInput
                value={passwordForm.getFieldValue('current_password') || ''}
                onChange={(e) => passwordForm.setFieldsValue({ current_password: e.target.value })}
                placeholder="Введите текущий пароль"
                disabled={isPasswordLoading}
                showPassword={showCurrentPassword}
                setShowPassword={setShowCurrentPassword}
              />
            </Form.Item>
            
            <Form.Item
              label="Новый пароль"
              name="new_password"
              rules={[
                { required: true, message: 'Введите новый пароль' },
                { min: 8, message: 'Пароль должен быть не менее 8 символов' },
                {
                  pattern: /^(?=.*[A-Za-z])(?=.*\d)/,
                  message: 'Пароль должен содержать хотя бы одну букву и одну цифру'
                }
              ]}
              extra="Пароль должен содержать минимум 8 символов, включая буквы, спецсимволы и цифры."
            >
              <PasswordInput
                value={passwordForm.getFieldValue('new_password') || ''}
                onChange={(e) => passwordForm.setFieldsValue({ new_password: e.target.value })}
                placeholder="Введите новый пароль"
                disabled={isPasswordLoading}
                showPassword={showNewPassword}
                setShowPassword={setShowNewPassword}
              />
            </Form.Item>
            
            <Form.Item
              label="Подтвердите новый пароль"
              name="confirm_password"
              dependencies={['new_password']}
              rules={[
                { required: true, message: 'Подтвердите новый пароль' },
                ({ getFieldValue }) => ({
                  validator(_, value) {
                    if (!value || getFieldValue('new_password') === value) {
                      return Promise.resolve();
                    }
                    return Promise.reject(new Error('Пароли не совпадают'));
                  },
                }),
              ]}
            >
              <PasswordInput
                value={passwordForm.getFieldValue('confirm_password') || ''}
                onChange={(e) => passwordForm.setFieldsValue({ confirm_password: e.target.value })}
                placeholder="Подтвердите новый пароль"
                disabled={isPasswordLoading}
                showPassword={showConfirmPassword}
                setShowPassword={setShowConfirmPassword}
              />
            </Form.Item>
            
            <Form.Item>
              <Button 
                type="primary" 
                htmlType="submit" 
                loading={isPasswordLoading}
                size="large"
                style={{ background: '#7b68ee', minWidth: '150px' }}
              >
                Сменить пароль
              </Button>
            </Form.Item>
          </Form>
        
        </div>
      ),
    },
  ];

  return (
    
    <div style={{ 
        padding: '24px', 
        maxWidth: 800, 
        margin: '0 auto', 
        
        }}>
        
      <Title level={2} style={{ marginBottom: '8px', color: '#2d3436' }}>
        Настройки
      </Title>
      <Text type="secondary" style={{ display: 'block', marginBottom: '24px', fontSize: '16px' }}>
        Управление вашим профилем и настройками безопасности
      </Text>
      
      <Card 
        style={{ 
          borderRadius: '12px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
          border: 'none'
        }}
      >
        <Tabs 
          defaultActiveKey="profile" 
          items={profileItems}
          size="large"
          tabBarStyle={{ marginBottom: '0', paddingLeft: '24px', paddingTop: '16px' }}
        />
      </Card>
    </div>
    
  );
};

export default SettingsPage;