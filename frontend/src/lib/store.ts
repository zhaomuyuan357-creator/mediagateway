/**
 * Zustand Store — 极简任务状态树
 *
 * 仅保留 4 个核心字段：
 *   selectedFile    — 用户上传的素材文件
 *   selectedTemplate — 用户选择的业务目标模板
 *   taskStatus      — 任务轮询状态
 *   taskResult      — 最终结果数据
 *
 * 无参数配置、无对话/消息模型、无中间状态。
 */

import { create } from 'zustand';
import { api, type TaskStatus, type TaskStatusResponse } from './api';

// ============ 类型定义 ============

export interface SelectedFile {
  file: File;
  previewUrl: string;
  uploadedUrl?: string;
}

export interface Template {
  id: string;
  name: string;
  description: string;
}

// ============ Store 接口 ============

interface TaskStore {
  // 素材
  selectedFile: SelectedFile | null;
  setSelectedFile: (file: File) => void;
  clearFile: () => void;

  // 业务目标模板
  selectedTemplate: Template | null;
  setSelectedTemplate: (template: Template) => void;
  clearTemplate: () => void;

  // 任务状态
  taskStatus: TaskStatus | null;
  taskId: string | null;
  taskError: string | null;

  // 结果数据
  taskResult: Record<string, any> | null;

  // 核心动作
  submitTask: () => Promise<void>;
  reset: () => void;
}

// ============ Store 实现 ============

export const useTaskStore = create<TaskStore>((set, get) => ({
  // ── 素材 ──
  selectedFile: null,

  setSelectedFile: (file: File) => {
    // 清理旧的预览 URL
    const prev = get().selectedFile;
    if (prev?.previewUrl) URL.revokeObjectURL(prev.previewUrl);

    set({
      selectedFile: {
        file,
        previewUrl: URL.createObjectURL(file),
      },
      // 切换文件时重置任务状态
      taskStatus: null,
      taskId: null,
      taskError: null,
      taskResult: null,
    });
  },

  clearFile: () => {
    const prev = get().selectedFile;
    if (prev?.previewUrl) URL.revokeObjectURL(prev.previewUrl);
    set({ selectedFile: null });
  },

  // ── 业务目标模板 ──
  selectedTemplate: null,

  setSelectedTemplate: (template: Template) => {
    set({
      selectedTemplate: template,
      // 切换模板时重置任务状态
      taskStatus: null,
      taskId: null,
      taskError: null,
      taskResult: null,
    });
  },

  clearTemplate: () => set({ selectedTemplate: null }),

  // ── 任务状态 ──
  taskStatus: null,
  taskId: null,
  taskError: null,
  taskResult: null,

  // ── 核心动作：提交任务 ──
  submitTask: async () => {
    const { selectedFile, selectedTemplate } = get();

    if (!selectedFile) {
      set({ taskError: '请先上传文件' });
      return;
    }
    if (!selectedTemplate) {
      set({ taskError: '请选择业务目标' });
      return;
    }

    set({ taskStatus: 'pending', taskError: null, taskResult: null });

    try {
      // fileUrl 优先用已上传的 URL，降级用本地预览 URL（Mock 模式兼容）
      const fileUrl = selectedFile.uploadedUrl || selectedFile.previewUrl;

      // 1. 提交任务
      const submitResult = await api.submitTask({
        fileUrl,
        templateId: selectedTemplate.id,
      });

      set({ taskId: submitResult.task_id, taskStatus: 'processing' });

      // 2. 轮询直到完成
      const finalResult = await api.pollTask(submitResult.task_id);

      if (finalResult.status === 'success') {
        set({
          taskStatus: 'success',
          taskResult: finalResult.result ?? null,
        });
      } else {
        set({
          taskStatus: 'failed',
          taskError: finalResult.error ?? '任务失败',
        });
      }
    } catch (err) {
      set({
        taskStatus: 'failed',
        taskError: err instanceof Error ? err.message : '未知错误',
      });
    }
  },

  // ── 重置全部状态 ──
  reset: () => {
    const prev = get().selectedFile;
    if (prev?.previewUrl) URL.revokeObjectURL(prev.previewUrl);
    set({
      selectedFile: null,
      selectedTemplate: null,
      taskStatus: null,
      taskId: null,
      taskError: null,
      taskResult: null,
    });
  },
}));
