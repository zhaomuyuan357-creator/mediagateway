/**
 * API client — 极简任务接口
 *
 * 入参仅 fileUrl + templateId，返回 task_id。
 * 通过 task_id 轮询状态直到完成或失败。
 */

const API_BASE_URL = '/v1';

// ============ 类型定义 ============

// ── 兼容保留文件的类型导出（Gallery / Settings / MaterialDetailModal） ──

export interface Material {
  id: string;
  type: 'image' | 'video';
  url: string;
  urls?: string[];
  prompt?: string;
  provider?: string;
  model?: string;
  conversation_id?: number;
  conversation_title?: string;
  created_at: string;
  completed_at?: string;
  duration?: number;
  width?: number;
  height?: number;
  cost?: number;
  generation_time?: number;
  metadata?: Record<string, any>;
}

export interface MaterialListResponse {
  items: Material[];
  total: number;
  page: number;
  page_size: number;
}

export interface APIProviderResponse {
  id: number;
  name: string;
  base_url: string;
  model_mapping: Record<string, string>;
  weight: number;
  is_active: boolean;
  key_preview?: string;
  created_at?: string;
  updated_at?: string;
}

export interface APIProviderCreate {
  name: string;
  base_url: string;
  api_key: string;
  model_mapping: Record<string, string>;
  weight?: number;
}

// ── 任务接口类型 ──

export interface TaskSubmitRequest {
  fileUrl: string;
  templateId: string;
}

export interface TaskSubmitResponse {
  task_id: string;
}

export type TaskStatus = 'pending' | 'processing' | 'success' | 'failed';

export interface TaskStatusResponse {
  task_id: string;
  status: TaskStatus;
  result?: Record<string, any>;
  error?: string;
}

// ============ API Client ============

class API {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `请求失败 (${response.status})`);
    }

    return response.json();
  }

  /**
   * 提交任务：入参仅 fileUrl + templateId
   */
  async submitTask(request: TaskSubmitRequest): Promise<TaskSubmitResponse> {
    return this.request<TaskSubmitResponse>('/tasks', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  /**
   * 查询任务状态
   */
  async getTaskStatus(taskId: string): Promise<TaskStatusResponse> {
    return this.request<TaskStatusResponse>(`/tasks/${taskId}`);
  }

  /**
   * 轮询任务直到完成或失败
   */
  async pollTask(
    taskId: string,
    maxAttempts = 120,
    intervalMs = 3000,
  ): Promise<TaskStatusResponse> {
    for (let i = 0; i < maxAttempts; i++) {
      const result = await this.getTaskStatus(taskId);
      if (result.status === 'success' || result.status === 'failed') {
        return result;
      }
      await new Promise((resolve) => setTimeout(resolve, intervalMs));
    }
    throw new Error('任务超时');
  }

  // ============ 中转站管理（保留） ============

  async createProvider(request: APIProviderCreate): Promise<APIProviderResponse> {
    return this.request<APIProviderResponse>('/providers', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async listProviders(): Promise<APIProviderResponse[]> {
    return this.request<APIProviderResponse[]>('/providers');
  }

  async getProvider(providerId: number): Promise<APIProviderResponse> {
    return this.request<APIProviderResponse>(`/providers/${providerId}`);
  }

  async updateProvider(
    providerId: number,
    request: Record<string, any>,
  ): Promise<APIProviderResponse> {
    return this.request<APIProviderResponse>(`/providers/${providerId}`, {
      method: 'PATCH',
      body: JSON.stringify(request),
    });
  }

  async deleteProvider(providerId: number): Promise<void> {
    await this.request(`/providers/${providerId}`, { method: 'DELETE' });
  }

  // ============ 素材库（保留） ============

  async listMaterials(
    params: Record<string, any> = {},
  ): Promise<MaterialListResponse> {
    const queryParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        queryParams.append(key, String(value));
      }
    });
    const query = queryParams.toString() ? `?${queryParams.toString()}` : '';
    return this.request<MaterialListResponse>(`/materials${query}`);
  }

  async getMaterial(materialId: string): Promise<Material> {
    return this.request<Material>(`/materials/${materialId}`);
  }

  async deleteMaterial(materialId: string): Promise<void> {
    await this.request(`/materials/${materialId}`, { method: 'DELETE' });
  }

  // ============ 用量统计（Usage 页面） ============

  async getDetailedUsage(
    startDate: string,
    endDate: string,
  ): Promise<any> {
    return this.request(`/usage/detailed?start=${startDate}&end=${endDate}`);
  }

  async getPricing(): Promise<any> {
    return this.request('/pricing');
  }
}

export const api = new API();
