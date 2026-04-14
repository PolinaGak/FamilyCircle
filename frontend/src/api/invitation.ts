import { apiClient } from './client';

export interface Invitation {
  id: number;
  code: string;
  family_id: number;
  invitation_type: 'new_member' | 'claim_member';
  target_member_id: number | null;
  expires_at: string;
  used_at: string | null;
  used_by_user_id: number | null;
  is_active: boolean;
  created_at: string;
}

export interface ClaimInvitationResponse {
  success: boolean;
  message: string;
  family_id: number;
  family_name: string;
  member_id: number;
  requires_profile_completion: boolean;
}

export const invitationAPI = {
  //Создать приглашение для существующего пользователя
  createClaimMemberInvitation: (familyId: number, memberId: number, expiresInDays: number = 7) =>
    apiClient.post<Invitation>('/invitation/create/claim-member', {
      family_id: familyId,
      expires_in_days: expiresInDays,
      member_id: memberId,
      invitation_type: 'claim_member',
    }),
  
  //Активировать приглашение
  claimInvitation: (code: string) =>
    apiClient.post<ClaimInvitationResponse>('/invitation/claim', { code }),
  
  // Получить все приглашения семьи
  getFamilyInvitations: (familyId: number) =>
    apiClient.get<Invitation[]>(`/invitation/family/${familyId}`),
  
  // Отозвать приглашение
  deactivateInvitation: (invitationId: number) =>
    apiClient.delete(`/invitation/${invitationId}`),
};