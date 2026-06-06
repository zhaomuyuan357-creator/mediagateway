import { useState, useEffect, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { api, Material, MaterialListResponse } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Search,
  Image as ImageIcon,
  Video as VideoIcon,
  MessageSquare,
  FileText,
  Download,
  Trash2,
  RefreshCw,
  Clock,
  ArrowLeft,
} from 'lucide-react';

type GalleryTab = 'conversations' | 'documents' | 'media';

export default function Gallery() {
  const location = useLocation();
  const navigate = useNavigate();

  // Determine active tab from URL
  const getTabFromPath = (): GalleryTab => {
    if (location.pathname.includes('/documents')) return 'documents';
    if (location.pathname.includes('/media')) return 'media';
    return 'conversations';
  };

  const [activeTab, setActiveTab] = useState<GalleryTab>(getTabFromPath());
  const [materials, setMaterials] = useState<Material[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  // Load materials based on tab
  const loadMaterials = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = {
        page: 1,
        page_size: 50,
      };

      // Filter by type based on tab
      if (activeTab === 'media') {
        params.type = 'image,video';
      }

      const response = await api.listMaterials(params);
      setMaterials(response.items || []);
    } catch (err) {
      console.error('Failed to load materials:', err);
    } finally {
      setLoading(false);
    }
  }, [activeTab]);

  useEffect(() => {
    loadMaterials();
  }, [loadMaterials]);

  // Update tab when URL changes
  useEffect(() => {
    setActiveTab(getTabFromPath());
  }, [location.pathname]);

  const handleTabChange = (tab: GalleryTab) => {
    setActiveTab(tab);
    navigate(`/gallery/${tab}`);
  };

  // Filter materials by search
  const filteredMaterials = materials.filter((m) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      m.prompt?.toLowerCase().includes(query) ||
      m.type?.toLowerCase().includes(query)
    );
  });

  // Format date
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    } else if (diffDays === 1) {
      return '昨天';
    } else if (diffDays < 7) {
      return `${diffDays}天前`;
    }
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
  };

  // Tab configuration
  const tabs = [
    { id: 'conversations' as const, label: '对话记录', icon: MessageSquare },
    { id: 'documents' as const, label: '文档资料', icon: FileText },
    { id: 'media' as const, label: '媒体素材', icon: ImageIcon },
  ];

  return (
    <div className="flex flex-col h-screen bg-zinc-950">
      {/* Header */}
      <header className="border-b border-zinc-800/50 bg-zinc-900/50 backdrop-blur-sm">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="icon"
                className="text-zinc-400 hover:text-zinc-200"
                onClick={() => navigate('/')}
              >
                <ArrowLeft className="h-4 w-4" />
              </Button>
              <div>
                <h1 className="text-lg font-semibold text-zinc-100">素材库</h1>
                <p className="text-xs text-zinc-500 mt-0.5">管理你的创作内容</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
                <Input
                  placeholder="搜索素材..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 w-64 bg-zinc-800/50 border-zinc-700/50 text-zinc-200 placeholder:text-zinc-600 focus:bg-zinc-800"
                />
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="text-zinc-400 hover:text-zinc-200"
                onClick={loadMaterials}
              >
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex gap-1 mt-4">
            {tabs.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => handleTabChange(id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-all duration-200 ${
                  activeTab === id
                    ? 'bg-sky-500/10 text-sky-400 border border-sky-500/20'
                    : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50 border border-transparent'
                }`}
              >
                <Icon className="h-4 w-4" />
                {label}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <Card key={i} className="bg-zinc-900/50 border-zinc-800/50">
                <CardContent className="p-4">
                  <Skeleton className="h-40 w-full rounded-lg bg-zinc-800" />
                  <Skeleton className="h-4 w-3/4 mt-3 bg-zinc-800" />
                  <Skeleton className="h-3 w-1/2 mt-2 bg-zinc-800" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : filteredMaterials.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-zinc-500">
            <div className="w-16 h-16 rounded-2xl bg-zinc-900 border border-zinc-800 flex items-center justify-center mb-4">
              {activeTab === 'conversations' ? (
                <MessageSquare className="h-8 w-8 text-zinc-700" />
              ) : activeTab === 'documents' ? (
                <FileText className="h-8 w-8 text-zinc-700" />
              ) : (
                <ImageIcon className="h-8 w-8 text-zinc-700" />
              )}
            </div>
            <p className="text-sm">暂无{tabs.find(t => t.id === activeTab)?.label}</p>
            <p className="text-xs text-zinc-600 mt-1">开始创作后，内容将在这里显示</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredMaterials.map((material) => (
              <Card
                key={material.id}
                className="group bg-zinc-900/50 border-zinc-800/50 hover:border-zinc-700/50 hover:bg-zinc-900/80 transition-all duration-200 cursor-pointer"
              >
                <CardContent className="p-0">
                  {/* Preview */}
                  <div className="relative overflow-hidden rounded-t-lg">
                    {material.type === 'video' && material.url ? (
                      <video
                        src={material.url}
                        className="w-full aspect-video object-cover"
                        muted
                        preload="metadata"
                      />
                    ) : material.url ? (
                      <img
                        src={material.url}
                        alt={material.prompt || '素材'}
                        className="w-full aspect-video object-cover"
                        loading="lazy"
                      />
                    ) : (
                      <div className="w-full aspect-video bg-zinc-800 flex items-center justify-center">
                        <ImageIcon className="h-8 w-8 text-zinc-700" />
                      </div>
                    )}

                    {/* Type badge */}
                    <div className="absolute top-2 left-2">
                      <Badge
                        variant="secondary"
                        className="bg-black/60 text-zinc-200 border-0 text-xs"
                      >
                        {material.type === 'video' ? (
                          <><VideoIcon className="h-3 w-3 mr-1" /> 视频</>
                        ) : (
                          <><ImageIcon className="h-3 w-3 mr-1" /> 图片</>
                        )}
                      </Badge>
                    </div>

                    {/* Actions overlay */}
                    <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                      <Button size="sm" variant="secondary" className="bg-zinc-800 hover:bg-zinc-700">
                        <Download className="h-3.5 w-3.5 mr-1" />
                        下载
                      </Button>
                      <Button size="sm" variant="destructive" className="bg-red-600/80 hover:bg-red-600">
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>

                  {/* Info */}
                  <div className="p-3">
                    <p className="text-sm text-zinc-300 line-clamp-2 leading-relaxed">
                      {material.prompt || '无描述'}
                    </p>
                    <div className="flex items-center gap-2 mt-2">
                      <Clock className="h-3 w-3 text-zinc-600" />
                      <span className="text-xs text-zinc-600">
                        {formatDate(material.created_at)}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
