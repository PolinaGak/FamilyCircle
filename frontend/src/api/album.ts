import { apiClient } from './client';

export interface Album {
  id: number;
  title: string;
  description: string;
  family_id: number;
  created_by_user_id: number;
  event_id: number | null;
  created_at: string;
  expires_at: string;
  is_deleted: boolean;
  hours_until_deletion: number;
  photos_count: number;
  members_count: number;
}

export interface CreateAlbumData {
  title: string;
  description?: string;
  family_id: number;
  event_id?: number;
}

export interface AlbumsResponse {
  albums: Album[];
  total: number;
}

export interface AlbumMember {
  album_id: number;
  user_id: number;
  can_edit: boolean;
  can_delete: boolean;
  status: string;
  added_by_user_id: number;
  added_at: string;
  user?: {
    id: number;
    name: string;
    email: string;
  };
}

export const albumAPI = {
  create: (data: CreateAlbumData) =>
    apiClient.post<Album>('/albums', data),

  getByFamily: (familyId: number) =>
    apiClient.get<AlbumsResponse>(`/albums?family_id=${familyId}`),

  getById: (albumId: number) =>
    apiClient.get<Album>(`/albums/${albumId}`),

  update: (albumId: number, data: { title?: string; description?: string }) =>
    apiClient.put<Album>(`/albums/${albumId}`, data),

  delete: (albumId: number) =>
    apiClient.delete(`/albums/${albumId}`),

  getViewers: (albumId: number) =>
    apiClient.get<AlbumMember[]>(`/albums/${albumId}/viewers`),

  getAdmins: (albumId: number) =>
    apiClient.get<AlbumMember[]>(`/albums/${albumId}/admins`),

  addMember: (albumId: number, userId: number) =>
    apiClient.post(`/albums/${albumId}/members`, { user_id: userId }),

  removeMember: (albumId: number, userId: number) =>
    apiClient.delete(`/albums/${albumId}/members/${userId}`),

  addAdmin: (albumId: number, userId: number) =>
    apiClient.post(`/albums/${albumId}/admins`, { user_id: userId }),

  removeAdmin: (albumId: number, userId: number) =>
    apiClient.delete(`/albums/${albumId}/admins/${userId}`),

  
};