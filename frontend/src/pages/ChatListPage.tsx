import React, { useState, useEffect } from 'react';
import { Card, List, Typography, Spin, Empty, Button, Tag, Avatar, Modal, Form, Input, Select, message} from 'antd';
import { MessageOutlined, TeamOutlined, PlusOutlined } from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext';
import { chatAPI, Chat } from '../api/chat';
import { useNavigate } from 'react-router-dom';


const { Title, Text } = Typography;

const ChatListPage: React.FC = () => {
  const { families, currentFamily, setCurrentFamily, loadUserFamilies } = useAuth();
  const [chats, setChats] = useState<Chat[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedFamilyId, setSelectedFamilyId] = useState<number | undefined>(currentFamily?.id);
  const [isLoadingFamilies, setIsLoadingFamilies] = useState(true);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [createForm] = Form.useForm();
  const [isCreating, setIsCreating] = useState(false);
  const navigate = useNavigate();
  // Загружаем семьи при монтировании
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

  // Загружаем чаты при выборе семьи
  useEffect(() => {
    if (selectedFamilyId) {
      loadChats();
    }
  }, [selectedFamilyId]);

  const loadChats = async () => {
    setIsLoading(true);
    try {
      const response = await chatAPI.list(selectedFamilyId);
      setChats(response.data.chats || []);
    } catch (error) {
      console.error('Ошибка загрузки чатов:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateChat = async (values: { name: string; member_ids?: number[] }) => {
    if (!selectedFamilyId) return;
    
    setIsCreating(true);
    try {
        await chatAPI.create({
        name: values.name,
        family_id: selectedFamilyId,
        member_ids: values.member_ids || [],
        });
        message.success('Чат создан');
        createForm.resetFields();
        setIsCreateModalOpen(false);
        loadChats(); 
    } catch (error: any) {
        console.error(error);
        message.error(error.response?.data?.detail || 'Ошибка создания чата');
    } finally {
        setIsCreating(false);
    }
  };

  const handleFamilyChange = (familyId: number) => {
    setSelectedFamilyId(familyId);
    const selected = families.find(f => f.id === familyId);
    if (selected) setCurrentFamily(selected);
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
    <div style={{ padding: '24px' }}>
      {/* Заголовок с выбором семьи */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <Title level={2} style={{ margin: 0 }}>Чаты</Title>
          <div style={{ marginTop: 8 }}>
            <Select
              value={selectedFamilyId}
              onChange={handleFamilyChange}
              style={{ width: 200 }}
              options={families.map(f => ({ value: f.id, label: f.name }))}
            />
          </div>
        </div>
        <Button 
        type="primary" 
        icon={<PlusOutlined />} 
        onClick={() => setIsCreateModalOpen(true)}
        style={{ background: '#7b68ee' }}
        >
        Создать чат
        </Button>
      </div>

      {/* Список чатов */}
      {isLoading ? (
        <div style={{ textAlign: 'center', padding: '50px' }}>
          <Spin size="large" />
        </div>
      ) : chats.length === 0 ? (
        <Empty description="В этой семье пока нет чатов. Создайте первый чат!" />
      ) : (
        <List
          dataSource={chats}
          renderItem={(chat) => (
            <List.Item
              style={{ cursor: 'pointer', padding: '16px', borderBottom: '1px solid #f0f0f0' }}
              onClick={() => navigate(`/chat/${chat.id}`)}
            >
              <List.Item.Meta
                avatar={<Avatar icon={<MessageOutlined />} style={{ backgroundColor: '#7b68ee' }} />}
                title={
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span>{chat.title}</span>
                    {chat.is_admin && <Tag color="purple">Админ</Tag>}
                    {chat.event_id && <Tag color="blue">Событие</Tag>}
                  </div>
                }
                description={
                  <div>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      <TeamOutlined /> Участников: {chat.members_count}
                    </Text>
                  </div>
                }
              />
            </List.Item>
          )}
        />
      )}

      <Modal
        title="Создать чат"
        open={isCreateModalOpen}
        onCancel={() => {
            setIsCreateModalOpen(false);
            createForm.resetFields();
        }}
        footer={null}
        destroyOnClose
        >
        <Form form={createForm} layout="vertical" onFinish={handleCreateChat}>
            <Form.Item
            name="name"
            label="Название чата"
            rules={[{ required: true, message: 'Введите название чата' }]}
            >
            <Input placeholder="Например: Общий чат" />
            </Form.Item>

            <Form.Item
            name="member_ids"
            label="Пригласить участников (опционально)"
            >
            <Select
                mode="multiple"
                placeholder="Выберите участников"
                options={[]} 
                disabled
            />
            </Form.Item>

            <Form.Item>
            <Button type="primary" htmlType="submit" loading={isCreating} block>
                Создать
            </Button>
            </Form.Item>
        </Form>
        </Modal>
    </div>
  );
};

export default ChatListPage;