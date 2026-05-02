// frontend/src/pages/CalendarPage.tsx
import React, { useState, useEffect } from 'react';
import { Calendar, dateFnsLocalizer } from 'react-big-calendar';
import { format, parse, startOfWeek, getDay } from 'date-fns';
import { ru } from 'date-fns/locale';
import { Card, Spin, Select, Typography, Button, Modal, Form, Input, DatePicker, message, Switch } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext';
import { eventAPI, CalendarEvent } from '../api/event';
import 'react-big-calendar/lib/css/react-big-calendar.css';
import { familyAPI } from '../api/family';
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
        <div>
          <Title level={2} style={{ margin: 0 }}>Календарь</Title>
          <Select
            value={selectedFamilyId}
            onChange={handleFamilyChange}
            style={{ width: 200, marginTop: 8 }}
            options={families.map(f => ({ value: f.id, label: f.name }))}
          />
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

      {/* Календарь */}
    <Card style={{ height: 'calc(100vh - 200px)', borderRadius: '12px', overflow: 'auto' }}>
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
};

export default CalendarPage;