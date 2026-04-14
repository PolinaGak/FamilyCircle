import React, { useState } from 'react';
import { familyAPI } from '../api/family';

interface CreateFamilyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const CreateFamilyModal: React.FC<CreateFamilyModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [familyName, setFamilyName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await familyAPI.create(familyName);
      onSuccess();
      onClose();
      setFamilyName('');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка создания семьи');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0,0,0,0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000
    }}>
      <div style={{
        background: 'white',
        padding: '24px',
        borderRadius: '12px',
        width: '400px',
        maxWidth: '90%'
      }}>
        <h2>Создать новую семью</h2>
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '8px' }}>Название семьи</label>
            <input
              type="text"
              value={familyName}
              onChange={(e) => setFamilyName(e.target.value)}
              placeholder="Например: Ивановы"
              required
              disabled={isLoading}
              style={{
                width: '100%',
                padding: '8px',
                border: '1px solid #ddd',
                borderRadius: '4px'
              }}
            />
          </div>
          {error && <div style={{ color: 'red', marginBottom: '16px' }}>{error}</div>}
          <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
            <button type="button" onClick={onClose} disabled={isLoading} style={{ padding: '8px 16px' }}>
              Отмена
            </button>
            <button type="submit" disabled={isLoading} style={{ padding: '8px 16px', background: '#7b68ee', color: 'white', border: 'none', borderRadius: '4px' }}>
              {isLoading ? 'Создание...' : 'Создать'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreateFamilyModal;