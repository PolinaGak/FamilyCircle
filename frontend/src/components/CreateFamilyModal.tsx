import React, { useState } from 'react';
import { Modal, Form, Input, Button, message, DatePicker, Select, Divider } from 'antd';
import { familyAPI } from '../api/family';
import { useAuth } from '../contexts/AuthContext';
import dayjs from 'dayjs';

interface CreateFamilyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const CreateFamilyModal: React.FC<CreateFamilyModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [form] = Form.useForm();
  const [isLoading, setIsLoading] = useState(false);
  const { user, loadUserFamilies } = useAuth();

  const handleSubmit = async (values: any) => {
    setIsLoading(true);
    try {
      const familyResponse = await familyAPI.create(values.familyName);
      const newFamilyId = familyResponse.data.id;
      
      const membersResponse = await familyAPI.getFamilyMembers(newFamilyId);
      const currentMember = membersResponse.data.find(m => m.user_id === Number(user?.id));
      
      if (currentMember) {
        await familyAPI.updateMember(currentMember.id, {
          first_name: values.first_name,
          last_name: values.last_name,
          patronymic: values.patronymic || '',
          gender: values.gender,
          birth_date: values.birth_date.toISOString(),
          phone: values.phone || '',
          workplace: values.workplace || '',
          residence: values.residence || '',
          is_active: true,
        });
      }
      
      if (!values.birth_date || !dayjs(values.birth_date).isValid()) {
        message.error('Пожалуйста, выберите корректную дату рождения');
        return;
      }

      message.success(`Семья "${values.familyName}" успешно создана!`);
      await loadUserFamilies(); 
      form.resetFields();
      onSuccess();
      onClose();
    } catch (error: any) {
      console.error('Ошибка создания семьи:', error);
      const errorDetail = error.response?.data?.detail;
      if (errorDetail?.includes('лимит')) {
        message.error('Вы не можете создать более 3 семей. Достигнут лимит.');
      } else {
        message.error(errorDetail || 'Не удалось создать семью');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Modal
      title="Создать новую семью"
      open={isOpen}
      onCancel={() => {
        form.resetFields();
        onClose();
      }}
      footer={null}
      destroyOnClose
      width={500}
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
      >
        <Form.Item
          name="familyName"
          label="Название семьи"
          rules={[{ required: true, message: 'Введите название семьи' }]}
        >
          <Input placeholder="Например: Ивановы" size="large" />
        </Form.Item>

        <Divider orientation="left">Ваши данные</Divider>

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

        <Form.Item
          name="patronymic"
          label="Отчество"
        >
          <Input placeholder="Иванович" size="large" />
        </Form.Item>

        <Form.Item
          name="birth_date"
          label="Дата рождения"
          rules={[
            { required: true, message: 'Выберите дату рождения' },
            { type: 'object', message: 'Пожалуйста, выберите корректную дату' }
          ]}
        >
          <DatePicker 
            style={{ width: '100%' }} 
            size="large" 
            placeholder="Выберите дату"
            format="DD.MM.YYYY"
            disabledDate={(current) => {
              return current && current > dayjs().endOf('day');
            }}
          />
        </Form.Item>

        <Form.Item
          name="gender"
          label="Пол"
          rules={[{ required: true, message: 'Выберите пол' }]}
        >
          <Select size="large" placeholder="Выберите пол">
            <Select.Option value="male">Мужской</Select.Option>
            <Select.Option value="female">Женский</Select.Option>
          </Select>
        </Form.Item>

        <Form.Item
          name="phone"
          label="Телефон"
        >
          <Input placeholder="+7 (999) 123-45-67" size="large" />
        </Form.Item>

        <Form.Item
          name="workplace"
          label="Место работы"
        >
          <Input placeholder="ООО Ромашка" size="large" />
        </Form.Item>

        <Form.Item
          name="residence"
          label="Место жительства"
        >
          <Input placeholder="г. Москва" size="large" />
        </Form.Item>

        <Form.Item>
          <Button 
            type="primary" 
            htmlType="submit" 
            loading={isLoading}
            size="large"
            block
            style={{ background: '#7b68ee' }}
          >
            {isLoading ? 'Создание...' : 'Создать семью'}
          </Button>
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default CreateFamilyModal;