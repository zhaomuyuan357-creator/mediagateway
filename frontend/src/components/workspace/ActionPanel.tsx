/**
 * ActionPanel.tsx — 操作面板
 *
 * 功能：
 *   - 一键生成按钮（file + template 均选中后激活）
 *   - 任务状态指示（pending / processing / success / failed）
 *   - 调用 store.submitTask() 提交任务
 */

import { useTaskStore } from '../../lib/store';
import { Button } from '../ui/button';

export function ActionPanel() {
  const {
    selectedFile,
    selectedTemplate,
    taskStatus,
    taskError,
    submitTask,
    reset,
  } = useTaskStore();

  const canSubmit = selectedFile && selectedTemplate && !taskStatus;
  const isProcessing = taskStatus === 'pending' || taskStatus === 'processing';

  return (
    <div className="space-y-3">
      {/* 主操作按钮 */}
      <Button
        className="w-full h-12 text-base font-medium bg-blue-600 hover:bg-blue-700
                   disabled:opacity-40 disabled:cursor-not-allowed transition-all"
        disabled={!canSubmit && !isProcessing}
        onClick={isProcessing ? undefined : submitTask}
      >
        {isProcessing ? (
          <span className="flex items-center gap-2">
            <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24">
              <circle
                className="opacity-25"
                cx="12" cy="12" r="10"
                stroke="currentColor" strokeWidth="4" fill="none"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
            {taskStatus === 'pending' ? '提交中…' : '生成中…'}
          </span>
        ) : taskStatus === 'success' ? (
          '✓ 生成完成'
        ) : taskStatus === 'failed' ? (
          '生成失败'
        ) : (
          '一键生成'
        )}
      </Button>

      {/* 状态提示 */}
      {!selectedFile && !taskStatus && (
        <p className="text-xs text-slate-600 text-center">请先上传素材文件</p>
      )}
      {selectedFile && !selectedTemplate && !taskStatus && (
        <p className="text-xs text-slate-600 text-center">请选择商业目标</p>
      )}
      {taskError && (
        <p className="text-xs text-red-400 text-center">{taskError}</p>
      )}

      {/* 完成/失败后显示重置按钮 */}
      {(taskStatus === 'success' || taskStatus === 'failed') && (
        <Button
          variant="ghost"
          className="w-full text-slate-400 hover:text-white"
          onClick={reset}
        >
          重新开始
        </Button>
      )}
    </div>
  );
}
