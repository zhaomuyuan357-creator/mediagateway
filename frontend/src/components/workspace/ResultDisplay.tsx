/**
 * ResultDisplay.tsx — 生成结果展示
 *
 * 功能：
 *   - 任务成功后展示图片网格或视频播放器
 *   - 每张图片带下载按钮
 *   - 视频带下载按钮
 *   - 仅在 taskStatus === 'success' 时渲染
 */

import { useTaskStore } from '../../lib/store';
import { Button } from '../ui/button';

export function ResultDisplay() {
  const { taskStatus, taskResult } = useTaskStore();

  if (taskStatus !== 'success' || !taskResult) return null;

  // 解析结果数据
  const images: string[] = taskResult.image_urls ?? (taskResult.image_url ? [taskResult.image_url] : []);
  const videoUrl: string | undefined = taskResult.video_url;

  // 视频结果
  if (videoUrl) {
    return (
      <div className="space-y-4">
        <h3 className="text-sm font-medium text-slate-300">生成结果</h3>
        <div className="rounded-2xl overflow-hidden bg-black border border-slate-800">
          <video
            src={videoUrl}
            controls
            className="w-full aspect-video"
          />
        </div>
        <Button
          variant="outline"
          className="w-full border-slate-700 text-slate-300 hover:bg-slate-800"
          onClick={() => {
            const a = document.createElement('a');
            a.href = videoUrl;
            a.download = `lumenroute-video-${Date.now()}.mp4`;
            a.click();
          }}
        >
          下载视频
        </Button>
      </div>
    );
  }

  // 图片结果
  if (images.length > 0) {
    return (
      <div className="space-y-4">
        <h3 className="text-sm font-medium text-slate-300">
          生成结果（{images.length} 张）
        </h3>
        <div className="grid grid-cols-2 gap-3">
          {images.map((url, i) => (
            <div
              key={i}
              className="relative group rounded-xl overflow-hidden bg-slate-900 border border-slate-800"
            >
              <img
                src={url}
                alt={`生成结果 ${i + 1}`}
                className="w-full aspect-square object-cover"
              />
              {/* 悬浮下载按钮 */}
              <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                <Button
                  size="sm"
                  className="bg-white/20 backdrop-blur-sm hover:bg-white/30 text-white"
                  onClick={() => {
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `lumenroute-${i + 1}.png`;
                    a.click();
                  }}
                >
                  下载
                </Button>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // 无结果数据
  return (
    <div className="text-center text-slate-500 py-8">
      <p>任务完成，但未获取到结果数据</p>
    </div>
  );
}
