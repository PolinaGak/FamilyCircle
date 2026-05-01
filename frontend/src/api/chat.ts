import { apiClient } from './client';

export interface ChatMember {
  id: number;
  chat_id: number;
  user_id: number;
  is_admin: boolean;
  joined_at: string;
  user_name?: string;
  user?: {
    id: number;
    name: string;
    email: string;
  };
}

export interface Chat {
  id: number;
  title: string;
  family_id: number;
  event_id?: number | null;
  created_by_user_id: number;
  created_at: string;
  members_count: number;
  is_admin?: boolean;
}

export interface ChatDetail extends Chat {
  members: ChatMember[];
}

export interface ChatCreate {
  name: string;
  family_id: number;
  event_id?: number;
  member_ids?: number[];
}

export interface ChatUpdate {
  name?: string;
}

export const chatAPI = {
  // Создать чат
  create: (data: ChatCreate) =>
  apiClient.post<Chat>('/chats', {
    title: data.name,  
    family_id: data.family_id,
    event_id: data.event_id,
    member_ids: data.member_ids,
  }),

  // Получить список чатов (с фильтром по семье)
  list: (familyId?: number) => {
    const params = familyId ? `?family_id=${familyId}` : '';
    return apiClient.get<{ chats: Chat[]; total: number }>(`/chats${params}`);
  },

  // Получить детали чата
  getById: (chatId: number) =>
    apiClient.get<ChatDetail>(`/chats/${chatId}`),

  // Обновить чат (только админ)
  update: (chatId: number, data: ChatUpdate) =>
    apiClient.put<Chat>(`/chats/${chatId}`, data),

  // Удалить чат (только админ)
  delete: (chatId: number) =>
    apiClient.delete(`/chats/${chatId}`),

  // Покинуть чат
  leave: (chatId: number) =>
    apiClient.post(`/chats/${chatId}/leave`),

  // Получить список участников чата
  getMembers: (chatId: number) =>
    apiClient.get<ChatMember[]>(`/chats/${chatId}/members`),

  // Добавить участника
  addMember: (chatId: number, userId: number) =>
    apiClient.post<ChatMember>(`/chats/${chatId}/members`, { user_id: userId }),

  // Удалить участника (только админ)
  removeMember: (chatId: number, userId: number) =>
    apiClient.delete(`/chats/${chatId}/members/${userId}`),

  // Назначить администратора
  addAdmin: (chatId: number, userId: number) =>
    apiClient.post<ChatMember>(`/chats/${chatId}/admins`, { user_id: userId }),

  // Снять права администратора
  removeAdmin: (chatId: number, userId: number) =>
    apiClient.delete(`/chats/${chatId}/admins/${userId}`),

  // Передать права администратора
  transferAdmin: (chatId: number, newAdminUserId: number) =>
    apiClient.post(`/chats/${chatId}/transfer-admin`, { new_admin_user_id: newAdminUserId }),
};