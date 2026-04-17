import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Form, Input, Button, message, DatePicker, Select, Spin } from 'antd';
import { UserOutlined, PhoneOutlined, HomeOutlined, BankOutlined } from '@ant-design/icons';
import { familyAPI } from '../api/family';
import dayjs from 'dayjs';

const EditProfilePage: React.FC = () => {
  const [form] = Form.useForm();
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const memberId = localStorage.getItem('pendingMemberId');

  useEffect(() => {

    if (!memberId) {
      message.warning('Информация о профиле не найдена');
      navigate('/dashboard');
    }
  }, [memberId, navigate]);

  const handleSubmit = async (values: any) => {
    if (!memberId) return;
    
    setIsLoading(true);
    try {
      const updateData: any = {};
      
      if (values.first_name) updateData.first_name = values.first_name;
      if (values.last_name) updateData.last_name = values.last_name;
      if (values.patronymic) updateData.patronymic = values.patronymic;
      if (values.gender) updateData.gender = values.gender;
      if (values.birth_date) updateData.birth_date = values.birth_date.toISOString();
      if (values.phone) updateData.phone = values.phone;
      if (values.workplace) updateData.workplace = values.workplace;
      if (values.residence) updateData.residence = values.residence;
      
      await familyAPI.updateMember(Number(memberId), updateData);
      
      message.success('Профиль успешно заполнен!');
      localStorage.removeItem('pendingMemberId');
      navigate('/dashboard');
    } catch (error: any) {
      console.error('Ошибка:', error);
      message.error(error.response?.data?.detail || 'Ошибка сохранения профиля');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 600, margin: '0 auto', padding: '40px 20px' }}>
      <Card title="Заполните информацию о себе" style={{ borderRadius: '12px' }}>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{ gender: 'male' }}
        >
          <Form.Item
            name="last_name"
            label="Фамилия"
            rules={[{ required: true, message: 'Введите фамилию' }]}
          >
            <Input placeholder="Иванов" size="large" />
          </Form.Item>

          <Form.Item
            name="first_name"
            label="Имя"
            rules={[{ required: true, message: 'Введите имя' }]}
          >
            <Input placeholder="Иван" size="large" />
          </Form.Item>

          <Form.Item name="patronymic" label="Отчество">
            <Input placeholder="Иванович" size="large" />
          </Form.Item>

          <Form.Item
            name="birth_date"
            label="Дата рождения"
            rules={[{ required: true, message: 'Выберите дату рождения' }]}
          >
            <DatePicker style={{ width: '100%' }} size="large" placeholder="Выберите дату" />
          </Form.Item>

          <Form.Item
            name="gender"
            label="Пол"
            rules={[{ required: true, message: 'Выберите пол' }]}
          >
            <Select size="large">
              <Select.Option value="male">Мужской</Select.Option>
              <Select.Option value="female">Женский</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item name="phone" label="Телефон">
            <Input prefix={<PhoneOutlined />} placeholder="+7 (999) 123-45-67" size="large" />
          </Form.Item>

          <Form.Item name="workplace" label="Место работы">
            <Input prefix={<BankOutlined />} placeholder="ООО Ромашка" size="large" />
          </Form.Item>

          <Form.Item name="residence" label="Место жительства">
            <Input prefix={<HomeOutlined />} placeholder="г. Москва" size="large" />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={isLoading} size="large" block>
              Сохранить
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default EditProfilePage;