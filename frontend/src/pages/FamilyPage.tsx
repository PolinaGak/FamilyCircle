import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Typography, Spin, Button, Descriptions, 
  message, Modal, Input, Space, Tag, Form, Select, Radio } from 'antd';
import { ArrowLeftOutlined, UserAddOutlined, CopyOutlined } from '@ant-design/icons';
import { familyAPI, Family, FamilyMember, RelativesGroup} from '../api/family';
import { invitationAPI, Invitation } from '../api/invitation';
import { useAuth } from '../contexts/AuthContext';
import { EditOutlined } from '@ant-design/icons';
import AddFamilyMemberModal from '../components/AddFamilyMemberModal';

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
  const [invitationType, setInvitationType] = useState<'new' | 'claim' | 'existing'>('new');
  const [isCreatingInvite, setIsCreatingInvite] = useState(false);
  const [isAddMemberModalOpen, setIsAddMemberModalOpen] = useState(false);
  const [inviteFormData, setInviteFormData] = useState({
    first_name: '',
    last_name: '',
    patronymic: '',
    birth_date: '',
    gender: 'male',
    phone: '',
    workplace: '',
    residence: '',
    relationship_type: undefined as string | undefined,
    related_member_id: undefined as number | undefined,

  });
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editFamilyName, setEditFamilyName] = useState('');
  const [expandedMemberId, setExpandedMemberId] = useState<number | null>(null);
  const [relativesMap, setRelativesMap] = useState<Record<number, RelativesGroup>>({});
  const [loadingRelatives, setLoadingRelatives] = useState(false);
  const [unlinkedMembers, setUnlinkedMembers] = useState<FamilyMember[]>([]);
  const loadFamilyData = async () => {
    if (!id) return;
    
    try {
      const familyResponse = await familyAPI.getFamilyDetail(Number(id));
      setFamily(familyResponse.data);
      
      const membersResponse = await familyAPI.getFamilyMembers(Number(id));
      setMembers(membersResponse.data);
      const unlinked = membersResponse.data.filter(m => !m.user_id);
      setUnlinkedMembers(unlinked);
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


  useEffect(() => {
    loadFamilyData();
  }, [id, user?.id]);

  //функция для обновления списка непривязанных карточек
  const refreshUnlinkedMembers = () => {
    const unlinked = members.filter(m => !m.user_id);
    setUnlinkedMembers(unlinked);
  };

  const getApiRelationshipType = (selectedRole: string, relatedMember: FamilyMember): string => {
    switch (selectedRole) {
      case 'father':
      case 'mother':
        return relatedMember.gender === 'male' ? 'son' : 'daughter';
      case 'son':
      case 'daughter':
        return relatedMember.gender === 'male' ? 'father' : 'mother';
      case 'brother':
      case 'sister':
        return selectedRole;
      case 'spouse':
      case 'partner':
        return selectedRole;
      default:
        return selectedRole;
    }
  };

  

  //создание карточки и приглашения
  const handleCreateInvitation = async () => {
    if (!id) return;
    setIsCreatingInvite(true);

    try {
      if (invitationType === 'new') {
        // Без создания карточки
        const invitationResponse = await invitationAPI.createNewMemberInvitation(Number(id), 7);
        setInviteCode(invitationResponse.data.code);
        message.success('Код приглашения создан!');
      } 
      else if (invitationType === 'claim') {
        // Создание карточки с возможной связью
        if (!inviteFormData.first_name || !inviteFormData.last_name || !inviteFormData.birth_date) {
          message.warning('Пожалуйста, заполните обязательные поля (Имя, Фамилия, Дата рождения)');
          setIsCreatingInvite(false);
          return;
        }

        const birthDate = new Date(inviteFormData.birth_date).toISOString();

        const memberPayload: any = {
          first_name: inviteFormData.first_name,
          last_name: inviteFormData.last_name,
          patronymic: inviteFormData.patronymic || undefined,
          birth_date: birthDate,
          gender: inviteFormData.gender,
          phone: inviteFormData.phone || undefined,
          workplace: inviteFormData.workplace || undefined,
          residence: inviteFormData.residence || undefined,
          is_admin: false,
        };

        // Если указана связь
        if (inviteFormData.relationship_type && inviteFormData.related_member_id) {
          const relatedMember = members.find(m => m.id === inviteFormData.related_member_id);
          if (!relatedMember) {
            message.error('Выбранный родственник не найден');
            setIsCreatingInvite(false);
            return;
          }
          memberPayload.related_member_id = relatedMember.id;
          memberPayload.relationship_type = getApiRelationshipType(inviteFormData.relationship_type, relatedMember);
        }

        const memberResponse = await familyAPI.createMember(Number(id), memberPayload);
        message.success('Карточка создана!');

        const invitationResponse = await invitationAPI.createClaimMemberInvitation(
          Number(id),
          memberResponse.data.id,
          7
        );
        setInviteCode(invitationResponse.data.code);
        message.success('Код приглашения создан!');

        // Обновить список членов
        const membersResponse = await familyAPI.getFamilyMembers(Number(id));
        setMembers(membersResponse.data);
      } 
      else if (invitationType === 'existing') {
        // Приглашение для существующей непривязанной карточки
        const selectedMemberId = inviteFormData.related_member_id; // используем это поле для хранения выбранного ID
        if (!selectedMemberId) {
          message.warning('Выберите карточку из списка');
          setIsCreatingInvite(false);
          return;
        }
        const invitationResponse = await invitationAPI.createClaimMemberInvitation(
          Number(id),
          selectedMemberId,
          7
        );
        setInviteCode(invitationResponse.data.code);
        message.success('Код приглашения создан!');
      }

      // Обновить список приглашений
      const invitationsResponse = await invitationAPI.getFamilyInvitations(Number(id));
      setInvitations(invitationsResponse.data.filter((inv: Invitation) => inv.is_active === true));

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



  const handleApproveMember = async (memberId: number, memberName: string) => {
    try {
      await familyAPI.approveMember(memberId, true);
      message.success(`Карточка "${memberName}" подтверждена`);
      loadFamilyData(); 
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Ошибка подтверждения');
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
      relationship_type: undefined as string | undefined,
      related_member_id: undefined as number | undefined,

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

  const loadRelatives = async (memberId: number) => {
    if (relativesMap[memberId]) return; 
    
    setLoadingRelatives(true);
    try {
      const response = await familyAPI.getMemberRelatives(Number(id), memberId);
      setRelativesMap(prev => ({ ...prev, [memberId]: response.data }));
    } catch (error) {
      console.error('Ошибка загрузки родственников:', error);
      message.error('Не удалось загрузить связи');
    } finally {
      setLoadingRelatives(false);
    }
  };

  const handleMemberClick = (memberId: number) => {
    if (expandedMemberId === memberId) {
      setExpandedMemberId(null);
    } else {
      setExpandedMemberId(memberId);
      loadRelatives(memberId);
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
              <Button danger onClick={handleDeleteFamily}>Удалить семью</Button>
              <Button type="primary" 
              icon={<UserAddOutlined />} 
              onClick={() => setIsInviteModalOpen(true)}
              style={{ background: '#7b68ee' }}
              >
                Пригласить
              </Button>
            </>
          )}
          {/* Кнопка для всех членов семьи */}
          <Button 
            type="default" 
            icon={<UserAddOutlined />}
            onClick={() => setIsAddMemberModalOpen(true)}
          >
            Добавить члена семьи
          </Button>
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
            <div key={member.id}>
              <div
                onClick={() => handleMemberClick(member.id)}
                style={{
                  padding: '12px',
                  border: '1px solid #e9ecef',
                  borderRadius: '8px',
                  background: '#f8f9fa',
                  cursor: 'pointer',
                  transition: 'background 0.2s',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = '#e9ecef')}
                onMouseLeave={(e) => (e.currentTarget.style.background = '#f8f9fa')}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <span style={{ fontWeight: 'bold' }}>
                      {member.last_name} {member.first_name} {member.patronymic || ''}
                    </span>
                    {member.is_admin && <Tag color="purple">Админ</Tag>}
                    {!member.user_id && (
                      member.approved ? (
                        <Tag color="green">Без аккаунта</Tag>
                      ) : (
                        <Tag color="orange">Ожидает подтверждения админом</Tag>
                      )
                    )}
                  </div>
                  <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                    {member.user_id === Number(user?.id) && <span style={{ color: '#666' }}>Это вы</span>}
                    
                    {/* Кнопки управления (без изменений) */}
                    {isAdmin && !member.approved && !member.user_id && (
                      <Button size="small" type="primary" onClick={(e) => { e.stopPropagation(); handleApproveMember(member.id, `${member.first_name} ${member.last_name}`); }} style={{ background: '#7b68ee' }}>Подтвердить</Button>
                    )}
                    {isAdmin && !member.is_admin && member.user_id !== null && (
                      <Button size="small" type="primary" style={{ background: '#7b68ee' }} onClick={(e) => { e.stopPropagation(); handleTransferAdmin(member.id, `${member.first_name} ${member.last_name}`); }}>Сделать админом</Button>
                    )}
                    {isAdmin && member.user_id !== Number(user?.id) && (
                      <Button size="small" danger onClick={(e) => { e.stopPropagation(); handleRemoveMember(member.id, `${member.first_name} ${member.last_name}`); }}>Исключить</Button>
                    )}
                  </div>
                </div>
              </div>

              {/* Раскрывающаяся панель с родственниками */}
              {expandedMemberId === member.id && (
                <div style={{
                  padding: '12px',
                  marginTop: '4px',
                  background: '#fff',
                  border: '1px solid #d9d9d9',
                  borderRadius: '0 0 8px 8px',
                  borderTop: 'none',
                }}>
                  {loadingRelatives && !relativesMap[member.id] ? (
                    <Spin />
                  ) : relativesMap[member.id] ? (
                    <div>
                      {relativesMap[member.id].parents.length > 0 && (
                        <div style={{ marginBottom: '8px' }}>
                          <Typography.Text strong>Родители:</Typography.Text>{' '}
                          {relativesMap[member.id].parents.map(p => (
                            <span key={p.id} style={{ marginRight: '12px' }}>
                              {p.first_name} {p.last_name} ({p.relationship_type === 'father' ? 'отец' : 'мать'})
                            </span>
                          ))}
                        </div>
                      )}
                      {relativesMap[member.id].children.length > 0 && (
                        <div style={{ marginBottom: '8px' }}>
                          <Typography.Text strong>Дети:</Typography.Text>{' '}
                          {relativesMap[member.id].children.map(c => (
                            <span key={c.id} style={{ marginRight: '12px' }}>
                              {c.first_name} {c.last_name}
                            </span>
                          ))}
                        </div>
                      )}
                      {relativesMap[member.id].spouses.length > 0 && (
                        <div style={{ marginBottom: '8px' }}>
                          <Typography.Text strong>Супруг(а):</Typography.Text>{' '}
                          {relativesMap[member.id].spouses.map(s => (
                            <span key={s.id} style={{ marginRight: '12px' }}>
                              {s.first_name} {s.last_name}
                            </span>
                          ))}
                        </div>
                      )}
                      {relativesMap[member.id].siblings.length > 0 && (
                        <div style={{ marginBottom: '8px' }}>
                          <Typography.Text strong>Братья/сёстры:</Typography.Text>{' '}
                          {relativesMap[member.id].siblings.map(sib => (
                            <span key={sib.id} style={{ marginRight: '12px' }}>
                              {sib.first_name} {sib.last_name}
                            </span>
                          ))}
                        </div>
                      )}
                      {Object.values(relativesMap[member.id]).every(arr => arr.length === 0) && (
                        <Typography.Text type="secondary">Нет указанных связей</Typography.Text>
                      )}
                    </div>
                  ) : (
                    <Typography.Text type="secondary">Нажмите, чтобы загрузить связи</Typography.Text>
                  )}
                </div>
              )}
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
                  setInvitationType(e.target.value);
                  setInviteFormData({
                    first_name: '',
                    last_name: '',
                    patronymic: '',
                    birth_date: '',
                    gender: 'male',
                    phone: '',
                    workplace: '',
                    residence: '',
                    relationship_type: undefined,
                    related_member_id: undefined,
                  });
                  if (e.target.value === 'existing') {
                    // Обновить список непривязанных
                    const unlinked = members.filter(m => !m.user_id);
                    setUnlinkedMembers(unlinked);
                  }
                }}
              >
                <Radio value="new">Без создания карточки</Radio>
                <Radio value="claim">С созданием карточки</Radio>
                <Radio value="existing">Выбрать существующую карточку</Radio>
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
                  <Form.Item label="Тип связи (необязательно)">
                    <Select
                      allowClear
                      placeholder="Кем будет новый член для выбранного родственника"
                      value={inviteFormData.relationship_type}
                      onChange={(value) => setInviteFormData({...inviteFormData, relationship_type: value})}
                    >
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

                  <Form.Item label="Родственник (необязательно)">
                    <Select
                      allowClear
                      placeholder="Выберите родственника"
                      disabled={!inviteFormData.relationship_type}
                      value={inviteFormData.related_member_id}
                      onChange={(value) => setInviteFormData({...inviteFormData, related_member_id: value})}
                      showSearch
                      filterOption={(input, option) =>
                        (String(option?.label ?? '')).toLowerCase().includes(input.toLowerCase())
                      }
                    >
                      {members.map((member) => (
                        <Select.Option key={member.id} value={member.id} label={`${member.last_name} ${member.first_name}`}>
                          {member.last_name} {member.first_name} {member.patronymic || ''}
                        </Select.Option>
                      ))}
                    </Select>
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
            {invitationType === 'existing' && (
            <div>
              <p>Выберите непривязанную карточку для приглашения:</p>
              {unlinkedMembers.length === 0 ? (
                <p style={{ color: '#999' }}>Нет непривязанных карточек. Сначала создайте карточку через «Добавить члена семьи».</p>
              ) : (
                <Select
                  style={{ width: '100%' }}
                  placeholder="Выберите карточку"
                  value={inviteFormData.related_member_id}
                  onChange={(value) => setInviteFormData({...inviteFormData, related_member_id: value})}
                  showSearch
                  filterOption={(input, option) =>
                    (String(option?.label ?? '')).toLowerCase().includes(input.toLowerCase())
                  }
                >
                  {unlinkedMembers.map((m) => (
                    <Select.Option key={m.id} value={m.id} label={`${m.last_name} ${m.first_name}`}>
                      {m.last_name} {m.first_name} {m.patronymic || ''}
                      {m.birth_date ? ` (${new Date(m.birth_date).getFullYear()})` : ''}
                    </Select.Option>
                  ))}
                </Select>
              )}
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

    <AddFamilyMemberModal
        open={isAddMemberModalOpen}
        onClose={() => setIsAddMemberModalOpen(false)}
        familyId={Number(id)}
        onSuccess={() => {
          loadFamilyData();
        }}
      />
    </div>
  );
};

export default FamilyPage;