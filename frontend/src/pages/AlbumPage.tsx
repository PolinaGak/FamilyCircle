import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Card, Row, Col, Button, Spin, Empty, Typography, 
  message, Modal, Upload, Popconfirm, Tooltip, Descriptions, Input, List, Select, Form
} from 'antd';
import { 
  ArrowLeftOutlined, UploadOutlined, DeleteOutlined, 
  ClockCircleOutlined, EditOutlined
} from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext';
import { albumAPI, Album, AlbumMember } from '../api/album';
import { photoAPI, Photo } from '../api/photo';
import { TeamOutlined, UserAddOutlined, CrownOutlined, DeleteOutlined as DeleteUserOutlined } from '@ant-design/icons';
import { UserOutlined } from '@ant-design/icons';
import { Tabs } from 'antd';
import { familyAPI } from '../api/family';

const { Title, Text, Paragraph } = Typography;

const PhotoImage: React.FC<{ photoId: number; size: string; onClick?: () => void }> = ({ photoId, size, onClick }) => {
  const [imageUrl, setImageUrl] = useState<string>('');

  useEffect(() => {
    const loadImage = async () => {
      const token = localStorage.getItem('token');
      const url = `${process.env.REACT_APP_API_URL}/photos/${photoId}/file?size=${size}`;
      try {
        const response = await fetch(url, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
          const blob = await response.blob();
          const blobUrl = URL.createObjectURL(blob);
          setImageUrl(blobUrl);
        } else {
          console.error('Ошибка загрузки фото:', response.status);
        }
      } catch (error) {
        console.error('Ошибка:', error);
      }
    };
    loadImage();
    return () => {
      if (imageUrl) URL.revokeObjectURL(imageUrl);
    };
  }, [photoId, size]);

  if (!imageUrl) return <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Spin /></div>;
  return <img src={imageUrl} alt="Фото" style={{ width: '100%', height: '100%', objectFit: 'cover' }} onClick={onClick} />;
};

const AlbumPage: React.FC = () => {
  const { albumId } = useParams<{ albumId: string }>();
  const navigate = useNavigate();
  const { user, currentFamily} = useAuth();
  
  const [album, setAlbum] = useState<Album | null>(null);
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [previewVisible, setPreviewVisible] = useState(false);
  const [previewTitle, setPreviewTitle] = useState('');
  const [previewImageBlob, setPreviewImageBlob] = useState<string>('');
  const [uploadDescription, setUploadDescription] = useState('');
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isMembersModalOpen, setIsMembersModalOpen] = useState(false);
  const [availableUsers, setAvailableUsers] = useState<any[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [isLoadingMembers, setIsLoadingMembers] = useState(false);
  const [admins, setAdmins] = useState<AlbumMember[]>([]);
  const [viewers, setViewers] = useState<AlbumMember[]>([]);
  const [familyMembers, setFamilyMembers] = useState<any[]>([]);
  const [isAddMemberModalOpen, setIsAddMemberModalOpen] = useState(false);
  const [availableMembers, setAvailableMembers] = useState<any[]>([]);
  const [selectedMemberId, setSelectedMemberId] = useState<number | null>(null);
  const [isAddingMember, setIsAddingMember] = useState(false);
  const [isAlbumAdmin, setIsAlbumAdmin] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editForm] = Form.useForm();
  const [isEditing, setIsEditing] = useState(false);
  const [editingPhotoId, setEditingPhotoId] = useState<number | null>(null);
  const [editingDescription, setEditingDescription] = useState('');

useEffect(() => {
    if (albumId) {
        loadAlbumData();
        loadFamilyMembers();
    }
    }, [albumId]);

  const loadFamilyMembers = async () => {
    if (!currentFamily) return;
    try {
        const response = await familyAPI.getFamilyMembers(currentFamily.id);
        setFamilyMembers(response.data);
    } catch (error) {
        console.error('Ошибка загрузки членов семьи:', error);
    }
  };
  
  const getUserName = (userId: number) => {
    const member = familyMembers.find(m => m.user_id === userId);
    if (member) {
        return `${member.first_name} ${member.last_name}`.trim();
    }
    return `Пользователь ${userId}`;
  };

 const loadAlbumData = async () => {
  if (!albumId) return;
  setIsLoading(true);
  try {
    const [albumResponse, photosResponse, adminsResponse] = await Promise.all([
      albumAPI.getById(Number(albumId)),
      photoAPI.getByAlbum(Number(albumId)),
      albumAPI.getAdmins(Number(albumId)), 
    ]);
    setAlbum(albumResponse.data);
    const photosData = photosResponse.data.photos || [];
    setPhotos(photosData);
    const isAdmin = adminsResponse.data.some(
      (admin: any) => admin.user_id === user?.id
    );
    setIsAlbumAdmin(isAdmin);
    
  } catch (error) {
    console.error('Ошибка загрузки альбома:', error);
    message.error('Не удалось загрузить альбом');
  } finally {
    setIsLoading(false);
  }
};


  

  const handleDeletePhoto = async (photoId: number) => {
    try {
      await photoAPI.delete(photoId);
      message.success('Фото удалено');
      loadAlbumData();
    } catch (error) {
      console.error('Ошибка удаления:', error);
      message.error('Не удалось удалить фото');
    }
  };

  const handleDeleteAlbum = async () => {
    if (!albumId) return;
    try {
      await albumAPI.delete(Number(albumId));
      message.success('Альбом удален');
      navigate('/gallery');
    } catch (error) {
      console.error('Ошибка удаления альбома:', error);
      message.error('Не удалось удалить альбом');
    }
  };

  const formatExpiration = (hoursUntilDeletion: number) => {
    if (hoursUntilDeletion <= 0) return 'Истекает сегодня';
    const days = Math.ceil(hoursUntilDeletion / 24);
    if (days === 1) return 'Истекает через 1 день';
    return `Истекает через ${days} дней`;
  };

  const handlePreview = async (photoId: number) => {
    const token = localStorage.getItem('token');
    const url = `${process.env.REACT_APP_API_URL}/photos/${photoId}/file?size=large`;
    try {
      const response = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!response.ok) throw new Error(`Ошибка ${response.status}`);
      const blob = await response.blob();
      const imageUrl = URL.createObjectURL(blob);
      setPreviewImageBlob(imageUrl);
      setPreviewTitle(`Фото ${photoId}`);
      setPreviewVisible(true);
    } catch (error) {
      console.error('Ошибка загрузки фото:', error);
      message.error('Не удалось загрузить фото');
    }
  };

  const handleUploadWithDescription = async () => {
    if (!albumId || !selectedFile) return;
    
    setIsUploading(true);
    setUploadProgress(0);
    
    const interval = setInterval(() => setUploadProgress(prev => Math.min(prev + 10, 90)), 200);
    
    try {
        await photoAPI.upload(Number(albumId), selectedFile, uploadDescription);
        clearInterval(interval);
        setUploadProgress(100);
        message.success('Фото загружено!');
        loadAlbumData();
        setIsUploadModalOpen(false);
        setSelectedFile(null);
        setUploadDescription('');
    } catch (error: any) {
        message.error(error.response?.data?.detail || 'Не удалось загрузить фото');
    } finally {
        clearInterval(interval);
        setIsUploading(false);
        setUploadProgress(0);
    }
  };

  const loadMembers = async () => {
    if (!albumId) return;
    setIsLoadingMembers(true);
    try {
        
        const [adminsResponse, viewersResponse] = await Promise.all([
        albumAPI.getAdmins(Number(albumId)),
        albumAPI.getViewers(Number(albumId)),
        ]);
        setAdmins(adminsResponse.data);
        const adminIds = new Set(adminsResponse.data.map((a: any) => a.user_id));
        const nonAdmins = viewersResponse.data.filter((v: any) => !adminIds.has(v.user_id));
        setViewers(nonAdmins);
        console.log('Админы:', adminsResponse.data);
        console.log('Участники:', viewersResponse.data);
    } catch (error) {
        console.error('Ошибка загрузки участников:', error);
        message.error('Не удалось загрузить участников');
    } finally {
        setIsLoadingMembers(false);
    }
  };

  //функция для загрузки доступных участников 
  const loadAvailableMembers = async () => {
    if (!currentFamily || !albumId) return;
    try {
        const familyMembersRes = await familyAPI.getFamilyMembers(currentFamily.id);
        const viewersRes = await albumAPI.getViewers(Number(albumId));
        
        const existingUserIds = new Set(viewersRes.data.map((v: any) => v.user_id));
        const available = familyMembersRes.data.filter(
        (member: any) => !existingUserIds.has(member.user_id) && member.user_id
        );
        setAvailableMembers(available);
    } catch (error) {
        console.error('Ошибка загрузки доступных участников:', error);
        message.error('Не удалось загрузить список участников');
    }
  };

  //функция добавления участника
  const handleAddMember = async () => {
    if (!albumId || !selectedMemberId) return;
    setIsAddingMember(true);
    try {
        await albumAPI.addMember(Number(albumId), selectedMemberId);
        message.success('Участник добавлен в альбом');
        loadMembers(); 
        setIsAddMemberModalOpen(false);
        setSelectedMemberId(null);
    } catch (error: any) {
        message.error(error.response?.data?.detail || 'Не удалось добавить участника');
    } finally {
        setIsAddingMember(false);
    }
  };

  //открыть модальное окно управления
  const handleOpenMembersModal = async () => {
    await loadMembers();
    setIsMembersModalOpen(true);
  };


  //назначить администратора
  const handleMakeAdmin = async (userId: number) => {
    if (!albumId) return;
    try {
        await albumAPI.addAdmin(Number(albumId), userId);
        message.success('Права админа назначены');
        loadMembers();
    } catch (error: any) {
        message.error(error.response?.data?.detail || 'Не удалось назначить админа');
    }
  };

  //снять права администратора
  const handleRemoveAdmin = async (userId: number) => {
    if (!albumId) return;
    try {
        await albumAPI.removeAdmin(Number(albumId), userId);
        message.success('Права админа сняты');
        loadMembers();
    } catch (error: any) {
        message.error(error.response?.data?.detail || 'Не удалось снять права');
    }
  };

  //удалить участника
  const handleRemoveMember = async (userId: number, isSelf: boolean = false) => {
    if (!albumId) return;
    
    Modal.confirm({
        title: isSelf ? 'Покинуть альбом' : 'Удалить участника',
        content: isSelf 
        ? 'Вы уверены, что хотите покинуть этот альбом?' 
        : 'Удалить этого участника из альбома?',
        onOk: async () => {
        try {
            await albumAPI.removeMember(Number(albumId), userId);
            message.success(isSelf ? 'Вы покинули альбом' : 'Участник удален');
            loadMembers();
        } catch (error: any) {
            message.error(error.response?.data?.detail || 'Не удалось удалить участника');
        }
        },
    });
  };

  const handleUpdateAlbum = async (values: { title: string; description?: string }) => {
    if (!albumId) return;
        setIsEditing(true);
    try {
        await albumAPI.update(Number(albumId), {
        title: values.title,
        description: values.description,
        });
        message.success('Альбом обновлен');
        setIsEditModalOpen(false);
        loadAlbumData(); 
    } catch (error: any) {
        message.error(error.response?.data?.detail || 'Не удалось обновить альбом');
    } finally {
        setIsEditing(false);
    }
  };

  // Функция для проверки, может ли пользователь редактировать/удалять фото
  const canModifyPhoto = (photo: Photo) => {
    return isAlbumAdmin || photo.uploaded_by_user_id === Number(user?.id);
  };

  const handleUpdateDescription = async (photoId: number) => {
    if (!editingDescription && editingDescription !== '') {
    }
    try {
        await photoAPI.update(photoId, editingDescription);
        message.success('Описание обновлено');
        loadAlbumData(); // Обновляем список фото
        setEditingPhotoId(null);
    } catch (error: any) {
        message.error(error.response?.data?.detail || 'Не удалось обновить описание');
    }
  };

  if (isLoading) return <div style={{ textAlign: 'center', padding: 50 }}><Spin size="large" /></div>;
  if (!album) return <div style={{ padding: 20 }}><Title level={4}>Альбом не найден</Title><Button onClick={() => navigate('/gallery')}>Вернуться</Button></div>;

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 24 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/gallery')}>Назад в галерею</Button>
        <Popconfirm title="Удалить альбом" description="Все фото будут удалены без возможности восстановления" onConfirm={handleDeleteAlbum} okText="Да" cancelText="Отмена" okButtonProps={{ danger: true }}>
        {isAlbumAdmin && (
            <Button danger icon={<DeleteOutlined />}
            >Удалить альбом
          </Button>
        )}
          
        </Popconfirm>
        <Button 
            icon={<TeamOutlined />} 
            onClick={handleOpenMembersModal}
            >
            Участники
          </Button>
      </div>

      <Card style={{ marginBottom: 24, borderRadius: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center' }}>
            <Title level={2} style={{ margin: 0 }}>{album.title}</Title>
            {isAlbumAdmin && (
                <Button 
                type="text" 
                icon={<EditOutlined />} 
                onClick={() => {
                    editForm.setFieldsValue({
                    title: album.title,
                    description: album.description,
                    });
                    setIsEditModalOpen(true);
                }}
                style={{ marginLeft: 16 }}
                />
            )}
            </div>
        
        {album.description && <Paragraph type="secondary">{album.description}</Paragraph>}
        <Descriptions column={2} size="small" style={{ marginTop: 16 }}>
          <Descriptions.Item label="Фото">{album.photos_count} шт.</Descriptions.Item>
          <Descriptions.Item label="Срок хранения">
            <Tooltip title={formatExpiration(album.hours_until_deletion)}>
              <span style={{ color: album.hours_until_deletion <= 72 ? '#fa8c16' : 'inherit' }}>
                <ClockCircleOutlined /> {formatExpiration(album.hours_until_deletion)}
              </span>
            </Tooltip>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <div style={{ marginBottom: 24 }}>
        <Button 
            type="primary" 
            icon={<UploadOutlined />} 
            onClick={() => setIsUploadModalOpen(true)}
            style={{ background: '#7b68ee' }}
        >
            Загрузить фото
        </Button>
        </div>

      {photos.length === 0 ? (
        <Empty description="В этом альбоме пока нет фото. Загрузите первые фотографии!" style={{ padding: 50 }} />
      ) : (
        <Row gutter={[16, 16]}>
          {photos.map((photo) => (
            <Col xs={12} sm={8} md={6} lg={4} key={photo.id}>
              <Card
                hoverable
                cover={
                    <div style={{ height: 160, overflow: 'hidden', cursor: 'pointer' }}>
                    <PhotoImage photoId={photo.id} size="medium" onClick={() => handlePreview(photo.id)} />
                    </div>
                }
                actions={
                    canModifyPhoto(photo) ? [
                    <Popconfirm
                        title="Удалить фото"
                        description="Фото будет удалено без возможности восстановления"
                        onConfirm={() => handleDeletePhoto(photo.id)}
                        okText="Удалить"
                        cancelText="Отмена"
                        okButtonProps={{ danger: true }}
                    >
                        <DeleteOutlined key="delete" style={{ color: '#ff4d4f' }} />
                    </Popconfirm>
                    ] : []
                }
                bodyStyle={{ padding: 12 }}
                >
                {/* Описание фото с возможностью редактирования */}
                {canModifyPhoto(photo) ? (
                    editingPhotoId === photo.id ? (
                    <Input.TextArea
                        autoFocus
                        defaultValue={photo.description || ''}
                        onChange={(e) => setEditingDescription(e.target.value)}
                        onBlur={() => handleUpdateDescription(photo.id)}
                        onPressEnter={() => handleUpdateDescription(photo.id)}
                        style={{ fontSize: '12px' }}
                    />
                    ) : (
                    <Paragraph 
                        ellipsis={{ rows: 2 }} 
                        style={{ fontSize: '12px', margin: 0, color: '#666', cursor: 'pointer' }}
                        onClick={() => {
                        setEditingPhotoId(photo.id);
                        setEditingDescription(photo.description || '');
                        }}
                    >
                        {photo.description || 'Без описания (кликните для редактирования)'}
                    </Paragraph>
                    )
                ) : (
                    <Paragraph 
                    ellipsis={{ rows: 2 }} 
                    style={{ fontSize: '12px', margin: 0, color: '#666' }}
                    >
                    {photo.description || 'Без описания'}
                    </Paragraph>
                )}
                
                <Text type="secondary" style={{ fontSize: 10 }}>
                    {photo.uploaded_at ? new Date(photo.uploaded_at).toLocaleDateString('ru-RU') : 'Дата неизвестна'}
                </Text>
                </Card>
            </Col>
          ))}
        </Row>
      )}

      <Modal
        open={previewVisible}
        title={previewTitle}
        footer={null}
        onCancel={() => {
          setPreviewVisible(false);
          if (previewImageBlob) {
            URL.revokeObjectURL(previewImageBlob);
            setPreviewImageBlob('');
          }
        }}
        width="90%"
        style={{ top: 20 }}
      >
        {previewImageBlob ? <img alt="preview" style={{ width: '100%' }} src={previewImageBlob} /> : <Spin />}
      </Modal>

      <Modal
        title="Загрузить фото"
        open={isUploadModalOpen}
        onCancel={() => {
            setIsUploadModalOpen(false);
            setSelectedFile(null);
            setUploadDescription('');
        }}
        onOk={handleUploadWithDescription}
        okText="Загрузить"
        cancelText="Отмена"
        confirmLoading={isUploading}
        okButtonProps={{
            style: { backgroundColor: '#7b68ee' }
        }}
        >
        <Upload
            beforeUpload={(file) => {
            const isImage = file.type.startsWith('image/');
            if (!isImage) {
                message.error('Можно загружать только изображения!');
                return false;
            }
            const isLt20M = file.size / 1024 / 1024 < 20;
            if (!isLt20M) {
                message.error('Изображение должно быть меньше 20MB!');
                return false;
            }
            setSelectedFile(file);
            return false;
            }}
            showUploadList={false}
            maxCount={1}
        >
            <Button icon={<UploadOutlined />}>Выбрать файл</Button>
        </Upload>
        {selectedFile && (
            <div style={{ marginTop: 16 }}>
            <Text strong>Выбранный файл:</Text> {selectedFile.name}
            </div>
        )}
        <Input.TextArea
            placeholder="Описание фото (необязательно)"
            value={uploadDescription}
            onChange={(e) => setUploadDescription(e.target.value)}
            style={{ marginTop: 16 }}
            rows={3}
        />
        </Modal>

        {/*Модальное окно управления участниками*/}
        <Modal
            title={
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Участники альбома</span>
            {isAlbumAdmin && (
                <Button 
                    type="primary" 
                    size="small" 
                    icon={<UserAddOutlined />}
                    style={{ 
                        backgroundColor: '#7b68ee', 
                        borderColor: '#7b68ee' ,
                        margin: '15px',   
                    }}
                    onClick={() => {
                    loadAvailableMembers();
                    setIsAddMemberModalOpen(true);
                    }}
                >
                    Добавить
                </Button>
            )}
            
            </div>
        }
            open={isMembersModalOpen}
            onCancel={() => setIsMembersModalOpen(false)}
            footer={null}
            width={500}
            >
            <Tabs
                items={[
                {
                    key: 'admins',
                    label: `Админы (${admins.length})`,
                    children: (
                    <List
                        dataSource={admins}
                        renderItem={(admin) => (
                        <List.Item
                          
                            actions={isAlbumAdmin && admin.user_id !== Number(user?.id) ? [
                            <Button 
                                size="small" 
                                danger 
                                onClick={() => handleRemoveAdmin(admin.user_id)}
                            >
                                Снять права админа
                            </Button>
                            ] : []}
                        >
                            <List.Item.Meta
                            avatar={<CrownOutlined style={{ color: '#faad14' }} />}
                            title={getUserName(admin.user_id)}
                            description="Админ"
                            />
                        </List.Item>
                        )}
                    />
                    ),
                },
                {
                    key: 'members',
                    label: `Участники (${viewers.length})`,
                    children: (
                    <List
                        dataSource={viewers}
                        locale={{ emptyText: 'Пока что нет участников' }}
                        renderItem={(viewer) => (
                        <List.Item
                            actions={isAlbumAdmin ? [
                            <Button size="small" onClick={() => handleMakeAdmin(viewer.user_id)}>
                                Назначить админом
                            </Button>,
                            <Button size="small" danger onClick={() => handleRemoveMember(viewer.user_id)}>
                                Удалить
                            </Button>,
                            ] : (
                            viewer.user_id === Number(user?.id) ? [
                                <Button size="small" danger onClick={() => handleRemoveMember(viewer.user_id, true)}>
                                Покинуть альбом
                                </Button>
                            ] : []
                            )}
                        >
                            <List.Item.Meta
                            avatar={<UserOutlined />}
                            title={getUserName(viewer.user_id)}
                            description="Участник"
                            />
                        </List.Item>
                        )}
                    />
                    ),
                },
                ]}
            />
        </Modal>

        {/*модальное окно выбора участника*/}
        <Modal
            title="Добавить участника"
            open={isAddMemberModalOpen}
            onCancel={() => {
                setIsAddMemberModalOpen(false);
                setSelectedMemberId(null);
            }}
            onOk={handleAddMember}
            confirmLoading={isAddingMember}
            okText="Добавить"
            cancelText="Отмена"
            okButtonProps={{
                style: { 
                backgroundColor: '#7b68ee', 
                borderColor: '#7b68ee',
                }
            }}
            >
            <Select
                placeholder="Выберите участника"
                style={{ width: '100%' }}
                onChange={(value) => setSelectedMemberId(value)}
                options={availableMembers.map((member) => ({
                value: member.user_id,
                label: `${member.first_name} ${member.last_name}`,
                }))}
            />
        </Modal>

        <Modal
            title="Редактировать альбом"
            open={isEditModalOpen}
            onCancel={() => setIsEditModalOpen(false)}
            footer={null}
            >
            <Form
                form={editForm}
                layout="vertical"
                onFinish={handleUpdateAlbum}
                initialValues={{ title: album?.title, description: album?.description }}
            >
                <Form.Item
                name="title"
                label="Название альбома"
                rules={[{ required: true, message: 'Введите название альбома' }]}
                >
                <Input placeholder="Название альбома" />
                </Form.Item>
                
                <Form.Item
                name="description"
                label="Описание"
                >
                <Input.TextArea rows={3} placeholder="Описание альбома (необязательно)" />
                </Form.Item>
                
                <Form.Item>
                <Button type="primary" htmlType="submit" loading={isEditing} block
                    style={{ 
                        backgroundColor: '#7b68ee', 
                        borderColor: '#7b68ee' ,   
                    }}
                >
                    Сохранить изменения
                </Button>
                </Form.Item>
            </Form>
        </Modal>
    </div>
  );
};

export default AlbumPage;