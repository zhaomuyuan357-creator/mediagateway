import { Material } from '@/lib/api';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Download, Trash2, MessageSquare, Clock, Zap, DollarSign, Image as ImageIcon, Video as VideoIcon } from 'lucide-react';

interface MaterialDetailModalProps {
  material: Material | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDelete?: (material: Material) => void;
  onNavigateToConversation?: (conversationId: number) => void;
}

export function MaterialDetailModal({
  material,
  open,
  onOpenChange,
  onDelete,
  onNavigateToConversation,
}: MaterialDetailModalProps) {
  if (!material) return null;

  const providerLabel = (provider?: string) => {
    switch (provider) {
      case 'seedance': return 'Seedance 2.0';
      case 'openai-image': return 'OpenAI 图片生成';
      default: return provider || '未知';
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const allUrls = material.urls && material.urls.length > 0 ? material.urls : [material.url];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {material.type === 'video' ? (
              <VideoIcon className="h-5 w-5 text-purple-600" />
            ) : (
              <ImageIcon className="h-5 w-5 text-orange-600" />
            )}
            <span>素材详情</span>
            <Badge variant={material.type === 'video' ? 'default' : 'secondary'}>
              {material.type === 'video' ? '视频' : '图片'}
            </Badge>
          </DialogTitle>
        </DialogHeader>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 左侧：预览 */}
          <div className="space-y-3">
            {material.type === 'video' && material.url ? (
              <video
                src={material.url}
                controls
                className="w-full rounded-lg bg-black"
                style={{ maxHeight: '400px' }}
              />
            ) : (
              <div className="space-y-2">
                {allUrls.map((url, idx) => (
                  <img
                    key={idx}
                    src={url}
                    alt={`素材 ${idx + 1}`}
                    className="w-full rounded-lg object-contain"
                    style={{ maxHeight: '400px' }}
                  />
                ))}
              </div>
            )}
          </div>

          {/* 右侧：详情信息 */}
          <div className="space-y-4">
            {/* 提示词 */}
            {material.prompt && (
              <div>
                <h4 className="text-sm font-medium text-muted-foreground mb-1">提示词</h4>
                <p className="text-sm bg-muted p-3 rounded-md leading-relaxed">
                  {material.prompt}
                </p>
              </div>
            )}

            {/* 信息网格 */}
            <div className="grid grid-cols-2 gap-3">
              {/* 服务商 */}
              <div className="bg-muted/50 rounded-lg p-3">
                <div className="text-xs text-muted-foreground mb-1">服务商</div>
                <div className="text-sm font-medium">{providerLabel(material.provider)}</div>
              </div>

              {/* 模型 */}
              {material.model && (
                <div className="bg-muted/50 rounded-lg p-3">
                  <div className="text-xs text-muted-foreground mb-1">模型</div>
                  <div className="text-sm font-medium">{material.model}</div>
                </div>
              )}

              {/* 尺寸 */}
              {material.width && material.height && (
                <div className="bg-muted/50 rounded-lg p-3">
                  <div className="text-xs text-muted-foreground mb-1">尺寸</div>
                  <div className="text-sm font-medium">{material.width} × {material.height}</div>
                </div>
              )}

              {/* 时长 */}
              {material.duration && (
                <div className="bg-muted/50 rounded-lg p-3">
                  <div className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
                    <Clock className="h-3 w-3" /> 时长
                  </div>
                  <div className="text-sm font-medium">{material.duration.toFixed(1)}s</div>
                </div>
              )}

              {/* 费用 */}
              {material.cost != null && (
                <div className="bg-muted/50 rounded-lg p-3">
                  <div className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
                    <DollarSign className="h-3 w-3" /> 费用
                  </div>
                  <div className="text-sm font-medium">
                    {material.provider === 'seedance' ? '¥' : '$'}{material.cost.toFixed(4)}
                  </div>
                </div>
              )}

              {/* 生成耗时 */}
              {material.generation_time && (
                <div className="bg-muted/50 rounded-lg p-3">
                  <div className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
                    <Zap className="h-3 w-3" /> 生成耗时
                  </div>
                  <div className="text-sm font-medium">{material.generation_time.toFixed(1)}s</div>
                </div>
              )}
            </div>

            {/* 时间 */}
            <div className="bg-muted/50 rounded-lg p-3">
              <div className="text-xs text-muted-foreground mb-1">创建时间</div>
              <div className="text-sm font-medium">{formatDate(material.created_at)}</div>
              {material.completed_at && (
                <>
                  <div className="text-xs text-muted-foreground mt-2 mb-1">完成时间</div>
                  <div className="text-sm font-medium">{formatDate(material.completed_at)}</div>
                </>
              )}
            </div>

            {/* 来源对话 */}
            {material.conversation_id && (
              <div className="bg-muted/50 rounded-lg p-3">
                <div className="text-xs text-muted-foreground mb-1">来源对话</div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">
                    {material.conversation_title || `对话 #${material.conversation_id}`}
                  </span>
                  {onNavigateToConversation && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 px-2 text-xs"
                      onClick={() => onNavigateToConversation(material.conversation_id!)}
                    >
                      <MessageSquare className="h-3 w-3 mr-1" />
                      查看
                    </Button>
                  )}
                </div>
              </div>
            )}

            {/* 操作按钮 */}
            <div className="flex gap-2 pt-2">
              {material.url && (
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => window.open(material.url, '_blank')}
                >
                  <Download className="h-4 w-4 mr-2" />
                  下载
                </Button>
              )}
              {onDelete && (
                <Button
                  variant="destructive"
                  className="flex-1"
                  onClick={() => {
                    onDelete(material);
                    onOpenChange(false);
                  }}
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  删除
                </Button>
              )}
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
