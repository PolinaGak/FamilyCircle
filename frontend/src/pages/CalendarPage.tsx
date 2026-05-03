// frontend/src/pages/CalendarPage.tsx
import React, { useState, useEffect } from 'react';
import { Calendar, dateFnsLocalizer } from 'react-big-calendar';
import { format, parse, startOfWeek, getDay } from 'date-fns';
import { useParams, useNavigate } from 'react-router-dom';
import { ru } from 'date-fns/locale';
import { Card, Spin, Select, Typography, Button, Modal, Form, Input, DatePicker, message, Switch } from 'antd';
import { PlusOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext';
import { eventAPI, CalendarEvent } from '../api/event';
import 'react-big-calendar/lib/css/react-big-calendar.css';
import { familyAPI } from '../api/family';
import { Tabs, List, Empty } from 'antd';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

// Настройка локализации для календаря
const locales = {
  'ru': ru,
};

const localizer = dateFnsLocalizer({
  format,
  parse,
  startOfWeek,
  getDay,
  locales,
});

// Функция для преобразования событий в формат react-big-calendar
const transformEvents = (events: CalendarEvent[]) => {
  return events.map(event => ({
    id: event.id,
    title: event.title,
    start: new Date(event.start_datetime),
    end: new Date(event.end_datetime),
    allDay: false,
  }));
};

const CalendarPage: React.FC = () => {
  const { families, currentFamily, setCurrentFamily, loadUserFamilies } = useAuth();
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [form] = Form.useForm();
  const [isCreating, setIsCreating] = useState(false);
  const [selectedFamilyId, setSelectedFamilyId] = useState<number | undefined>(currentFamily?.id);
  const [isLoadingFamilies, setIsLoadingFamilies] = useState(true);
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [selectedEventId, setSelectedEventId] = useState<number | null>(null);
  const [availableMembers, setAvailableMembers] = useState<any[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [isInviting, setIsInviting] = useState(false);
  const [pendingInvitations, setPendingInvitations] = useState<any[]>([]);
  const [isLoadingInvitations, setIsLoadingInvitations] = useState(false);
  const [respondingEventId, setRespondingEventId] = useState<number | null>(null);
  
  
    useEffect(() => {
    const loadData = async () => {
        setIsLoadingFamilies(true);
        if (families.length === 0) {
        await loadUserFamilies();
        }
        if (families.length > 0 && !currentFamily) {
        setCurrentFamily(families[0]);
        setSelectedFamilyId(families[0].id);
        }
        setIsLoadingFamilies(false);
    };
    loadData();
    }, []);

  const loadEvents = async () => {
    if (!selectedFamilyId) return;
    
    setIsLoading(true);
    try {
        const response = await eventAPI.getCalendarEvents(selectedFamilyId);
        setEvents(response.data);
    } catch (error) {
        console.error('Ошибка загрузки событий:', error);
        message.error('Не удалось загрузить события');
    } finally {
        setIsLoading(false);
    }
  };

  useEffect(() => {
    if (selectedFamilyId) {
        loadEvents();
    }
    }, [selectedFamilyId]);

    const loadAvailableMembersForEvent = async (eventId: number) => {
        if (!selectedFamilyId) return;
        
        try {
            const eventResponse = await eventAPI.getById(eventId);
            const existingParticipantIds = eventResponse.data.participants.map(p => p.user_id);
            
            const familyMembersResponse = await familyAPI.getFamilyMembers(selectedFamilyId);
            const available = familyMembersResponse.data.filter(
            (member: any) => member.user_id && !existingParticipantIds.includes(member.user_id)
            );
            setAvailableMembers(available);
        } catch (error) {
            console.error('Ошибка загрузки участников:', error);
            message.error('Не удалось загрузить список участников');
        }
    };

    useEffect(() => {
    if (selectedFamilyId) {
        loadEvents();
        loadPendingInvitations();
    }
    }, [selectedFamilyId]);

    const handleInviteMember = async () => {
        if (!selectedEventId || !selectedUserId) return;
        
        setIsInviting(true);
        try {
            await eventAPI.inviteParticipant(selectedEventId, selectedUserId);
            message.success('Приглашение отправлено');
            setIsInviteModalOpen(false);
            setSelectedUserId(null);
            loadEvents(); 
        } catch (error: any) {
            message.error(error.response?.data?.detail || 'Не удалось пригласить участника');
        } finally {
            setIsInviting(false);
        }
    };

  
  const handleFamilyChange = (familyId: number) => {
    setSelectedFamilyId(familyId);
    const selected = families.find(f => f.id === familyId);
    if (selected) setCurrentFamily(selected);
  };

  const handleCreateEvent = async (values: any) => {
    if (!selectedFamilyId) return;
    
    setIsCreating(true);
    try {
      const [start, end] = values.dateRange;
      
      await eventAPI.create({
        title: values.title,
        description: values.description,
        family_id: selectedFamilyId,
        start_datetime: start.toISOString(),
        end_datetime: end.toISOString(),
        create_chat: values.create_chat || false,
        invite_members: [],
      });
      
      message.success('Событие создано');
      form.resetFields();
      setIsModalOpen(false);
      loadEvents();
    } catch (error: any) {
      console.error('Ошибка создания:', error);
      message.error(error.response?.data?.detail || 'Не удалось создать событие');
    } finally {
      setIsCreating(false);
    }
  };

  const loadPendingInvitations = async () => {
    setIsLoadingInvitations(true);
    try {
        const response = await eventAPI.getPendingInvitations();
        setPendingInvitations(response.data);
    } catch (error) {
        console.error('Ошибка загрузки приглашений:', error);
    } finally {
        setIsLoadingInvitations(false);
    }
    };

    const handleRespondToInvitation = async (eventId: number, accept: boolean) => {
    setRespondingEventId(eventId);
    try {
        await eventAPI.respondToInvitation(eventId, accept);
        message.success(accept ? 'Вы приняли приглашение' : 'Вы отклонили приглашение');
        await loadPendingInvitations();
        await loadEvents();
    } catch (error: any) {
        message.error(error.response?.data?.detail || 'Ошибка при ответе на приглашение');
    } finally {
        setRespondingEventId(null);
    }
    };

  const handleEventClick = (event: any) => {
    const eventId = event.id;
    setSelectedEventId(eventId);
    loadAvailableMembersForEvent(eventId);
    setIsInviteModalOpen(true);
  };

  if (isLoadingFamilies) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (families.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Title level={4}>У вас нет семей</Title>
        <Text type="secondary">Создайте или присоединитесь к семье на главной странице</Text>
      </div>
    );
  }
return (
  <div style={{ padding: '24px', height: 'calc(100vh - 64px)' }}>
    {/* Заголовок с выбором семьи и кнопкой создания */}
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        
        <div>
          <Title level={2} style={{ margin: 0 }}>Календарь</Title>
          <Select
            value={selectedFamilyId}
            onChange={handleFamilyChange}
            style={{ width: 200, marginTop: 8 }}
            options={families.map(f => ({ value: f.id, label: f.name }))}
          />
        </div>
      </div>
      <Button 
        type="primary" 
        icon={<PlusOutlined />} 
        onClick={() => setIsModalOpen(true)}
        style={{ background: '#7b68ee' }}
      >
        Создать событие
      </Button>
    </div>

    {/* Вкладки: Календарь и Приглашения */}
    <Tabs
      defaultActiveKey="calendar"
      items={[
        {
          key: 'calendar',
          label: 'Календарь',
          children: (
            <Card style={{ height: 'calc(100vh - 270px)', borderRadius: '12px', overflow: 'auto' }}>
              {isLoading ? (
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                  <Spin size="large" />
                </div>
              ) : (
                <Calendar
                  localizer={localizer}
                  events={transformEvents(events)}
                  startAccessor="start"
                  endAccessor="end"
                  style={{ height: '100%', minHeight: 600 }}
                  culture="ru"
                  onSelectEvent={handleEventClick}
                  messages={{
                    today: 'Сегодня',
                    previous: 'Назад',
                    next: 'Вперед',
                    month: 'Месяц',
                    week: 'Неделя',
                    day: 'День',
                    agenda: 'Повестка',
                    date: 'Дата',
                    time: 'Время',
                    event: 'Событие',
                    noEventsInRange: 'Нет событий в выбранном периоде',
                  }}
                />
              )}
            </Card>
          ),
        },
        {
          key: 'invitations',
          label: `Приглашения (${pendingInvitations.length})`,
          children: (
            <Card style={{ borderRadius: '12px' }}>
              {isLoadingInvitations ? (
                <div style={{ textAlign: 'center', padding: 40 }}>
                  <Spin size="large" />
                </div>
              ) : pendingInvitations.length === 0 ? (
                <Empty description="Нет ожидающих приглашений" />
              ) : (
                <List
                  dataSource={pendingInvitations}
                  renderItem={(inv) => (
                    <List.Item
                      actions={[
                        <Button 
                          type="primary" 
                          size="small"
                          loading={respondingEventId === inv.event_id}
                          onClick={() => handleRespondToInvitation(inv.event_id, true)}
                          style={{ background: '#52c41a' }}
                        >
                          Принять
                        </Button>,
                        <Button 
                          danger 
                          size="small"
                          loading={respondingEventId === inv.event_id}
                          onClick={() => handleRespondToInvitation(inv.event_id, false)}
                        >
                          Отклонить
                        </Button>,
                      ]}
                    >
                      <List.Item.Meta
                        title={<strong>{inv.event_title}</strong>}
                        description={
                          <div>
                            <div>Семья: {inv.family_name}</div>
                            <div>📅 Начало: {new Date(inv.start_datetime).toLocaleString()}</div>
                            <div>🔚 Окончание: {new Date(inv.end_datetime).toLocaleString()}</div>
                            <div>🕒 Приглашение отправлено: {new Date(inv.invited_at).toLocaleString()}</div>
                          </div>
                        }
                      />
                    </List.Item>
                  )}
                />
              )}
            </Card>
          ),
        },
      ]}
    />
    {/* Модальное окно для приглашения участников */}
    <Modal
    title="Пригласить участников"
    open={isInviteModalOpen}
    onCancel={() => {
        setIsInviteModalOpen(false);
        setSelectedUserId(null);
    }}
    onOk={handleInviteMember}
    confirmLoading={isInviting}
    okText="Пригласить"
    cancelText="Отмена"
    okButtonProps={{
        style: { backgroundColor: '#7b68ee' }
    }}
    >
    <Select
        placeholder="Выберите участника"
        style={{ width: '100%' }}
        onChange={(value) => setSelectedUserId(value)}
        options={availableMembers.map((member) => ({
        value: member.user_id,
        label: `${member.last_name} ${member.first_name}`,
        }))}
    />
    </Modal>

    {/* Модальное окно создания события */}
      <Modal
        title="Создать событие"
        open={isModalOpen}
        onCancel={() => {
          setIsModalOpen(false);
          form.resetFields();
        }}
        footer={null}
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={handleCreateEvent}>
          <Form.Item
            name="title"
            label="Название"
            rules={[{ required: true, message: 'Введите название' }]}
          >
            <Input placeholder="Например: День рождения" />
          </Form.Item>

          <Form.Item
            name="description"
            label="Описание"
          >
            <Input.TextArea rows={3} placeholder="Описание события (необязательно)" />
          </Form.Item>

          <Form.Item
            name="dateRange"
            label="Дата и время"
            rules={[{ required: true, message: 'Выберите дату и время' }]}
          >
            <RangePicker showTime format="DD.MM.YYYY HH:mm" style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="create_chat"
            label="Создать чат для события"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" 
            loading={isCreating} block
            style={{ background: '#7b68ee' }}
            >
              Создать
            </Button>
          </Form.Item>
        </Form>
      </Modal>
  </div>
);
}

export default CalendarPage;