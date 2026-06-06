/**
 * UploadZone.tsx — 拖拽上传区
 *
 * 功能：
 *   - 大面积虚线边框拖拽区域
 *   - 支持拖拽文件、点击浏览
 *   - 文件验证：50MB 限制，图片/视频类型
 *   - 选中后显示缩略图预览
 *   - 通过 store.setSelectedFile() 更新状态
 */

import { useRef, useCallback } from 'react';
import { useTaskStore } from '../../lib/store';
import { Button } from '../ui/button';

const MAX_SIZE = 50 * 1024 * 1024; // 50MB
const ACCEPTED_TYPES = [
  'image/jpeg', 'image/png', 'image/webp', 'image/gif',
  'video/mp4', 'video/webm', 'video/quicktime',
];

export function UploadZone() {
  const inputRef = useRef<HTMLInputElement>(null);
  const { selectedFile, setSelectedFile, clearFile } = useTaskStore();

  const validateAndSet = useCallback(
    (file: File) => {
      if (file.size > MAX_SIZE) {
        alert('文件大小不能超过 50MB');
        return;
      }
      if (!ACCEPTED_TYPES.includes(file.type)) {
        alert('仅支持 JPG/PNG/WebP/GIF/MP4/WebM 格式');
        return;
      }
      setSelectedFile(file);
    },
    [setSelectedFile],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      const file = e.dataTransfer.files[0];
      if (file) validateAndSet(file);
    },
    [validateAndSet],
  );

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) validateAndSet(file);
      // 重置 input 以便重复选择同一文件
      e.target.value = '';
    },
    [validateAndSet],
  );

  // 已选中文件 → 显示预览
  if (selectedFile) {
    const isVideo = selectedFile.file.type.startsWith('video/');

    return (
      <div className="relative rounded-2xl border border-slate-700/50 bg-slate-900/40 p-4">
        <div className="flex items-center gap-4">
          {/* 缩略图 */}
          <div className="w-20 h-20 rounded-lg overflow-hidden bg-slate-800 flex-shrink-0">
            {isVideo ? (
              <video
                src={selectedFile.previewUrl}
                className="w-full h-full object-cover"
                muted
              />
            ) : (
              <img
                src={selectedFile.previewUrl}
                alt={selectedFile.file.name}
                className="w-full h-full object-cover"
              />
            )}
          </div>

          {/* 文件信息 */}
          <div className="flex-1 min-w-0">
            <p className="text-sm text-white truncate">{selectedFile.file.name}</p>
            <p className="text-xs text-slate-500 mt-1">
              {(selectedFile.file.size / 1024 / 1024).toFixed(1)} MB ·{' '}
              {isVideo ? '视频' : '图片'}
            </p>
            {selectedFile.uploadedUrl && (
              <p className="text-xs text-green-500 mt-1">✓ 已上传</p>
            )}
          </div>

          {/* 移除按钮 */}
          <Button
            variant="ghost"
            size="sm"
            className="text-slate-500 hover:text-red-400"
            onClick={clearFile}
          >
            ✕
          </Button>
        </div>
      </div>
    );
  }

  // 未选中 → 拖拽区域
  return (
    <div
      className="relative rounded-2xl border-2 border-dashed border-slate-700 bg-slate-900/20
                 hover:border-blue-500/50 hover:bg-slate-900/40 transition-all duration-300
                 cursor-pointer group"
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onClick={() => inputRef.current?.click()}
    >
      <div className="flex flex-col items-center justify-center py-16 px-8">
        <div className="w-16 h-16 rounded-full bg-slate-800/50 flex items-center justify-center mb-4
                        group-hover:bg-blue-500/10 transition-colors">
          <svg
            className="w-8 h-8 text-slate-600 group-hover:text-blue-400 transition-colors"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            />
          </svg>
        </div>
        <p className="text-sm text-slate-400 group-hover:text-slate-300 transition-colors">
          拖拽图片或视频到此处，或点击浏览
        </p>
        <p className="text-xs text-slate-600 mt-2">
          支持 JPG / PNG / WebP / MP4 / WebM · 最大 50MB
        </p>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_TYPES.join(',')}
        className="hidden"
        onChange={handleFileInput}
      />
    </div>
  );
}
