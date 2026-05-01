import { apiClient } from './client';

export interface Message {
  id: number;
  chat_id: number;
  sender_user_id: number;
  sender_name?: string;
  content: string;
  sent_at: string;
  updated_at?: string;
  is_edited?: boolean;
  is_deleted?: boolean;
}

export interface MessageCreate {
  content: string;
}

export interface MessageUpdate {
  content: string;
}

export const messageAPI = {
  // Отправить сообщение
  send: (chatId: number, content: string) =>
    apiClient.post<Message>(`/chats/${chatId}/messages`, { content }),

  // Получить сообщения чата 
  getMessages: (chatId: number, limit: number = 50, offset: number = 0) =>
    apiClient.get<{ messages: Message[]; total: number; chat_id: number }>(
      `/chats/${chatId}/messages?limit=${limit}&offset=${offset}`
    ),

  // Редактировать сообщение 
  update: (chatId: number, messageId: number, content: string) =>
    apiClient.put<Message>(`/chats/${chatId}/messages/${messageId}`, { content }),

  // Удалить сообщение
  delete: (chatId: number, messageId: number) =>
    apiClient.delete(`/chats/${chatId}/messages/${messageId}`),
};