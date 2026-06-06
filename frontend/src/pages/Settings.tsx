import { useState, useEffect } from 'react';
import { api, APIProviderResponse, APIProviderCreate } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Settings as SettingsIcon,
  Plus,
  Trash2,
  CheckCircle,
  XCircle,
  ArrowLeft,
  Server,
  Edit3,
  Save,
  X,
  ToggleLeft,
  ToggleRight,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

type SettingsTab = 'providers';

const TASK_TYPE_LABELS: Record<string, string> = {
  image: '图片生成',
  video: '视频生成',
  analysis: 'AI 分析',
};

export default function Settings() {
  const navigate = useNavigate();
  const [activeTab] = useState<SettingsTab>('providers');
  const [providers, setProviders] = useState<APIProviderResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Add provider form state
  const [showAddForm, setShowAddForm] = useState(false);
  const [newProvider, setNewProvider] = useState<APIProviderCreate>({
    name: '',
    base_url: '',
    api_key: '',
    model_mapping: {},
    weight: 1,
  });
  const [modelMappingText, setModelMappingText] = useState('{"image": "", "video": "", "analysis": ""}');

  // Edit state
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState({
    name: '',
    base_url: '',
    api_key: '',
    model_mapping: '{}',
    weight: 1,
  });

  useEffect(() => {
    loadProviders();
  }, []);

  const loadProviders = async () => {
    try {
      const data = await api.listProviders();
      setProviders(data);
    } catch (err: any) {
      setError('加载中转站列表失败');
    }
  };

  const handleAddProvider = async () => {
    if (!newProvider.name.trim() || !newProvider.base_url.trim() || !newProvider.api_key.trim()) {
      setError('请填写名称、地址和 API Key');
      return;
    }

    let modelMapping: Record<string, string>;
    try {
      modelMapping = JSON.parse(modelMappingText);
    } catch {
      setError('模型映射格式错误，请输入合法 JSON');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess('');
    try {
      await api.createProvider({
        ...newProvider,
        model_mapping: modelMapping,
      });
      setSuccess('中转站添加成功！');
      setShowAddForm(false);
      setNewProvider({ name: '', base_url: '', api_key: '', model_mapping: {}, weight: 1 });
      setModelMappingText('{"image": "", "video": "", "analysis": ""}');
      await loadProviders();
    } catch (err: any) {
      setError(err.message || '添加失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteProvider = async (providerId: number) => {
    if (!confirm('确定要删除此中转站吗？')) return;
    try {
      await api.deleteProvider(providerId);
      setSuccess('中转站已删除');
      await loadProviders();
    } catch (err: any) {
      setError(err.message || '删除失败');
    }
  };

  const handleToggleActive = async (provider: APIProviderResponse) => {
    try {
      await api.updateProvider(provider.id, { is_active: !provider.is_active });
      await loadProviders();
    } catch (err: any) {
      setError(err.message || '更新失败');
    }
  };

  const startEdit = (provider: APIProviderResponse) => {
    setEditingId(provider.id);
    setEditForm({
      name: provider.name,
      base_url: provider.base_url,
      api_key: '',
      model_mapping: JSON.stringify(provider.model_mapping, null, 2),
      weight: provider.weight,
    });
  };

  const cancelEdit = () => {
    setEditingId(null);
  };

  const handleSaveEdit = async () => {
    if (!editingId) return;

    let modelMapping: Record<string, string>;
    try {
      modelMapping = JSON.parse(editForm.model_mapping);
    } catch {
      setError('模型映射格式错误，请输入合法 JSON');
      return;
    }

    setLoading(true);
    setError('');
    try {
      const update: Record<string, any> = {
        name: editForm.name,
        base_url: editForm.base_url,
        model_mapping: modelMapping,
        weight: editForm.weight,
      };
      if (editForm.api_key.trim()) {
        update.api_key = editForm.api_key.trim();
      }
      await api.updateProvider(editingId, update);
      setSuccess('中转站已更新');
      setEditingId(null);
      await loadProviders();
    } catch (err: any) {
      setError(err.message || '更新失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-zinc-950">
      {/* Header */}
      <header className="border-b border-zinc-800/50 bg-zinc-900/50 backdrop-blur-sm">
        <div className="px-6 py-4">
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
              <h1 className="text-lg font-semibold text-zinc-100">设置</h1>
              <p className="text-xs text-zinc-500 mt-0.5">管理中转站配置</p>
            </div>
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {/* Messages */}
        {error && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm flex items-center gap-2">
            <XCircle className="h-4 w-4 flex-shrink-0" />
            {error}
            <button onClick={() => setError('')} className="ml-auto"><X className="h-3.5 w-3.5" /></button>
          </div>
        )}
        {success && (
          <div className="mb-4 p-3 bg-green-500/10 border border-green-500/20 rounded-lg text-green-400 text-sm flex items-center gap-2">
            <CheckCircle className="h-4 w-4 flex-shrink-0" />
            {success}
            <button onClick={() => setSuccess('')} className="ml-auto"><X className="h-3.5 w-3.5" /></button>
          </div>
        )}

        {/* Providers Tab */}
        {activeTab === 'providers' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-medium text-zinc-300">中转站管理</h2>
                <p className="text-xs text-zinc-600 mt-1">配置 API 中转站，系统将按权重自动分配请求</p>
              </div>
              <Button
                onClick={() => setShowAddForm(!showAddForm)}
                className="bg-sky-600 hover:bg-sky-500 text-white"
                size="sm"
              >
                <Plus className="h-4 w-4 mr-1" />
                添加中转站
              </Button>
            </div>

            {/* Add provider form */}
            {showAddForm && (
              <Card className="bg-zinc-900/50 border-zinc-800/50">
                <CardContent className="p-4 space-y-3">
                  <h3 className="text-sm font-medium text-zinc-300">新增中转站</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs text-zinc-500 mb-1">名称</label>
                      <Input
                        placeholder="如：XX中转站-图片"
                        value={newProvider.name}
                        onChange={(e) => setNewProvider({ ...newProvider, name: e.target.value })}
                        className="bg-zinc-800 border-zinc-700 text-zinc-200"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-zinc-500 mb-1">API 地址</label>
                      <Input
                        placeholder="https://api.example.com/v1"
                        value={newProvider.base_url}
                        onChange={(e) => setNewProvider({ ...newProvider, base_url: e.target.value })}
                        className="bg-zinc-800 border-zinc-700 text-zinc-200"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-zinc-500 mb-1">API Key</label>
                      <Input
                        type="password"
                        placeholder="sk-..."
                        value={newProvider.api_key}
                        onChange={(e) => setNewProvider({ ...newProvider, api_key: e.target.value })}
                        className="bg-zinc-800 border-zinc-700 text-zinc-200"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-zinc-500 mb-1">权重</label>
                      <Input
                        type="number"
                        min={1}
                        value={newProvider.weight}
                        onChange={(e) => setNewProvider({ ...newProvider, weight: parseInt(e.target.value) || 1 })}
                        className="bg-zinc-800 border-zinc-700 text-zinc-200"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs text-zinc-500 mb-1">模型映射（JSON）</label>
                    <textarea
                      value={modelMappingText}
                      onChange={(e) => setModelMappingText(e.target.value)}
                      placeholder='{"image": "dall-e-3", "video": "seedance-2.0-t2v", "analysis": "gpt-4o"}'
                      className="w-full text-sm rounded-lg border border-zinc-700 bg-zinc-800 p-2.5 text-zinc-300 min-h-[60px] resize-y focus:outline-none focus:border-sky-500 font-mono"
                    />
                  </div>
                  <div className="flex gap-2 justify-end">
                    <Button variant="ghost" size="sm" onClick={() => setShowAddForm(false)} className="text-zinc-400">
                      取消
                    </Button>
                    <Button onClick={handleAddProvider} disabled={loading} className="bg-sky-600 hover:bg-sky-500" size="sm">
                      {loading ? '添加中...' : '确认添加'}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Provider list */}
            <div className="space-y-3">
              {providers.length === 0 ? (
                <Card className="bg-zinc-900/50 border-zinc-800/50">
                  <CardContent className="p-8 text-center">
                    <Server className="h-12 w-12 text-zinc-800 mx-auto mb-3" />
                    <p className="text-zinc-500 text-sm">尚未配置任何中转站</p>
                    <p className="text-zinc-600 text-xs mt-1">添加 API 中转站开始使用</p>
                  </CardContent>
                </Card>
              ) : (
                providers.map((provider) => (
                  <Card key={provider.id} className="bg-zinc-900/50 border-zinc-800/50 hover:border-zinc-700/50 transition-colors">
                    <CardContent className="p-4">
                      {editingId === provider.id ? (
                        /* Edit mode */
                        <div className="space-y-3">
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            <div>
                              <label className="block text-xs text-zinc-500 mb-1">名称</label>
                              <Input
                                value={editForm.name}
                                onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                                className="bg-zinc-800 border-zinc-700 text-zinc-200"
                              />
                            </div>
                            <div>
                              <label className="block text-xs text-zinc-500 mb-1">API 地址</label>
                              <Input
                                value={editForm.base_url}
                                onChange={(e) => setEditForm({ ...editForm, base_url: e.target.value })}
                                className="bg-zinc-800 border-zinc-700 text-zinc-200"
                              />
                            </div>
                            <div>
                              <label className="block text-xs text-zinc-500 mb-1">新 API Key（留空不更新）</label>
                              <Input
                                type="password"
                                placeholder="留空则保持不变"
                                value={editForm.api_key}
                                onChange={(e) => setEditForm({ ...editForm, api_key: e.target.value })}
                                className="bg-zinc-800 border-zinc-700 text-zinc-200"
                              />
                            </div>
                            <div>
                              <label className="block text-xs text-zinc-500 mb-1">权重</label>
                              <Input
                                type="number"
                                min={1}
                                value={editForm.weight}
                                onChange={(e) => setEditForm({ ...editForm, weight: parseInt(e.target.value) || 1 })}
                                className="bg-zinc-800 border-zinc-700 text-zinc-200"
                              />
                            </div>
                          </div>
                          <div>
                            <label className="block text-xs text-zinc-500 mb-1">模型映射（JSON）</label>
                            <textarea
                              value={editForm.model_mapping}
                              onChange={(e) => setEditForm({ ...editForm, model_mapping: e.target.value })}
                              className="w-full text-sm rounded-lg border border-zinc-700 bg-zinc-800 p-2.5 text-zinc-300 min-h-[60px] resize-y focus:outline-none focus:border-sky-500 font-mono"
                            />
                          </div>
                          <div className="flex gap-2 justify-end">
                            <Button variant="ghost" size="sm" onClick={cancelEdit} className="text-zinc-400">
                              取消
                            </Button>
                            <Button onClick={handleSaveEdit} disabled={loading} className="bg-sky-600 hover:bg-sky-500" size="sm">
                              <Save className="h-3.5 w-3.5 mr-1" />
                              {loading ? '保存中...' : '保存'}
                            </Button>
                          </div>
                        </div>
                      ) : (
                        /* Display mode */
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-lg bg-zinc-800 flex items-center justify-center text-lg">
                              <Server className="h-5 w-5 text-sky-400" />
                            </div>
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-medium text-zinc-200">
                                  {provider.name}
                                </span>
                                <Badge
                                  variant="secondary"
                                  className={`text-xs ${
                                    provider.is_active
                                      ? 'bg-green-500/10 text-green-400 border-green-500/20'
                                      : 'bg-zinc-700/50 text-zinc-500 border-zinc-600/20'
                                  }`}
                                >
                                  {provider.is_active ? '启用' : '禁用'}
                                </Badge>
                                <span className="text-xs text-zinc-600 font-mono">
                                  权重 {provider.weight}
                                </span>
                              </div>
                              <p className="text-xs text-zinc-600 mt-0.5 font-mono">{provider.base_url}</p>
                              {provider.key_preview && (
                                <p className="text-xs text-zinc-700 mt-0.5 font-mono">{provider.key_preview}</p>
                              )}
                              <div className="flex gap-1.5 mt-1.5 flex-wrap">
                                {Object.entries(provider.model_mapping).map(([type, model]) => (
                                  <Badge key={type} variant="outline" className="text-[10px] text-zinc-500 border-zinc-700">
                                    {TASK_TYPE_LABELS[type] || type}: {model}
                                  </Badge>
                                ))}
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleToggleActive(provider)}
                              className="text-zinc-500 hover:text-zinc-300"
                              title={provider.is_active ? '禁用' : '启用'}
                            >
                              {provider.is_active ? (
                                <ToggleRight className="h-4 w-4 text-green-400" />
                              ) : (
                                <ToggleLeft className="h-4 w-4" />
                              )}
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => startEdit(provider)}
                              className="text-zinc-500 hover:text-zinc-300"
                            >
                              <Edit3 className="h-3.5 w-3.5" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteProvider(provider.id)}
                              className="text-red-500/60 hover:text-red-400 hover:bg-red-500/10"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
