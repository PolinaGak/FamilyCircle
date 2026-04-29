import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Button, Typography, Spin, Input, 
  message, Empty, Form 
} from 'antd';
import { 
  ArrowLeftOutlined, SendOutlined
} from '@ant-design/icons';
import { chatAPI } from '../api/chat';
import { messageAPI, Message } from '../api/message';
import { useAuth } from '../contexts/AuthContext';

const { Title, Text } = Typography;
const { TextArea } = Input;

const ChatPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [chatName, setChatName] = useState('');
  const [isAdmin, setIsAdmin] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [form] = Form.useForm();

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

  // Функция для определения, является ли сообщение своим
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
        gap: '16px'
      }}>
        <Button 
          icon={<ArrowLeftOutlined />} 
          onClick={() => navigate('/chats')}
        >
          Назад
        </Button>
        <Title level={4} style={{ margin: 0 }}>{chatName || `Чат ${id}`}</Title>
        {isAdmin && <Text type="secondary" style={{ fontSize: 12 }}>(Администратор)</Text>}
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
                return (
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
    </div>
  );
};

export default ChatPage;