/**
 * MockTaskService — 前端联调模拟服务
 *
 * 功能：在无后端环境下，模拟 task 提交 → 轮询 → 成功 的完整状态流。
 *
 * 用法：
 *   import { enableMock, mockSubmitTask, mockPollTask } from './mockTaskService';
 *   enableMock();  // 开启 mock 模式
 *
 * 工作原理：
 *   - mockSubmitTask 返回一个递增的 mock task_id
 *   - mockPollTask 模拟 2 秒 processing 后返回 success + mock 数据
 *   - 通过 monkey-patch api 实例方法实现无侵入切换
 */

import { api } from './api';
import type { TaskSubmitRequest, TaskSubmitResponse, TaskStatusResponse } from './api';

// ── 内部状态 ──
let mockTaskCounter = 0;
let mockEnabled = false;
const mockTasks = new Map<string, { createdAt: number; fileUrl: string; templateId: string }>();

// ── Mock 数据 ──

const MOCK_IMAGE_RESULT: TaskStatusResponse = {
  task_id: 'mock-1',
  status: 'success',
  result: {
    image_urls: [
      'https://picsum.photos/seed/lr1/1024/1024',
      'https://picsum.photos/seed/lr2/1024/1024',
      'https://picsum.photos/seed/lr3/1024/1024',
      'https://picsum.photos/seed/lr4/1024/1024',
    ],
  },
};

const MOCK_VIDEO_RESULT: TaskStatusResponse = {
  task_id: 'mock-2',
  status: 'success',
  result: {
    video_url: 'https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4',
  },
};

// ── Mock 实现 ──

function mockSubmit(request: TaskSubmitRequest): TaskSubmitResponse {
  mockTaskCounter++;
  const taskId = `mock-task-${mockTaskCounter}`;
  mockTasks.set(taskId, {
    createdAt: Date.now(),
    fileUrl: request.fileUrl,
    templateId: request.templateId,
  });
  console.log(`[Mock] 任务已提交: ${taskId}`, request);
  return { task_id: taskId };
}

function mockPoll(taskId: string): TaskStatusResponse {
  const task = mockTasks.get(taskId);
  if (!task) {
    return { task_id: taskId, status: 'failed', error: '任务不存在' };
  }

  const elapsed = Date.now() - task.createdAt;

  // 前 2 秒为 processing
  if (elapsed < 2000) {
    return { task_id: taskId, status: 'processing' };
  }

  // 2 秒后返回 success（交替返回图片/视频结果）
  const isVideo = task.templateId.includes('video') || mockTaskCounter % 3 === 0;
  console.log(`[Mock] 任务完成: ${taskId}`, isVideo ? '视频结果' : '图片结果');

  return {
    task_id: taskId,
    status: 'success',
    result: isVideo ? MOCK_VIDEO_RESULT.result : MOCK_IMAGE_RESULT.result,
  };
}

async function mockPollTask(
  taskId: string,
  maxAttempts = 120,
  intervalMs = 500,
): Promise<TaskStatusResponse> {
  for (let i = 0; i < maxAttempts; i++) {
    const result = mockPoll(taskId);
    if (result.status === 'success' || result.status === 'failed') {
      return result;
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  throw new Error('Mock 任务超时');
}

// ── 保存原始方法引用 ──
const originalSubmitTask = api.submitTask.bind(api);
const originalPollTask = api.pollTask.bind(api);

// ── 启用/禁用 Mock ──

export function enableMock() {
  if (mockEnabled) return;
  mockEnabled = true;

  (api as any).submitTask = (req: TaskSubmitRequest) => Promise.resolve(mockSubmit(req));
  (api as any).pollTask = mockPollTask;

  console.log('[MockTaskService] 已启用 Mock 模式 — 提交任务将模拟 2 秒后返回成功');
}

export function disableMock() {
  if (!mockEnabled) return;
  mockEnabled = false;

  (api as any).submitTask = originalSubmitTask;
  (api as any).pollTask = originalPollTask;

  console.log('[MockTaskService] 已禁用 Mock 模式 — 使用真实 API');
}

export function isMockEnabled() {
  return mockEnabled;
}
