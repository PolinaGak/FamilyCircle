import { apiClient } from './client';

export interface TreeNode {
  id: number;
  first_name: string;
  last_name: string;
  patronymic: string | null;
  birth_date: string | null;
  death_date: string | null;
  gender: 'male' | 'female' | null;
  is_active: boolean;
  is_admin: boolean;
  generation: number;
  partners: number[];
  user_id: number | null;
}

export interface TreeEdge {
  from: number;
  to: number;
  type: string;
}

export interface FamilyUnit {
  id: string;
  parents: number[];
  children: number[];
  type: 'nuclear_family' | 'single_parent';
}

export interface TreeResponse {
  nodes: TreeNode[];
  edges: TreeEdge[];
  family_units: FamilyUnit[];
  root_id: number;
  family_id: number;
}

export interface RootInfo {
  id: number;
  name: string;
  birth_date: string | null;
  is_admin: boolean;
}

export interface SearchResult {
  id: number;
  first_name: string;
  last_name: string;
  patronymic: string | null;
  birth_date: string | null;
  death_date: string | null;
  gender: 'male' | 'female' | null;
  is_active: boolean;
  user_id: number | null;
}

export interface RelativesGroup {
  parents: RelativeInfo[];
  children: RelativeInfo[];
  spouses: RelativeInfo[];
  siblings: RelativeInfo[];
}

export interface RelativeInfo {
  id: number;
  first_name: string;
  last_name: string;
  patronymic: string | null;
  gender?: 'male' | 'female' | null;
  relationship_type?: string;
}

export interface SubtreeResponse {
  nodes: TreeNode[];
  edges: TreeEdge[];
  center_id: number;
}

export const treeAPI = {
  /**
   * Получить полное семейное древо
   * @param familyId - ID семьи
   * @param rootMemberId - ID корневого члена 
   * @param includeInactive - показывать неактивных
   * @param maxDepth - глубина дерева 
   */
  getTree: (familyId: number, rootMemberId?: number, includeInactive: boolean = false, maxDepth: number = 10) => {
    const params = new URLSearchParams();
    if (rootMemberId) params.append('root_member_id', String(rootMemberId));
    params.append('include_inactive', String(includeInactive));
    params.append('max_depth', String(maxDepth));
    
    return apiClient.get<TreeResponse>(`/family/${familyId}/tree?${params.toString()}`);
  },

  
   
  getRoots: (familyId: number) =>
    apiClient.get<RootInfo[]>(`/family/${familyId}/tree/roots`),

  /**
   * Поиск по семейному древу
   * @param familyId - ID семьи
   * @param query - поисковый запрос
   * @param searchInactive - искать среди неактивных
   * @param birthDateFrom - дата рождения от
   * @param birthDateTo - дата рождения до
   */
  search: (
    familyId: number,
    query?: string,
    searchInactive: boolean = false,
    birthDateFrom?: string,
    birthDateTo?: string
  ) => {
    const params = new URLSearchParams();
    if (query) params.append('query', query);
    params.append('search_inactive', String(searchInactive));
    if (birthDateFrom) params.append('birth_date_from', birthDateFrom);
    if (birthDateTo) params.append('birth_date_to', birthDateTo);
    
    return apiClient.get<SearchResult[]>(`/family/${familyId}/tree/search?${params.toString()}`);
  },

  getSubtree: (familyId: number, memberId: number, direction: 'up' | 'down' | 'both' = 'both', generations: number = 3) =>
    apiClient.get<SubtreeResponse>(
      `/family/${familyId}/tree/member/${memberId}/subtree?direction=${direction}&generations=${generations}`
    ),

  getRelatives: (familyId: number, memberId: number) =>
    apiClient.get<RelativesGroup>(`/family/${familyId}/tree/member/${memberId}/relatives`),


  deleteRelationship: (familyId: number, relationshipId: number) =>
    apiClient.delete(`/family/${familyId}/tree/relationship/${relationshipId}`),
};

export default treeAPI;