import React, { useState, useEffect } from 'react';
import { Modal, Form, Tag, Input, Button, Select, DatePicker, message, Space, Divider, Typography } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { familyAPI, FamilyMember, RelativesGroup } from '../api/family';
import dayjs from 'dayjs';

const { Text } = Typography;

interface EditFamilyMemberModalProps {
  open: boolean;
  member: FamilyMember | null;
  familyId: number;
  members: FamilyMember[];
  relatives: RelativesGroup | null;
  onClose: () => void;
  onSuccess: () => void;
}

interface RelativeItem {
  id: number;
  name: string;
  type: string; 
  relationshipId: number; 
}

const EditFamilyMemberModal: React.FC<EditFamilyMemberModalProps> = ({
  open,
  member,
  familyId,
  members,
  relatives,
  onClose,
  onSuccess,
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [addRelativeModal, setAddRelativeModal] = useState<{
    visible: boolean;
    type: string; 
  }>({ visible: false, type: '' });
  const [selectedRelativeId, setSelectedRelativeId] = useState<number | undefined>(undefined);
  const [addingRelative, setAddingRelative] = useState(false);

  // Сброс формы при открытии
  useEffect(() => {
    if (member) {
      form.setFieldsValue({
        first_name: member.first_name,
        last_name: member.last_name,
        patronymic: member.patronymic,
        gender: member.gender,
        birth_date: member.birth_date ? dayjs(member.birth_date) : null,
        death_date: member.death_date ? dayjs(member.death_date) : null,
        phone: member.phone,
        workplace: member.workplace,
        residence: member.residence,
      });
    }
  }, [member, form]);

  
  const handleSavePersonal = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      const payload: any = {
        first_name: values.first_name,
        last_name: values.last_name,
        patronymic: values.patronymic || undefined,
        gender: values.gender,
        birth_date: values.birth_date?.toISOString(),
        death_date: values.death_date?.toISOString() || undefined,
        phone: values.phone || undefined,
        workplace: values.workplace || undefined,
        residence: values.residence || undefined,
      };

      await familyAPI.updateMember(member!.id, payload);
      message.success('Данные сохранены');
      onSuccess();
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Ошибка сохранения');
    } finally {
      setLoading(false);
    }
  };

  // Добавление связи
  const handleAddRelative = async () => {
    if (!selectedRelativeId) {
      message.warning('Выберите родственника');
      return;
    }
    setAddingRelative(true);
    try {
      await familyAPI.updateMember(member!.id, {
        related_member_id: selectedRelativeId,
        relationship_type: addRelativeModal.type,
      });
      message.success('Связь добавлена');
      setAddRelativeModal({ visible: false, type: '' });
      setSelectedRelativeId(undefined);
      onSuccess();
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Ошибка добавления связи');
    } finally {
      setAddingRelative(false);
    }
  };

  
  const getCandidates = (type: string) => {
    
    return members.filter(m => m.id !== member?.id);
  };

  const handleDeleteRelationship = async (relationshipId: number) => {
    try {
        await familyAPI.deleteRelationship(familyId, relationshipId);
        message.success('Связь удалена');
        onSuccess();
    } catch (error: any) {
        message.error(error.response?.data?.detail || 'Ошибка удаления связи');
    }
    };

  const getCurrentRelatives = (type: string): RelativeItem[] => {
    if (!relatives) return [];
    
    const items: RelativeItem[] = [];
    
    if (type === 'father' || type === 'mother') {
        relatives.parents
        .filter(p => (type === 'father' ? p.relationship_type === 'father' : p.relationship_type === 'mother'))
        .forEach(p => items.push({ id: p.id, name: `${p.first_name} ${p.last_name}`, type, relationshipId: Number(p.relationship_id)  }));
    }
    
    if (type === 'son' || type === 'daughter') {
        relatives.children
        .filter(c => (type === 'son' ? c.gender === 'male' : c.gender === 'female'))
        .forEach(c => items.push({ id: c.id, name: `${c.first_name} ${c.last_name}`, type, relationshipId: Number(c.relationship_id)  }));
    }
    
    if (type === 'brother') {
        relatives.siblings
            .filter(s => s.gender === 'male')
            .forEach(s => items.push({ id: s.id, name: `${s.first_name} ${s.last_name}`, type, relationshipId: Number(s.relationship_id) }));
    }
    if (type === 'sister') {
        relatives.siblings
            .filter(s => s.gender === 'female')
            .forEach(s => items.push({ id: s.id, name: `${s.first_name} ${s.last_name}`, type, relationshipId: Number(s.relationship_id) }));
    }
    
    if (type === 'spouse' || type === 'partner') {
        relatives.spouses.forEach(s => items.push({ id: s.id, name: `${s.first_name} ${s.last_name}`, type, relationshipId: Number(s.relationship_id)  }));
    }
    
    return items;
    };
  const openAddRelative = (type: string) => {
    setSelectedRelativeId(undefined);
    setAddRelativeModal({ visible: true, type });
  };

  if (!member) return null;

  return (
    <>
      <Modal
        title={`Редактирование: ${member.last_name} ${member.first_name}`}
        open={open}
        onCancel={onClose}
        footer={null}
        width={600}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="last_name" label="Фамилия" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="first_name" label="Имя" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="patronymic" label="Отчество">
            <Input />
          </Form.Item>
          <Form.Item name="birth_date" label="Дата рождения" rules={[{ required: true }]}>
            <DatePicker style={{ width: '100%' }} format="DD.MM.YYYY" />
          </Form.Item>
          <Form.Item name="death_date" label="Дата смерти">
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

          <Button type="primary" 
          onClick={handleSavePersonal} 
          style={{ background: '#7b68ee' }}
          loading={loading} block>
            Сохранить личные данные
          </Button>
        </Form>

        <Divider />

        {/* Управление связями */}
        <Typography.Title level={5}>Связи</Typography.Title>

        {(['father','mother','son','daughter','brother','sister','spouse','partner'] as const).map(type => (
          <div key={type} style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Text>{typeLabels[type]}: {getCurrentRelatives(type).map(r => (
                <Tag key={r.id} closable onClose={() => handleDeleteRelationship(r.relationshipId)}>
                    {r.name}
                </Tag>
                ))}</Text>
            <Button size="small" 
            icon={<PlusOutlined />} onClick={() => openAddRelative(type)}>Добавить</Button>
          </div>
        ))}
      </Modal>

      {/* Маленькое модальное окно для выбора родственника */}
      <Modal
        title={`Добавить ${typeLabels[addRelativeModal.type] || addRelativeModal.type}`}
        open={addRelativeModal.visible}
        onCancel={() => setAddRelativeModal({ visible: false, type: '' })}
        onOk={handleAddRelative}
        confirmLoading={addingRelative}
        okText="Добавить"
        cancelText="Отмена"
        okButtonProps={{ 
        style: { backgroundColor: '#7b68ee', borderColor: '#7b68ee' } 
      }}
      >
        <Select
          style={{ width: '100%' }}
          placeholder="Выберите члена семьи"
          value={selectedRelativeId}
          onChange={setSelectedRelativeId}
          showSearch
          filterOption={(input, option) =>
            (String(option?.label ?? '')).toLowerCase().includes(input.toLowerCase())
          }
        >
          {getCandidates(addRelativeModal.type).map(m => (
            <Select.Option key={m.id} value={m.id} label={`${m.last_name} ${m.first_name}`}>
              {m.last_name} {m.first_name} {m.patronymic || ''}
            </Select.Option>
          ))}
        </Select>
      </Modal>
    </>
  );
};

// Подписи к типам связей
const typeLabels: Record<string, string> = {
  father: 'Отец',
  mother: 'Мать',
  son: 'Сын',
  daughter: 'Дочь',
  brother: 'Брат',
  sister: 'Сестра',
  spouse: 'Супруг(а)',
  partner: 'Партнёр',
};


   
    

export default EditFamilyMemberModal;