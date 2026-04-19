import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Card, Row, Col, Button, Spin, Empty, Typography, 
  message, Modal, Upload, Popconfirm, Tooltip, Descriptions, Input
} from 'antd';
import { 
  ArrowLeftOutlined, UploadOutlined, DeleteOutlined, 
  ClockCircleOutlined 
} from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext';
import { albumAPI, Album } from '../api/album';
import { photoAPI, Photo } from '../api/photo';

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
  const { user } = useAuth();
  
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
  
  useEffect(() => {
    if (albumId) loadAlbumData();
  }, [albumId]);

  const loadAlbumData = async () => {
    if (!albumId) return;
    setIsLoading(true);
    try {
      const [albumResponse, photosResponse] = await Promise.all([
        albumAPI.getById(Number(albumId)),
        photoAPI.getByAlbum(Number(albumId)),
      ]);
      setAlbum(albumResponse.data);
      const photosData = photosResponse.data.photos || [];
      setPhotos(photosData);
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

  if (isLoading) return <div style={{ textAlign: 'center', padding: 50 }}><Spin size="large" /></div>;
  if (!album) return <div style={{ padding: 20 }}><Title level={4}>Альбом не найден</Title><Button onClick={() => navigate('/gallery')}>Вернуться</Button></div>;

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 24 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/gallery')}>Назад в галерею</Button>
        <Popconfirm title="Удалить альбом" description="Все фото будут удалены без возможности восстановления" onConfirm={handleDeleteAlbum} okText="Да" cancelText="Отмена" okButtonProps={{ danger: true }}>
          <Button danger icon={<DeleteOutlined />}>Удалить альбом</Button>
        </Popconfirm>
      </div>

      <Card style={{ marginBottom: 24, borderRadius: 12 }}>
        <Title level={2}>{album.title}</Title>
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
                actions={[
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
                ]}
                bodyStyle={{ padding: 12 }}
              >
                <Paragraph ellipsis={{ rows: 2 }} style={{ fontSize: 12, margin: 0, color: '#666' }}>
                  {photo.description || 'Без описания'}
                </Paragraph>
                <Text type="secondary" style={{ fontSize: 10 }}>
                  {photo.uploaded_at ? new Date(photo.uploaded_at).toLocaleDateString() : 'Дата неизвестна'}
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
    </div>
  );
};

export default AlbumPage;