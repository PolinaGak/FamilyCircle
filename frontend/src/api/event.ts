import { apiClient } from './client';
export interface EventParticipant {
  id: number;
  event_id: number;
  user_id: number;
  status: 'invited' | 'accepted' | 'declined';
  invited_at: string;
  responded_at?: string;
  user?: {
    id: number;
    name: string;
    email: string;
  };
}

export interface CalendarEvent {
  id: number;
  title: string;
  description?: string;
  family_id: number;
  created_by_user_id: number;
  start_datetime: string;
  end_datetime: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface EventDetail extends CalendarEvent {
  participants: EventParticipant[];
  chat_id?: number;
  chat_exists: boolean;
  is_admin: boolean;
}

export interface CreateEventData {
  title: string;
  description?: string;
  family_id: number;
  start_datetime: string;
  end_datetime: string;
  create_chat?: boolean;
  invite_members?: number[];
}

export interface UpdateEventData {
  title?: string;
  description?: string;
  start_datetime?: string;
  end_datetime?: string;
}

export interface PendingInvitation {
  event_id: number;
  event_title: string;
  start_datetime: string;
  end_datetime: string;
  invited_at: string;
  family_name: string;
}

export interface EventListResponse {
  events: CalendarEvent[];
  total: number;
}


export const eventAPI = {
  
  getCalendarEvents: (familyId?: number) => {
    const params = familyId ? `?family_id=${familyId}` : '';
    return apiClient.get<CalendarEvent[]>(`/events/my/calendar${params}`);
  },

  
  getFamilyEvents: (familyId: number, includePast: boolean = false) => {
    return apiClient.get<EventListResponse>(`/events/family/${familyId}?include_past=${includePast}`);
  },

  
  getById: (eventId: number) =>
    apiClient.get<EventDetail>(`/events/${eventId}`),

  
  create: (data: CreateEventData) =>
    apiClient.post<CalendarEvent>('/events', data),

  
  update: (eventId: number, data: UpdateEventData) =>
    apiClient.put<CalendarEvent>(`/events/${eventId}`, data),

  
  delete: (eventId: number, permanent: boolean = false) =>
    apiClient.delete(`/events/${eventId}?permanent=${permanent}`),

  
  inviteParticipant: (eventId: number, userId: number) =>
    apiClient.post(`/events/${eventId}/invite`, { user_id: userId }),

  
  respondToInvitation: (eventId: number, accept: boolean) =>
    apiClient.post(`/events/${eventId}/respond`, { accept }),

  
  getPendingInvitations: () =>
    apiClient.get<PendingInvitation[]>('/events/my/invitations/pending'),

  
  removeParticipant: (eventId: number, userId: number) =>
    apiClient.delete(`/events/${eventId}/participants/${userId}`),

  createChat: (eventId: number) =>
    apiClient.post<{ success: boolean; chat_id: number }>(`/events/${eventId}/create-chat`),
};

export default eventAPI;