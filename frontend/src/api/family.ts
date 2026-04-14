import { apiClient } from "./client";

export interface Family {
    id: number;
    name: string;
    admin_user_id: number;
    created_at: string;
}

export interface FamilyMember {
  id: number;
  family_id: number;
  user_id: number | null;
  is_admin: boolean;
  first_name: string;
  last_name: string;
  patronymic?: string;
  gender: string;
  birth_date: string;
  death_date?: string;
  phone?: string;
  workplace?: string;
  residence?: string;
  is_active: boolean;
  approved: boolean;
}

export interface CreateMemberData {
  first_name: string;
  last_name: string;
  patronymic?: string;
  birth_date: string;
  gender: "male" | "female";
  phone?: string;
  workplace?: string;
  residence?: string;
  is_admin?: boolean;
}

export const familyAPI = {
  //Создать семью
  create: (name: string) =>
    apiClient.post<Family>('/family/create', { name }),
  
  //Получить все семьи пользователя
  getMyFamilies: () =>
    apiClient.get<Family[]>('/family/my'),
  
  //Получить детали конкретной семьи
  getFamilyDetail: (familyId: number) =>
    apiClient.get<Family>(`/family/${familyId}`),
  
  //Получить всех членов семьи
  getFamilyMembers: (familyId: number) =>
    apiClient.get<FamilyMember[]>(`/family/${familyId}/members`),

  //Создать карточку родственника
  createMember: (familyId: number, data: CreateMemberData) =>
  apiClient.post<FamilyMember>(`/family/${familyId}/member`, {
    first_name: data.first_name,
    last_name: data.last_name,
    patronymic: data.patronymic,
    birth_date: data.birth_date,
    gender: data.gender,  
    phone: data.phone,
    workplace: data.workplace,
    residence: data.residence,
    is_admin: data.is_admin || false,
    related_member_id: 0,
  }),

  removeMember: (memberId: number) =>
  apiClient.delete(`/family/member/${memberId}`),
};