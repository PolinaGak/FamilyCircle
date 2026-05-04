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
  first_name: string;
  last_name: string;
  patronymic: string | null;
  gender: 'male' | 'female';
  birth_date: string;
  death_date: string | null;
  phone: string | null;
  workplace: string | null;
  residence: string | null;
  is_admin: boolean;
  is_active: boolean;
  approved: boolean;
  created_by_user_id: number;
  created_at: string;
  
}

export interface CreateMemberData {
  first_name: string;
  last_name: string;
  patronymic?: string;
  birth_date: string;
  gender: "male" | "female";
  phone?: string;
  death_date?: string;
  workplace?: string;
  residence?: string;
  is_admin?: boolean;
  user_id?: number;
  related_member_id?: number;      
  relationship_type?: string;       
}

export interface RelativesGroup {
  parents: Array<{
    id: number;
    first_name: string;
    last_name: string;
    patronymic?: string;
    gender?: string;
    relationship_type: string;
  }>;
  children: Array<{
    id: number;
    first_name: string;
    last_name: string;
    patronymic?: string;
    gender?: string;
  }>;
  spouses: Array<{
    id: number;
    first_name: string;
    last_name: string;
  }>;
  siblings: Array<{
    id: number;
    first_name: string;
    last_name: string;
  }>;
}

export const familyAPI = {
  //Создать семью
  create: (name: string) =>
    apiClient.post<Family>('/family/create', { name }),
  
  //Получить все семьи пользователя
  getMyFamilies: () =>
    apiClient.get<Family[]>('/family/my'),
  
  //Получить детали семьи
  getFamilyDetail: (familyId: number) =>
    apiClient.get<Family>(`/family/${familyId}`),
  
  //Получить всех членов семьи
  getFamilyMembers: (familyId: number) =>
    apiClient.get<FamilyMember[]>(`/family/${familyId}/members`),

  //Создать карточку родственника
  createMember: (familyId: number, data: CreateMemberData) => {
    return apiClient.post(`/family/${familyId}/member`, data);
  },

  removeMember: (memberId: number) =>
  apiClient.delete(`/family/member/${memberId}`),

  approveMember: (memberId: number, approved: boolean) =>
  apiClient.post(`/family/member/${memberId}/approve`, { approved }),

  leaveFamily: (familyId: number) => 
    apiClient.post(`/family/${familyId}/leave`),

  deleteFamily: (familyId: number) =>
  apiClient.delete(`/family/${familyId}`),

  transferAdmin: (familyId: number, targetMemberId: number) =>
  apiClient.post(`/family/${familyId}/transfer-admin?target_member_id=${targetMemberId}`),

  updateFamily: (familyId: number, name: string) =>
  apiClient.put<Family>(`/family/${familyId}`, { name }),

  updateMember: (memberId: number, data: {
  first_name: string;
  last_name: string;
  patronymic?: string;
  gender: 'male' | 'female';
  birth_date: string;
  death_date?: string;
  phone?: string;
  workplace?: string;
  residence?: string;
  is_active?: boolean;
}) => apiClient.put(`/family/member/${memberId}`, data),

 getMemberRelatives: (familyId: number, memberId: number) => {
  return apiClient.get(`/family/${familyId}/tree/member/${memberId}/relatives`);
}

}
