/**
 * TaskWorkspace.tsx — 主工作台页面
 *
 * 布局结构：
 *   顶部 — UploadZone（最显著的交互入口）
 *   中部 — GoalCardGrid（业务目标选择）
 *   底部 — ActionPanel（一键生成控制）
 *   结果 — ResultDisplay（自动生成后渲染）
 *
 * 使用 max-w-6xl mx-auto 保持专业工具感。
 */

import { UploadZone } from '../components/workspace/UploadZone';
import { GoalCardGrid } from '../components/workspace/GoalCardGrid';
import { ActionPanel } from '../components/workspace/ActionPanel';
import { ResultDisplay } from '../components/workspace/ResultDisplay';
import { useTaskStore } from '../lib/store';

function TaskWorkspace() {
  const { taskStatus } = useTaskStore();
  const showResult = taskStatus === 'success';

  return (
    <div className="min-h-screen bg-slate-950">
      {/* 顶部导航栏 */}
      <header className="border-b border-slate-800/50 bg-slate-950/80 backdrop-blur-sm sticky top-0 z-20">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <h1 className="text-lg font-bold text-white tracking-tight">LumenRoute AI</h1>
          <span className="text-xs text-slate-500">电商多智能体执行引擎</span>
        </div>
      </header>

      {/* 主内容区 */}
      <main className="max-w-6xl mx-auto px-6 py-8">
        <div className="space-y-8">
          {/* ── 上传区 ── */}
          <section>
            <UploadZone />
          </section>

          {/* ── 目标选择区 ── */}
          <section>
            <GoalCardGrid />
          </section>

          {/* ── 操作控制区 ── */}
          <section className="max-w-md mx-auto">
            <ActionPanel />
          </section>

          {/* ── 结果展示区（成功后自动出现） ── */}
          {showResult && (
            <section className="pt-4 border-t border-slate-800/50">
              <ResultDisplay />
            </section>
          )}
        </div>
      </main>
    </div>
  );
}

export default TaskWorkspace;
