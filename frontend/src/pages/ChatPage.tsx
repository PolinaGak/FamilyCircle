import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Button, Typography, Spin, Input, 
  message, Empty, Form, Tag
} from 'antd';
import { 
  ArrowLeftOutlined, SendOutlined
} from '@ant-design/icons';
import { chatAPI, ChatMember } from '../api/chat';
import { messageAPI, Message } from '../api/message';
import { message as antdMessage, Modal, Dropdown } from 'antd';
import { useAuth } from '../contexts/AuthContext';
import { List, Avatar, Select } from 'antd';
import { UserAddOutlined, TeamOutlined, UserOutlined } from '@ant-design/icons';
import { familyAPI } from '../api/family';
import { EditOutlined, DeleteOutlined, CheckOutlined, CloseOutlined } from '@ant-design/icons';
const { Title, Text } = Typography;
const { TextArea } = Input;

const ChatPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user, currentFamily  } = useAuth();
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [chatName, setChatName] = useState('');
  const [isAdmin, setIsAdmin] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [form] = Form.useForm();
  const [selectedMessage, setSelectedMessage] = useState<Message | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editContent, setEditContent] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [members, setMembers] = useState<ChatMember[]>([]);
  const [isMembersModalOpen, setIsMembersModalOpen] = useState(false);
  const [isAddMemberModalOpen, setIsAddMemberModalOpen] = useState(false);
  const [availableMembers, setAvailableMembers] = useState<any[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [isLoadingMembers, setIsLoadingMembers] = useState(false);
  const [isAddingMember, setIsAddingMember] = useState(false);
  const [membersCount, setMembersCount] = useState(0);
  const [editChatName, setEditChatName] = useState('');
  const [isMessageEditModalOpen, setIsMessageEditModalOpen] = useState(false);
  const [isMessageEditing, setIsMessageEditing] = useState(false);
  useEffect(() => {
    if (id) {
      loadMessages();
      loadChatInfo();
    }
  }, [id]);

  const loadChatInfo = async () => {
    try {
      const response = await chatAPI.getById(Number(id));
      setChatName(response.data.title);
      setIsAdmin(response.data.is_admin || false);
      setMembersCount(response.data.members_count);
    } catch (error) {
      console.error('Ошибка загрузки информации о чате:', error);
    }
  };

  const loadMessages = async () => {
    setIsLoading(true);
    try {
        const response = await messageAPI.getMessages(Number(id));
        const messagesData = response.data.messages || [];
        const sortedMessages = [...messagesData].sort((a, b) => 
        new Date(a.sent_at).getTime() - new Date(b.sent_at).getTime()
        );
        
        setMessages(sortedMessages);
    } catch (error) {
        console.error('Ошибка загрузки сообщений:', error);
        message.error('Не удалось загрузить сообщения');
    } finally {
        setIsLoading(false);
    }
    };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async (values: { content: string }) => {
    if (!values.content.trim()) return;
    
    setIsSending(true);
    try {
        const response = await messageAPI.send(Number(id), values.content);
        const newMessage = response.data;
        setMessages(prev => [...prev, newMessage]);
        form.resetFields();
    } catch (error: any) {
        console.error('Ошибка отправки:', error);
        message.error(error.response?.data?.detail || 'Не удалось отправить сообщение');
    } finally {
        setIsSending(false);
    }
    };

  const formatDateTime = (dateString: string) => {
    if (!dateString) return '';
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) return '';
      return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return '';
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) return '';
      const today = new Date();
      const yesterday = new Date(today);
      yesterday.setDate(yesterday.getDate() - 1);
      
      if (date.toDateString() === today.toDateString()) {
        return 'Сегодня';
      } else if (date.toDateString() === yesterday.toDateString()) {
        return 'Вчера';
      }
      return date.toLocaleDateString('ru-RU');
    } catch {
      return '';
    }
  };

  
  const isMyMessage = (msg: Message): boolean => {
    if (!msg.sender_user_id || !user?.id) return false;
    return Number(msg.sender_user_id) === Number(user.id);
  };

  // Группировка сообщений по датам
  const groupedMessages = () => {
    const groups: { date: string; messages: Message[] }[] = [];
    let currentDate = '';
    
    messages.forEach(msg => {
      if (!msg.sent_at) return;
      const msgDate = new Date(msg.sent_at).toDateString();
      if (msgDate !== currentDate) {
        currentDate = msgDate;
        groups.push({
          date: formatDate(msg.sent_at),
          messages: [msg]
        });
      } else {
        groups[groups.length - 1].messages.push(msg);
      }
    });
    return groups;
  };

  const handleEditMessage = async () => {
  if (!selectedMessage || !editContent.trim()) return;
  
  setIsEditing(true);
  try {
    const response = await messageAPI.update(
      Number(id), 
      selectedMessage.id, 
      editContent
    );
    
    // Обновляем сообщение в списке
    setMessages(prev => prev.map(msg => 
      msg.id === selectedMessage.id 
        ? { ...msg, content: editContent, is_edited: true }
        : msg
    ));
    
    setIsMessageEditModalOpen(false);
    setSelectedMessage(null);
    setEditContent('');
  } catch (error: any) {
    message.error(error.response?.data?.detail || 'Не удалось редактировать сообщение');
  } finally {
    setIsEditing(false);
  }
};

// Удаление сообщения
const handleDeleteMessage = async (message: Message) => {
  Modal.confirm({
    title: 'Удалить сообщение',
    content: 'Вы уверены, что хотите удалить это сообщение?',
    okText: 'Удалить',
    cancelText: 'Отмена',
    okButtonProps: { danger: true },
    onOk: async () => {
      try {
        await messageAPI.delete(Number(id), message.id);
        setMessages(prev => prev.filter(msg => msg.id !== message.id));
        antdMessage.success('Сообщение удалено');
      } catch (error: any) {
        antdMessage.error(error.response?.data?.detail || 'Не удалось удалить сообщение');
      }
    },
  });
};
  
// Загрузить участников чата
const loadMembers = async () => {
  setIsLoadingMembers(true);
  try {
    const response = await chatAPI.getMembers(Number(id));
    const membersData = response.data;
    setMembersCount(membersData.length);
    const currentMember = membersData.find(m => m.user_id === Number(user?.id));
    if (currentMember) {
      setIsAdmin(currentMember.is_admin);
    }
    // Получаем всех членов семьи для подстановки имён
    if (currentFamily) {
      const familyMembers = await familyAPI.getFamilyMembers(currentFamily.id);
      const userMap = new Map();
      familyMembers.data.forEach((member: any) => {
        if (member.user_id) {
          userMap.set(member.user_id, `${member.first_name} ${member.last_name}`);
        }
      });
      
      const membersWithNames = membersData.map((member: ChatMember) => ({
        ...member,
        user: {
          id: member.user_id,
          name: userMap.get(member.user_id) || `Пользователь ${member.user_id}`,
        }
      }));
      setMembers(membersWithNames);
    } else {
      setMembers(membersData);
    }
  } catch (error) {
    console.error('Ошибка загрузки участников:', error);
    antdMessage.error('Не удалось загрузить участников');
  } finally {
    setIsLoadingMembers(false);
  }
};

// Загрузить доступных участников из семьи (кто ещё не в чате)
const loadAvailableMembers = async () => {
  try {
    // Получаем всех членов семьи
    const familyMembersResponse = await familyAPI.getFamilyMembers(Number(currentFamily?.id));
    const existingMemberIds = new Set(members.map(m => m.user_id));
    const available = familyMembersResponse.data.filter(
      (member: any) => member.user_id && !existingMemberIds.has(member.user_id)
    );
    setAvailableMembers(available);
  } catch (error) {
    console.error('Ошибка загрузки доступных участников:', error);
  }
};

// Добавить участника
const handleAddMember = async () => {
  if (!selectedUserId) return;
  setIsAddingMember(true);
  try {
    await chatAPI.addMember(Number(id), selectedUserId);
    antdMessage.success('Участник добавлен');
    await loadMembers();
    setIsAddMemberModalOpen(false);
    setSelectedUserId(null);
  } catch (error: any) {
    antdMessage.error(error.response?.data?.detail || 'Не удалось добавить участника');
  } finally {
    setIsAddingMember(false);
  }
};

// Удалить участника
const handleRemoveMember = async (userId: number, userName: string) => {
  Modal.confirm({
    title: 'Удалить участника',
    content: `Вы уверены, что хотите удалить "${userName}" из чата?`,
    okText: 'Удалить',
    cancelText: 'Отмена',
    okButtonProps: { danger: true },
    onOk: async () => {
      try {
        await chatAPI.removeMember(Number(id), userId);
        antdMessage.success('Участник удален');
        await loadMembers();
      } catch (error: any) {
        antdMessage.error(error.response?.data?.detail || 'Не удалось удалить участника');
      }
    },
  });
};

const handleLeaveChat = () => {
  Modal.confirm({
    title: 'Покинуть чат',
    content: 'Вы уверены, что хотите покинуть этот чат? Вы потеряете доступ к сообщениям.',
    okText: 'Покинуть',
    cancelText: 'Отмена',
    okButtonProps: { danger: true },
    onOk: async () => {
      try {
        await chatAPI.leave(Number(id));
        antdMessage.success('Вы покинули чат');
        navigate('/chats');
      } catch (error: any) {
        antdMessage.error(error.response?.data?.detail || 'Не удалось покинуть чат');
      }
    },
  });
};

  const handleTransferAdmin = async (newAdminUserId: number, userName: string) => {
    Modal.confirm({
      title: 'Передать права администратора',
      content: `Вы уверены, что хотите передать права админа "${userName}"? Вы станете обычным участником.`,
      okButtonProps: {
          style: {
            backgroundColor: '#7b68ee'
            
          }
        },
      okText: 'Передать',
      cancelText: 'Отмена',
      onOk: async () => {
        try {
          await chatAPI.transferAdmin(Number(id), newAdminUserId);
          antdMessage.success(`Права администратора переданы "${userName}"`);
          await loadChatInfo();
          await loadMembers();
        } catch (error: any) {
          antdMessage.error(error.response?.data?.detail || 'Не удалось передать права');
        }
      },
    });
  };

  const handleUpdateChat = async () => {
    if (!editChatName.trim()) {
      antdMessage.warning('Название чата не может быть пустым');
      return;
    }
    
    setIsEditing(true);
    try {
      await chatAPI.update(Number(id), { name: editChatName });
      setChatName(editChatName);
      antdMessage.success('Название чата обновлено');
      setIsEditModalOpen(false);
    } catch (error: any) {
      antdMessage.error(error.response?.data?.detail || 'Не удалось обновить название');
    } finally {
      setIsEditing(false);
    }
  };

  // Удаление чата
  const handleDeleteChat = () => {
    Modal.confirm({
      title: 'Удалить чат',
      content: 'Вы уверены, что хотите удалить этот чат? Все сообщения будут потеряны без возможности восстановления.',
      okText: 'Удалить',
      cancelText: 'Отмена',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await chatAPI.delete(Number(id));
          antdMessage.success('Чат удален');
          navigate('/chats');
        } catch (error: any) {
          antdMessage.error(error.response?.data?.detail || 'Не удалось удалить чат');
        }
      },
    });
  };

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 64px)' }}>
      {/* Шапка чата */}
      <div style={{ 
        padding: '16px 24px', 
        borderBottom: '1px solid #f0f0f0',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/chats')}>
            Назад
          </Button>
          <Title level={4} style={{ margin: 0 }}>{chatName || `Чат ${id}`}</Title>
          {isAdmin && <Text type="secondary" style={{ fontSize: 12 }}>(Администратор)</Text>}
        </div>
        
        <div style={{ display: 'flex', gap: '8px' }}>
          <Button 
            type="text" 
            icon={<TeamOutlined />} 
            onClick={() => {
              loadMembers();
              setIsMembersModalOpen(true);
            }}
          >
            Участники ({membersCount})
          </Button>
          {isAdmin && (
            <>
              <Button 
                type="text" 
                danger
                icon={<DeleteOutlined />} 
                onClick={handleDeleteChat}
              />
              
            </>
          )}
          {!isAdmin && (
            <Button danger onClick={handleLeaveChat}>
              Покинуть чат
            </Button>
          )}
        </div>
      </div>

      {/* Область сообщений */}
      <div style={{ 
        flex: 1, 
        overflowY: 'auto', 
        padding: '20px',
        background: '#f5f5f5'
      }}>
        {messages.length === 0 ? (
          <Empty 
            description="Нет сообщений. Начните общение!" 
            style={{ marginTop: 50 }}
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        ) : (
          groupedMessages().map((group, idx) => (
            <div key={idx}>
              <div style={{ textAlign: 'center', margin: '16px 0' }}>
                <Text type="secondary" style={{ background: '#e8e8e8', padding: '4px 12px', borderRadius: '16px' }}>
                  {group.date}
                </Text>
              </div>
              {group.messages.map((msg) => {
                const myMessage = isMyMessage(msg);
                const canEdit = myMessage;  
                const canDelete = myMessage || isAdmin;  
                

                const menuItems = [
                ...(canEdit ? [{
                  key: 'edit',
                  label: '✏️ Редактировать',
                  onClick: () => {
                    setSelectedMessage(msg);
                    setEditContent(msg.content);
                    setIsMessageEditModalOpen(true);
                  },
                }] : []),
                ...(canDelete ? [{
                  key: 'delete',
                  label: '🗑️ Удалить',
                  danger: true,
                  onClick: () => handleDeleteMessage(msg),
                }] : []),
              ];

                return (

                  <Dropdown
                  menu={{ items: menuItems }}
                  trigger={['contextMenu']}  
                >

                  <div
                    key={msg.id}
                    style={{
                      display: 'flex',
                      justifyContent: myMessage ? 'flex-end' : 'flex-start',
                      marginBottom: '12px'
                    }}
                  >
                    <div style={{ maxWidth: '70%' }}>
                      {!myMessage && (
                        <Text type="secondary" style={{ fontSize: 12, marginLeft: 8, display: 'block' }}>
                          {msg.sender_name || `Пользователь ${msg.sender_user_id}`}
                        </Text>
                      )}
                      <div
                        style={{
                          background: myMessage ? '#7b68ee' : '#fff',
                          color: myMessage ? '#fff' : '#333',
                          padding: '8px 12px',
                          borderRadius: 12,
                          borderTopRightRadius: myMessage ? 4 : 12,
                          borderTopLeftRadius: myMessage ? 12 : 4,
                          boxShadow: '0 1px 2px rgba(0,0,0,0.1)',
                          wordBreak: 'break-word'
                        }}
                      >
                        {msg.content}
                      </div>
                      <Text type="secondary" style={{ fontSize: 10, marginLeft: 8 }}>
                        {formatDateTime(msg.sent_at)}
                        {msg.is_edited && <span> (ред.)</span>}
                      </Text>
                    </div>
                  </div>
                  </Dropdown>
                );
              })}
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Форма отправки сообщения */}
      <div style={{ 
        padding: '16px 24px', 
        borderTop: '1px solid #f0f0f0',
        background: '#fff'
      }}>
        <Form form={form} onFinish={handleSendMessage} style={{ display: 'flex', gap: '8px' }}>
          <Form.Item name="content" style={{ flex: 1, marginBottom: 0 }}>
            <TextArea
              rows={1}
              placeholder="Введите сообщение..."
              autoSize={{ minRows: 1, maxRows: 4 }}
              onPressEnter={(e) => {
                if (!e.shiftKey) {
                  e.preventDefault();
                  form.submit();
                }
              }}
            />
          </Form.Item>
          <Button 
            type="primary" 
            htmlType="submit" 
            icon={<SendOutlined />} 
            loading={isSending}
            style={{ background: '#7b68ee' }}
          />
        </Form>
      </div>

      <Modal
        title="Редактировать сообщение"
        open={isMessageEditModalOpen}
        onCancel={() => {
          setIsMessageEditModalOpen(false);
          setSelectedMessage(null);
          setEditContent('');
        }}
        onOk={handleEditMessage}
        confirmLoading={isEditing}
        okText="Сохранить"
        okButtonProps={{
          style: {
            backgroundColor: '#7b68ee'
            
          }
        }}
        cancelText="Отмена"
      >
        <Input.TextArea
          value={editContent}
          onChange={(e) => setEditContent(e.target.value)}
          rows={3}
          placeholder="Введите текст сообщения"
        />
      </Modal>

      <Modal
        title="Участники чата"
        open={isMembersModalOpen}
        onCancel={() => {
          setIsMembersModalOpen(false);
          setSelectedUserId(null);
        }}
        footer={null}
        width={500}
      >
        {isLoadingMembers ? (
          <div style={{ textAlign: 'center', padding: 20 }}>
            <Spin />
          </div>
        ) : (
          <>
            {/* Кнопка добавления — только для админа */}
            {isAdmin && (
              <Button 
                type="dashed" 
                icon={<UserAddOutlined />} 
                onClick={() => {
                  loadAvailableMembers();
                  setIsAddMemberModalOpen(true);
                }}
                style={{ marginBottom: 16, width: '100%' }}
              >
                Добавить участника
              </Button>
            )}
            
            <List
              dataSource={members}
              renderItem={(member) => (
                <List.Item
                  actions={[
                    // Действия только для админа (и не для себя)
                    isAdmin && member.user_id !== Number(user?.id) && (
                      <>
                        {!member.is_admin && (
                          <Button 
                            size="small" 
                            type="primary"
                            style={{ background: '#7b68ee' }}
                            onClick={() => handleTransferAdmin(member.user_id, member.user?.name || `Пользователь ${member.user_id}`)}
                          >
                            Передать права
                          </Button>
                        )}
                        <Button 
                          size="small" 
                          danger 
                          onClick={() => handleRemoveMember(member.user_id, member.user?.name || `Пользователь ${member.user_id}`)}
                        >
                          Удалить
                        </Button>
                      </>
                    )
                  ].filter(Boolean)}
                >
                  <List.Item.Meta
                    avatar={<Avatar icon={<UserOutlined />} />}
                    title={
                      <span>
                        {member.user?.name || `Пользователь ${member.user_id}`}
                        {member.is_admin && <Tag color="purple" style={{ marginLeft: 8 }}>Админ</Tag>}
                      </span>
                    }
                  />
                </List.Item>
              )}
            />
          </>
        )}
      </Modal>

      <Modal
        title="Добавить участника"
        open={isAddMemberModalOpen}
        onCancel={() => {
          setIsAddMemberModalOpen(false);
          setSelectedUserId(null);
        }}
        onOk={handleAddMember}
        confirmLoading={isAddingMember}
        okText="Добавить"
        cancelText="Отмена"
        okButtonProps={{
          style: {
            backgroundColor: '#7b68ee'
            
          }
        }}
      >
        <Select
          placeholder="Выберите участника"
          style={{ width: '100%' }}
          
          onChange={(value) => {
            console.log('Выбран участник с ID:', value);
            setSelectedUserId(value);
          }}
          options={availableMembers.map((member) => ({
            value: member.user_id,
            label: `${member.last_name} ${member.first_name}`,
          }))}
        />
      </Modal>

      <Modal
        title="Редактировать название чата"
        open={isEditModalOpen}
        onCancel={() => {
          setIsEditModalOpen(false);
          setEditChatName('');
        }}
        onOk={handleUpdateChat}
        confirmLoading={isEditing}
        okText="Сохранить"
        cancelText="Отмена"
      >
        <Input
          value={editChatName}
          onChange={(e) => setEditChatName(e.target.value)}
          placeholder="Название чата"
          autoFocus
        />
      </Modal>

      
    </div>
  );
};

export default ChatPage;