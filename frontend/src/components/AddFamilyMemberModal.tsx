import React, { useState } from 'react';
import { Modal, Form, Input, Button, Select, DatePicker, message } from 'antd';
import { familyAPI } from '../api/family';
import dayjs from 'dayjs';

interface AddFamilyMemberModalProps {
  open: boolean;
  onClose: () => void;
  familyId: number;
  onSuccess: () => void;
}

const AddFamilyMemberModal: React.FC<AddFamilyMemberModalProps> = ({
  open,
  onClose,
  familyId,
  onSuccess,
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (values: any) => {
    setLoading(true);
    try {
      const birthDate = values.birth_date ? values.birth_date.toISOString() : null;
      const deathDate = values.death_date ? values.death_date.toISOString() : null;

      await familyAPI.createMember(familyId, {
        first_name: values.first_name,
        last_name: values.last_name,
        patronymic: values.patronymic,
        birth_date: birthDate,
        gender: values.gender,
        death_date: deathDate,
        phone: values.phone,
        workplace: values.workplace,
        residence: values.residence,
        is_admin: false,      
      });

      message.success('Карточка родственника создана');
      form.resetFields();
      onSuccess();
      onClose();
    } catch (error: any) {
      console.error(error);
      message.error(error.response?.data?.detail || 'Ошибка создания');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title="Добавить члена семьи"
      open={open}
      onCancel={() => {
        form.resetFields();
        onClose();
      }}
      footer={null}
      width={500}
      destroyOnClose
    >
      <Form form={form} layout="vertical" onFinish={handleSubmit}>
        <Form.Item name="last_name" label="Фамилия" rules={[{ required: true, message: 'Введите фамилию' }]}>
          <Input />
        </Form.Item>
        <Form.Item name="first_name" label="Имя" rules={[{ required: true, message: 'Введите имя' }]}>
          <Input />
        </Form.Item>
        <Form.Item name="patronymic" label="Отчество">
          <Input />
        </Form.Item>
        <Form.Item name="birth_date" label="Дата рождения" rules={[{ required: true, message: 'Выберите дату' }]}>
          <DatePicker style={{ width: '100%' }} format="DD.MM.YYYY" />
        </Form.Item>
        <Form.Item name="death_date" label="Дата смерти (если есть)">
          <DatePicker style={{ width: '100%' }} format="DD.MM.YYYY" />
        </Form.Item>
        <Form.Item name="gender" label="Пол" rules={[{ required: true }]}>
          <Select>
            <Select.Option value="male">Мужской</Select.Option>
            <Select.Option value="female">Женский</Select.Option>
          </Select>
        </Form.Item>
        <Form.Item name="phone" label="Телефон">
          <Input />
        </Form.Item>
        <Form.Item name="workplace" label="Место работы">
          <Input />
        </Form.Item>
        <Form.Item name="residence" label="Место жительства">
          <Input />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading} block
           style = {{ background: '#7b68ee' }}
          >
            Создать
          </Button>
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default AddFamilyMemberModal;