import { apiClient } from './client';

export interface Photo {
  id: number;
  album_id: number;
  user_id: number;
  description: string | null;
  file_size: number;
  file_type: string;
  uploaded_at: string;
}

export interface PhotosResponse {
  photos: Photo[];
  total: number;
}

export const photoAPI = {
  upload: (albumId: number, file: File, description?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    if (description) {
      formData.append('description', description);
    }
    return apiClient.post<Photo>(`/albums/${albumId}/photos`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  getByAlbum: (albumId: number) =>
    apiClient.get<PhotosResponse>(`/albums/${albumId}/photos`),

  getById: (photoId: number) =>
    apiClient.get<Photo>(`/photos/${photoId}`),

  getFileUrl: (photoId: number, size: 'small' | 'medium' | 'large' | 'original' = 'medium') =>
    `${process.env.REACT_APP_API_URL}/photos/${photoId}/file?size=${size}`,

  update: (photoId: number, description: string) =>
    apiClient.put<Photo>(`/photos/${photoId}`, { description }),

  delete: (photoId: number) =>
    apiClient.delete(`/photos/${photoId}`),
};