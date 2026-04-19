import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Row, Col, Button, Spin, Empty, Typography, message, Modal, Form, Input, Select, Tag, Tooltip } from 'antd';
import { PlusOutlined, PictureOutlined, ClockCircleOutlined, SwapOutlined } from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext';
import { albumAPI, Album } from '../api/album';

const { Title, Text, Paragraph } = Typography;

const GalleryPage: React.FC = () => {
  const { families, currentFamily, setCurrentFamily, user } = useAuth();
  const navigate = useNavigate();
  const [albums, setAlbums] = useState<Album[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [form] = Form.useForm();
  const [isCreating, setIsCreating] = useState(false);
  const [selectedFamilyId, setSelectedFamilyId] = useState<number>(currentFamily?.id || 0);

  useEffect(() => {
    if (selectedFamilyId) {
      loadAlbums(selectedFamilyId);
    }
  }, [selectedFamilyId]);

  useEffect(() => {
    if (currentFamily) {
      setSelectedFamilyId(currentFamily.id);
    }
  }, [currentFamily]);

  const loadAlbums = async (familyId: number) => {
    setIsLoading(true);
    try {
      const response = await albumAPI.getByFamily(familyId);
      const albumsData = response.data.albums || [];
      setAlbums(albumsData);
    } catch (error) {
      console.error('Ошибка загрузки альбомов:', error);
      message.error('Не удалось загрузить альбомы');
      setAlbums([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFamilyChange = (familyId: number) => {
    setSelectedFamilyId(familyId);
    const selectedFamily = families.find(f => f.id === familyId);
    if (selectedFamily && setCurrentFamily) {
      setCurrentFamily(selectedFamily);
    }
  };

  const handleCreateAlbum = async (values: any) => {
    if (!selectedFamilyId) return;
    
    setIsCreating(true);
    try {
      await albumAPI.create({
        title: values.title,
        description: values.description,
        family_id: selectedFamilyId,
      });
      message.success('Альбом создан!');
      form.resetFields();
      setIsModalOpen(false);
      loadAlbums(selectedFamilyId);
    } catch (error: any) {
      console.error('Ошибка создания альбома:', error);
      message.error(error.response?.data?.detail || 'Не удалось создать альбом');
    } finally {
      setIsCreating(false);
    }
  };

  const formatExpiration = (hoursUntilDeletion: number) => {
    if (hoursUntilDeletion <= 0) return 'Истекает сегодня';
    const days = Math.ceil(hoursUntilDeletion / 24);
    if (days === 1) return 'Истекает через 1 день';
    return `Истекает через ${days} дней`;
  };

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
      {/*Заголовок с выбором семьи*/}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <Title level={2} style={{ margin: 0 }}>Галерея</Title>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '8px' }}>
            <Text type="secondary">Семья:</Text>
            <Select
              value={selectedFamilyId}
              onChange={handleFamilyChange}
              style={{ width: 200 }}
              suffixIcon={<SwapOutlined />}
              options={families.map(family => ({
                value: family.id,
                label: family.name,
              }))}
            />
          </div>
        </div>
        <Button 
          type="primary" 
          icon={<PlusOutlined />} 
          onClick={() => setIsModalOpen(true)}
          style={{ background: '#7b68ee' }}
        >
          Создать альбом
        </Button>
      </div>

      {/*Список альбомов*/}
      {isLoading ? (
        <div style={{ textAlign: 'center', padding: '50px' }}>
          <Spin size="large" />
        </div>
      ) : albums.length === 0 ? (
        <Empty 
          description="В этой семье пока нет альбомов. Создайте первый альбом!"
          style={{ padding: '50px' }}
        />
      ) : (
        <Row gutter={[24, 24]}>
          {albums.map((album) => (
            <Col xs={24} sm={12} md={8} lg={6} key={album.id}>
              <Card
                hoverable
                onClick={() => navigate(`/album/${album.id}`)}
                cover={
                  <div style={{ 
                    height: 180, 
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}>
                    <PictureOutlined style={{ fontSize: 48, color: 'white', opacity: 0.8 }} />
                  </div>
                }
                style={{ borderRadius: '12px' }}
              >
                <Card.Meta
                  title={
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontWeight: 500 }}>{album.title}</span>
                      {album.hours_until_deletion <= 72 && album.hours_until_deletion > 0 && (
                        <Tag color="orange">Скоро истекает</Tag>
                      )}
                    </div>
                  }
                  description={
                    <div>
                      <Paragraph ellipsis={{ rows: 2 }} style={{ fontSize: '13px', color: '#666', marginBottom: '12px' }}>
                        {album.description || 'Нет описания'}
                      </Paragraph>
                      <div style={{ display: 'flex', gap: '16px', fontSize: '12px', color: '#999' }}>
                        <span>
                          <PictureOutlined style={{ marginRight: '4px' }} />
                          {album.photos_count} фото
                        </span>
                        <Tooltip title={formatExpiration(album.hours_until_deletion)}>
                          <span>
                            <ClockCircleOutlined style={{ marginRight: '4px' }} />
                            {album.hours_until_deletion > 0 ? formatExpiration(album.hours_until_deletion) : 'Скоро'}
                          </span>
                        </Tooltip>
                      </div>
                    </div>
                  }
                />
              </Card>
            </Col>
          ))}
        </Row>
      )}

      {/*Модальное окно создания альбома*/}
      <Modal
        title="Создать новый альбом"
        open={isModalOpen}
        onCancel={() => {
          setIsModalOpen(false);
          form.resetFields();
        }}
        footer={null}
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateAlbum}
        >
          <Form.Item
            name="title"
            label="Название альбома"
            rules={[{ required: true, message: 'Введите название альбома' }]}
          >
            <Input placeholder="Например: Лето 2024" size="large" />
          </Form.Item>

          <Form.Item
            name="description"
            label="Описание"
          >
            <Input.TextArea 
              rows={3} 
              placeholder="Небольшое описание альбома (необязательно)" 
            />
          </Form.Item>

          <Form.Item>
            <Button 
              type="primary" 
              htmlType="submit" 
              loading={isCreating}
              style={{ width: '100%', background: '#7b68ee' }}
            >
              Создать
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default GalleryPage;