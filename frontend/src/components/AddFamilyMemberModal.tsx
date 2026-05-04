import React, { useState, useEffect } from 'react';
import { Modal, Form, Input, Button, Select, DatePicker, message } from 'antd';
import { familyAPI, FamilyMember } from '../api/family';

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
  const [familyMembers, setFamilyMembers] = useState<FamilyMember[]>([]);
  const [selectedRelationship, setSelectedRelationship] = useState<string | undefined>(undefined);

  useEffect(() => {
    if (open) {
      loadFamilyMembers();
    } else {
      setFamilyMembers([]);
      setSelectedRelationship(undefined);
    }
  }, [open, familyId]);

  const loadFamilyMembers = async () => {
    try {
      const response = await familyAPI.getFamilyMembers(familyId);
      setFamilyMembers(response.data);
    } catch (error) {
      console.error('Ошибка загрузки членов семьи:', error);
      message.error('Не удалось загрузить список членов семьи');
    }
  };

  // Фильтрация родственников в зависимости от выбранной роли нового члена
  const getFilteredMembers = () => {
    if (!selectedRelationship) return [];

    // Для брата/сестры родственник должен быть соотв. пола
    if (selectedRelationship === 'brother') {
      return familyMembers.filter(m => m.gender === 'male');
    }
    if (selectedRelationship === 'sister') {
      return familyMembers.filter(m => m.gender === 'female');
    }

    // Для остальных ролей показываем всех
    return familyMembers;
  };

  const handleRelationshipChange = (value: string | undefined) => {
    setSelectedRelationship(value);
    form.resetFields(['related_member_id']);
  };

  // Преобразование выбранной роли нового члена в тип связи для API
  const getApiRelationshipType = (selectedRole: string, relatedMember: FamilyMember): string => {
    switch (selectedRole) {
      case 'father':
      case 'mother':
        // Новый – родитель, значит родственник – ребёнок
        return relatedMember.gender === 'male' ? 'son' : 'daughter';
      case 'son':
      case 'daughter':
        // Новый – ребёнок, значит родственник – родитель
        return relatedMember.gender === 'male' ? 'father' : 'mother';
      case 'brother':
      case 'sister':
        // Родственник будет братом/сестрой нового
        return selectedRole; // brother / sister
      case 'spouse':
      case 'partner':
        return selectedRole; // spouse / partner
      default:
        return selectedRole;
    }
  };

  const handleSubmit = async (values: any) => {
    if ((values.relationship_type && !values.related_member_id) ||
        (!values.relationship_type && values.related_member_id)) {
      message.warning('Выберите и тип связи, и родственника');
      return;
    }

    setLoading(true);
    try {
      const birthDate = values.birth_date ? values.birth_date.toISOString() : null;
      const deathDate = values.death_date ? values.death_date.toISOString() : null;

      const memberData: any = {
        first_name: values.first_name,
        last_name: values.last_name,
        patronymic: values.patronymic || undefined,
        birth_date: birthDate,
        gender: values.gender,
        death_date: deathDate || undefined,
        phone: values.phone || undefined,
        workplace: values.workplace || undefined,
        residence: values.residence || undefined,
        is_admin: false,
      };

      if (values.relationship_type && values.related_member_id) {
        const relatedMember = familyMembers.find(m => m.id === values.related_member_id);
        if (!relatedMember) {
          message.error('Выбранный родственник не найден');
          return;
        }
        memberData.related_member_id = relatedMember.id;
        memberData.relationship_type = getApiRelationshipType(values.relationship_type, relatedMember);
      }

      await familyAPI.createMember(familyId, memberData);

      if (values.relationship_type && values.related_member_id) {
        const relatedMember = familyMembers.find(m => m.id === values.related_member_id);
        const roleLabels: Record<string, string> = {
          father: 'отцом',
          mother: 'матерью',
          son: 'сыном',
          daughter: 'дочерью',
          brother: 'братом',
          sister: 'сестрой',
          spouse: 'супругом(ой)',
          partner: 'партнёром',
        };
        const role = roleLabels[values.relationship_type] || values.relationship_type;
        message.success(
          `${values.first_name} ${values.last_name} теперь является ${role} для ${relatedMember?.first_name} ${relatedMember?.last_name}`
        );
      } else {
        message.success('Карточка родственника создана');
      }

      form.resetFields();
      setSelectedRelationship(undefined);
      onSuccess();
      onClose();
    } catch (error: any) {
      console.error('Ошибка создания:', error);
      const detail = error.response?.data?.detail;
      if (detail?.includes('не может быть отцом')) message.error('Ошибка: выбранный родственник не может быть отцом (не мужской пол)');
      else if (detail?.includes('не может быть матерью')) message.error('Ошибка: выбранный родственник не может быть матерью (не женский пол)');
      else if (detail?.includes('не может быть братом')) message.error('Ошибка: выбранный родственник не может быть братом (не мужской пол)');
      else if (detail?.includes('не может быть сестрой')) message.error('Ошибка: выбранный родственник не может быть сестрой (не женский пол)');
      else if (detail?.includes('цикл')) message.error('Ошибка: образуется цикл в родословной');
      else if (detail?.includes('уже существует')) message.error('Такая связь уже существует');
      else message.error(detail || 'Ошибка создания');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    form.resetFields();
    setSelectedRelationship(undefined);
    onClose();
  };

  return (
    <Modal title="Добавить члена семьи" open={open} onCancel={handleCancel} footer={null} width={500} destroyOnClose>
      <Form form={form} layout="vertical" onFinish={handleSubmit}>
        <Form.Item name="last_name" label="Фамилия" rules={[{ required: true, message: 'Введите фамилию' }]}>
          <Input placeholder="Введите фамилию" />
        </Form.Item>
        <Form.Item name="first_name" label="Имя" rules={[{ required: true, message: 'Введите имя' }]}>
          <Input placeholder="Введите имя" />
        </Form.Item>
        <Form.Item name="patronymic" label="Отчество">
          <Input placeholder="Введите отчество (необязательно)" />
        </Form.Item>
        <Form.Item name="birth_date" label="Дата рождения" rules={[{ required: true, message: 'Выберите дату' }]}>
          <DatePicker style={{ width: '100%' }} format="DD.MM.YYYY" placeholder="Выберите дату рождения" />
        </Form.Item>
        <Form.Item name="death_date" label="Дата смерти (если есть)">
          <DatePicker style={{ width: '100%' }} format="DD.MM.YYYY" placeholder="Выберите дату смерти" />
        </Form.Item>
        <Form.Item name="gender" label="Пол" rules={[{ required: true, message: 'Выберите пол' }]}>
          <Select placeholder="Выберите пол">
            <Select.Option value="male">Мужской</Select.Option>
            <Select.Option value="female">Женский</Select.Option>
          </Select>
        </Form.Item>
        <Form.Item name="phone" label="Телефон">
          <Input placeholder="+7-XXX-XXX-XX-XX (необязательно)" />
        </Form.Item>
        <Form.Item name="workplace" label="Место работы">
          <Input placeholder="Место работы (необязательно)" />
        </Form.Item>
        <Form.Item name="residence" label="Место жительства">
          <Input placeholder="Место жительства (необязательно)" />
        </Form.Item>

        <Form.Item
          name="relationship_type"
          label="Кем приходится новый член выбранному родственнику"
          tooltip="Выберите роль нового члена по отношению к существующему"
        >
          <Select allowClear placeholder="Выберите тип связи" onChange={handleRelationshipChange}>
            <Select.Option value="father">Отец</Select.Option>
            <Select.Option value="mother">Мать</Select.Option>
            <Select.Option value="son">Сын</Select.Option>
            <Select.Option value="daughter">Дочь</Select.Option>
            <Select.Option value="brother">Брат</Select.Option>
            <Select.Option value="sister">Сестра</Select.Option>
            <Select.Option value="spouse">Супруг(а)</Select.Option>
            <Select.Option value="partner">Партнёр</Select.Option>
          </Select>
        </Form.Item>

        <Form.Item
          name="related_member_id"
          label="Родственник (необязательно)"
          tooltip="Выберите существующего члена семьи"
        >
          <Select
            allowClear
            placeholder={selectedRelationship ? 'Выберите родственника' : 'Сначала выберите тип связи'}
            disabled={!selectedRelationship}
            showSearch
            filterOption={(input, option) =>
              (String(option?.label ?? '')).toLowerCase().includes(input.toLowerCase())
            }
            notFoundContent={getFilteredMembers().length === 0 ? 'Нет подходящих кандидатов' : 'Нет членов семьи'}
          >
            {getFilteredMembers().map((member) => (
              <Select.Option
                key={member.id}
                value={member.id}
                label={`${member.last_name} ${member.first_name} ${member.patronymic || ''}`}
              >
                {member.last_name} {member.first_name} {member.patronymic || ''}
                {member.birth_date && ` (${new Date(member.birth_date).getFullYear()})`}
              </Select.Option>
            ))}
          </Select>
        </Form.Item>

        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading} block style={{ background: '#7b68ee' }}>
            Создать
          </Button>
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default AddFamilyMemberModal;