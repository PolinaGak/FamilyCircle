import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Typography, Spin, Button, Descriptions, message, Modal, Input, Space, Tag, Form, Select, Radio } from 'antd';
import { ArrowLeftOutlined, UserAddOutlined, CopyOutlined } from '@ant-design/icons';
import { familyAPI, Family, FamilyMember} from '../api/family';
import { invitationAPI, Invitation } from '../api/invitation';
import { useAuth } from '../contexts/AuthContext';
import { EditOutlined } from '@ant-design/icons';

const { Title } = Typography;
const FamilyPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user, loadUserFamilies } = useAuth();
  const [family, setFamily] = useState<Family | null>(null);
  const [members, setMembers] = useState<FamilyMember[]>([]);
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [inviteCode, setInviteCode] = useState('');
  const [invitationType, setInvitationType] = useState<'new' | 'claim'>('new');
  const [isCreatingInvite, setIsCreatingInvite] = useState(false);
  const [inviteFormData, setInviteFormData] = useState({
    first_name: '',
    last_name: '',
    patronymic: '',
    birth_date: '',
    gender: 'male',
    phone: '',
    workplace: '',
    residence: '',
  });
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editFamilyName, setEditFamilyName] = useState('');

  // Загружаем данные семьи
  useEffect(() => {
    const loadFamilyData = async () => {
      if (!id) return;
      
      try {
        const familyResponse = await familyAPI.getFamilyDetail(Number(id));
        setFamily(familyResponse.data);
        
        const membersResponse = await familyAPI.getFamilyMembers(Number(id));
        setMembers(membersResponse.data);
        
        const currentMember = membersResponse.data.find(m => m.user_id === Number(user?.id));
        const adminStatus = currentMember?.is_admin || false;
        setIsAdmin(adminStatus);
        
        if (adminStatus) {
          try {
            const invitationsResponse = await invitationAPI.getFamilyInvitations(Number(id));
            const activeInvitations = filterActiveInvitations(invitationsResponse.data);
            setInvitations(activeInvitations);
          } catch (error) {
            console.error('Ошибка загрузки приглашений:', error);
          }
        }
        
      } catch (error) {
        console.error('Ошибка загрузки семьи:', error);
        message.error('Не удалось загрузить информацию о семье');
      } finally {
        setIsLoading(false);
      }
    };
    
    loadFamilyData();
  }, [id, user?.id]);

  //создание карточки и приглашения
  const handleCreateInvitation = async () => {
    if (!id) return;
    
    setIsCreatingInvite(true);
    
    try {
      let invitationResponse;
      
      if (invitationType === 'new') {
        //для нового:
        invitationResponse = await invitationAPI.createNewMemberInvitation(Number(id), 7);
        message.success('Код приглашения создан!');
        
      } else {
        // для существующего:
        // Валидация формы
        if (!inviteFormData.first_name || !inviteFormData.last_name || !inviteFormData.birth_date) {
          message.warning('Пожалуйста, заполните обязательные поля (Имя, Фамилия, Дата рождения)');
          setIsCreatingInvite(false);
          return;
        }
        
        const birthDate = new Date(inviteFormData.birth_date).toISOString();
        
        // Создаем карточку родственника
        const memberResponse = await familyAPI.createMember(Number(id), {
          first_name: inviteFormData.first_name,
          last_name: inviteFormData.last_name,
          patronymic: inviteFormData.patronymic || undefined,
          birth_date: birthDate,
          gender: inviteFormData.gender,
          phone: inviteFormData.phone || undefined,
          workplace: inviteFormData.workplace || undefined,
          residence: inviteFormData.residence || undefined,
          is_admin: false,
        } as any);
        
        message.success('Карточка создана!');
        invitationResponse = await invitationAPI.createClaimMemberInvitation(
          Number(id), 
          memberResponse.data.id,
          7
        );
        message.success('Код приглашения создан!');
        const membersResponse = await familyAPI.getFamilyMembers(Number(id));
        setMembers(membersResponse.data);
      }
      
      setInviteCode(invitationResponse.data.code);
      
      const invitationsResponse = await invitationAPI.getFamilyInvitations(Number(id));
      const activeInvitations = filterActiveInvitations(invitationsResponse.data);
      setInvitations(activeInvitations);
      
    } catch (error: any) {
      console.error('Ошибка:', error);
      const errorDetail = error.response?.data?.detail;
      if (errorDetail?.includes('уже существует')) {
        message.error('Этот пользователь уже является членом семьи');
      } else if (errorDetail?.includes('лимит')) {
        message.error('Достигнут лимит приглашений');
      } else {
        message.error(errorDetail || 'Не удалось создать приглашение');
      }
    } finally {
      setIsCreatingInvite(false);
    }
  };

  //Фильтруем только активные приглашения
  const filterActiveInvitations = (invitations: Invitation[]) => {
    return invitations.filter(inv => inv.is_active === true);
  };

  const copyInviteCode = () => {
    navigator.clipboard.writeText(inviteCode);
    message.success('Код скопирован в буфер обмена');
  };

  const resetModal = () => {
    setIsInviteModalOpen(false);
    setInviteCode('');
    setInviteFormData({
      first_name: '',
      last_name: '',
      patronymic: '',
      birth_date: '',
      gender: 'male',
      phone: '',
      workplace: '',
      residence: '',
    });
  };

  //функция отзыва приглашения
  const handleDeactivateInvitation = async (invitationId: number, invitationCode: string) => {
  try {
    await invitationAPI.deactivateInvitation(invitationId);
    message.success(`Приглашение ${invitationCode} отозвано`);
    setInvitations(prev => prev.filter(inv => inv.id !== invitationId));
    
  } catch (error: any) {
    console.error('Ошибка отзыва приглашения:', error);
    message.error(error.response?.data?.detail || 'Не удалось отозвать приглашение');
  }
};

  const handleRemoveMember = async (memberId: number, memberName: string) => {
    console.log('Попытка удаления:', { memberId, memberName }); //   
    if (!window.confirm(`Вы уверены, что хотите исключить ${memberName} из семьи?`)) {
      console.log('Удаление отменено'); 
      return;
    }
    console.log('Отправка DELETE запроса...'); 
    try {
      const response = await familyAPI.removeMember(memberId);
      console.log('Ответ:', response); 
      message.success(`${memberName} исключен(а) из семьи`);
      
      const membersResponse = await familyAPI.getFamilyMembers(Number(id));
      setMembers(membersResponse.data);
      
      if (isAdmin) {
        const invitationsResponse = await invitationAPI.getFamilyInvitations(Number(id));
        setInvitations(invitationsResponse.data.filter(inv => inv.is_active === true));
      }
      
    } catch (error: any) {
      console.error('Ошибка удаления:', error);
      message.error(error.response?.data?.detail || 'Не удалось исключить участника');
    }
  };


  
  //Выход из семьи участника
  const handleLeaveFamily = async () => {
    if (!window.confirm(`Вы уверены, что хотите покинуть семью "${family?.name}"?`)) {
      return;
    }
    
    try {
      await familyAPI.leaveFamily(Number(id));
      message.success(`Вы покинули семью "${family?.name}"`);
      await loadUserFamilies();
      navigate('/dashboard');
      
    } catch (error: any) {
      console.error('Ошибка выхода из семьи:', error);
      message.error(error.response?.data?.detail || 'Не удалось покинуть семью');
    }
  };

  //удаление семьи ее администратором
  const handleDeleteFamily = async () => {
    if (!window.confirm(`Вы уверены, что хотите удалить семью "${family?.name}"?`)) {
      return;
    }
    
    if (!window.confirm(`Это действие нельзя будет отменить. Все данные семьи будут удалены. Вы уверены?`)) {
      return;
    }
    
    try {
      await familyAPI.deleteFamily(Number(id));
      message.success(`Семья "${family?.name}" удалена`);
      await loadUserFamilies();
      navigate('/dashboard');
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Не удалось удалить семью');
    }
  };

  
  //передача прав админа
  const handleTransferAdmin = async (targetMemberId: number, memberName: string) => {
    if (!window.confirm(`Вы уверены, что хотите передать права администратора "${memberName}"?`)) {
      return;
    }
    
    if (!window.confirm(`Вы перестанете быть администратором. Это действие можно отменить, только если новый администратор передаст права обратно. Продолжить?`)) {
      return;
    }
    
    try {
      await familyAPI.transferAdmin(Number(id), targetMemberId);
      message.success(`Права администратора переданы "${memberName}"`);
      const membersResponse = await familyAPI.getFamilyMembers(Number(id));
      setMembers(membersResponse.data);
      const currentMember = membersResponse.data.find(m => m.user_id === Number(user?.id));
      setIsAdmin(currentMember?.is_admin || false);
      if (!currentMember?.is_admin) {
        setInvitations([]);
      }
      
    } catch (error: any) {
      console.error('Ошибка передачи прав:', error);
      message.error(error.response?.data?.detail || 'Не удалось передать права администратора');
    }
  };

  //функция редактирования названия семьи
  const handleUpdateFamilyName = async () => {
    if (!editFamilyName.trim()) {
      message.warning('Название семьи не может быть пустым');
      return;
    }
    
    try {
      await familyAPI.updateFamily(Number(id), editFamilyName);
      message.success('Название семьи обновлено');
      const updatedFamily = await familyAPI.getFamilyDetail(Number(id));
      setFamily(updatedFamily.data);
      await loadUserFamilies();
      setIsEditModalOpen(false);
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Не удалось обновить название');
    }
  };


  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!family) {
    return (
      <div style={{ padding: '20px' }}>
        <Title level={4}>Семья не найдена</Title>
        <Button onClick={() => navigate('/dashboard')}>Вернуться на главную</Button>
      </div>
    );
  }

  return (
    <div style={{ padding: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <Button 
          icon={<ArrowLeftOutlined />} 
          onClick={() => navigate('/dashboard')}
        >
          На главную
        </Button>
        
        {!isAdmin && (
          <Button 
            danger
            onClick={handleLeaveFamily}
          >
            Покинуть семью
          </Button>
        )}

        {isAdmin && (
          <>
            <Button 
              danger
              onClick={handleDeleteFamily}
            >
              Удалить семью
            </Button>
            <Button 
              type="primary" 
              icon={<UserAddOutlined />}
              onClick={() => setIsInviteModalOpen(true)}
              style={{ background: '#7b68ee' }}
            >
              Пригласить
            </Button>
          </>
        )}
      </div>
      
      <Card>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <Title level={2} style={{ margin: 0 }}>{family.name}</Title>
          {isAdmin && (
            <Button 
              type="text" 
              icon={<EditOutlined />} 
              onClick={() => {
                setEditFamilyName(family.name);
                setIsEditModalOpen(true);
              }}
            />
          )}
        </div>
        
        <Descriptions bordered column={1} style={{ marginTop: '20px' }}>
          <Descriptions.Item label="ID семьи">{family.id}</Descriptions.Item>
          <Descriptions.Item label="Дата создания">
            {new Date(family.created_at).toLocaleDateString()}
          </Descriptions.Item>
          <Descriptions.Item label="Ваша роль">
            {isAdmin ? 'Администратор' : 'Участник'}
          </Descriptions.Item>
        </Descriptions>
        
        <Title level={4} style={{ marginTop: '30px' }}>Члены семьи ({members.length})</Title>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {members.map((member) => (
            <div key={member.id} style={{
              padding: '12px',
              border: '1px solid #e9ecef',
              borderRadius: '8px',
              background: '#f8f9fa'}}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <span style={{ fontWeight: 'bold' }}>
                    {member.last_name} {member.first_name} {member.patronymic || ''}
                  </span>
                  {member.is_admin && <Tag color="purple" style={{ marginLeft: '10px' }}>Админ</Tag>}
                  {!member.user_id && <Tag color="orange" style={{ marginLeft: '10px' }}>Ожидает привязки</Tag>}
                </div>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                  {member.user_id === Number(user?.id) && (
                    <span style={{ color: '#666', fontSize: '12px' }}>Это вы</span>
                  )}
                  
                  {/* Кнопка "Сделать администратором" только для текущего админа и для обычных участников */}
                  {isAdmin && !member.is_admin && member.user_id !== null && (
                    <Button 
                      size="small" 
                      type="primary"
                      style={{ background: '#7b68ee' }}
                      onClick={() => handleTransferAdmin(member.id, `${member.first_name} ${member.last_name}`)}
                    >
                      Сделать админом
                    </Button>
                  )}
                  
                  {/* Кнопка удаления только для администратора и не для себя */}
                  {isAdmin && member.user_id !== Number(user?.id) && (
                    <Button 
                      size="small" 
                      danger 
                      onClick={() => handleRemoveMember(member.id, `${member.first_name} ${member.last_name}`)}
                    >
                      Исключить
                    </Button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {isAdmin && invitations.length > 0 && (
  <>
        <Title level={4} style={{ marginTop: '30px' }}>Активные приглашения</Title>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {invitations.map((inv) => (
            <div 
              key={inv.id} 
              style={{ 
                padding: '10px', 
                background: '#f0f0f0', 
                borderRadius: '8px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}
            >
              <div>
                <span style={{ fontFamily: 'monospace', fontWeight: 'bold' }}>{inv.code}</span>
                <span style={{ marginLeft: '10px', fontSize: '12px', color: '#666' }}>
                  Действительно до: {new Date(inv.expires_at).toLocaleDateString()}
                </span>
              </div>
              <Button 
                size="small" 
                danger 
                onClick={() => handleDeactivateInvitation(inv.id, inv.code)}
              >
                Отменить
              </Button>
            </div>
          ))}
        </div>
      </>
    )}
      </Card>

      {/* Модальное окно для создания приглашения */}
      <Modal
        title="Пригласить участника"
        open={isInviteModalOpen}
        onCancel={resetModal}
        footer={null}
        width={500}
      >
        {!inviteCode ? (
          <div>
            {/*переключатель типа приглашения*/}
            <Form.Item label="Тип приглашения" required style={{ marginBottom: '16px' }}>
              <Radio.Group 
                value={invitationType} 
                onChange={(e) => {
                  setInvitationType(e.target.value)
                  if (e.target.value === 'new') {
                    setInviteFormData({
                      first_name: '',
                      last_name: '',
                      patronymic: '',
                      birth_date: '',
                      gender: 'male',
                      phone: '',
                      workplace: '',
                      residence: '',
                    });
                  }
                }}
              >
                <Radio value="new">
                  Без создания карточки
                </Radio>
                <Radio value="claim">
                  С созданием карточки
                </Radio>
              </Radio.Group>
            </Form.Item>

            {/*форма для существующего*/}
            {invitationType === 'claim' && (
              <>
                <p>Создайте карточку для нового участника:</p>
                <Form layout="vertical">
                  <Form.Item label="Имя" required>
                    <Input 
                      value={inviteFormData.first_name}
                      onChange={(e) => setInviteFormData({...inviteFormData, first_name: e.target.value})}
                      placeholder="Введите имя"
                    />
                  </Form.Item>
                  <Form.Item label="Фамилия" required>
                    <Input 
                      value={inviteFormData.last_name}
                      onChange={(e) => setInviteFormData({...inviteFormData, last_name: e.target.value})}
                      placeholder="Введите фамилию"
                    />
                  </Form.Item>
                  <Form.Item label="Отчество">
                    <Input 
                      value={inviteFormData.patronymic}
                      onChange={(e) => setInviteFormData({...inviteFormData, patronymic: e.target.value})}
                      placeholder="Введите отчество (необязательно)"
                    />
                  </Form.Item>
                  <Form.Item label="Дата рождения" required>
                    <Input 
                      type="date"
                      value={inviteFormData.birth_date}
                      onChange={(e) => setInviteFormData({...inviteFormData, birth_date: e.target.value})}
                    />
                  </Form.Item>
                  <Form.Item label="Пол" required>
                    <Select 
                      value={inviteFormData.gender}
                      onChange={(value) => setInviteFormData({...inviteFormData, gender: value})}
                      placeholder="Выберите пол"
                    >
                      <Select.Option value="male">Мужской</Select.Option>
                      <Select.Option value="female">Женский</Select.Option>
                    </Select>
                  </Form.Item>
                  <Form.Item label="Телефон">
                    <Input 
                      value={inviteFormData.phone}
                      onChange={(e) => setInviteFormData({...inviteFormData, phone: e.target.value})}
                      placeholder="+7-XXX-XXX-XX-XX (необязательно)"
                    />
                  </Form.Item>
                  <Form.Item label="Место работы">
                    <Input 
                      value={inviteFormData.workplace}
                      onChange={(e) => setInviteFormData({...inviteFormData, workplace: e.target.value})}
                      placeholder="Необязательно"
                    />
                  </Form.Item>
                  <Form.Item label="Место жительства">
                    <Input 
                      value={inviteFormData.residence}
                      onChange={(e) => setInviteFormData({...inviteFormData, residence: e.target.value})}
                      placeholder="Необязательно"
                    />
                  </Form.Item>
                </Form>
              </>
            )}

            {/*информация для нового пользователя*/}
            {invitationType === 'new' && (
              <div style={{ 
                background: '#f0f5ff', 
                padding: '16px', 
                borderRadius: '8px',
                marginBottom: '20px'
              }}>
                <p style={{ margin: '8px 0 0', fontSize: '14px', color: '#666' }}>
                  Пользователь сам внесет свои данные
                </p>
              </div>
            )}
            <Button 
              type="primary" 
              onClick={handleCreateInvitation}
              loading={isCreatingInvite}
              style={{ width: '100%', background: '#7b68ee', marginTop: '16px' }}
            >
              Создать код приглашения
            </Button>
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: '20px' }}>
            <p>Отправьте этот код новому участнику:</p>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Input.TextArea 
                value={inviteCode} 
                readOnly 
                rows={2}
                style={{ textAlign: 'center', fontFamily: 'monospace', fontSize: '18px' }}
              />
              <Button icon={<CopyOutlined />} onClick={copyInviteCode} style={{ width: '100%' }}>
                Копировать код
              </Button>
            </Space>
            <p style={{ marginTop: '20px', color: '#666', fontSize: '12px' }}>
              Код действителен 7 дней. После активации участник сможет войти в семью.
            </p>
            <Button onClick={resetModal} style={{ marginTop: '20px' }}>
              Закрыть
            </Button>
          </div>
        )}
      </Modal>

      {/*модальное окно для редактирования названия семьи*/}
      <Modal
      title="Редактировать название семьи"
      open={isEditModalOpen}
      onOk={handleUpdateFamilyName}
      onCancel={() => setIsEditModalOpen(false)}
      okText="Сохранить"     
      cancelText="Отмена"  
      okButtonProps={{ 
        style: { backgroundColor: '#7b68ee', borderColor: '#7b68ee' } 
      }} 
    >
      <Input
        value={editFamilyName}
        onChange={(e) => setEditFamilyName(e.target.value)}
        placeholder="Введите новое название семьи"
        autoFocus
      />
    </Modal>
    </div>
  );
};

export default FamilyPage;