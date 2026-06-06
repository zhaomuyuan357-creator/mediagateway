import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { api } from '@/lib/api';
import { RefreshCw, AlertCircle, TrendingUp, Film, Clock, Zap } from 'lucide-react';

interface UsageSummary {
  total_generations: number;
  total_cost: number;
  total_video_duration: number;
  total_processing_time: number;
  average_cost_per_generation: number;
}

interface DailyStats {
  date: string;
  count: number;
  cost: number;
  duration: number;
  success: number;
  failed: number;
}

interface ProviderStats {
  provider: string;
  count: number;
  cost: number;
  duration: number;
  avg_cost_per_second: number;
}

interface DetailedUsage {
  summary: UsageSummary;
  daily: DailyStats[];
  by_provider: ProviderStats[];
}

interface PricingInfo {
  provider: string;
  model: string;
  per_second?: number;
  per_image?: number;
  base_cost: number;
  currency: string;
  pricing_type: string;
  examples?: {
    "5_seconds": number;
    "10_seconds": number;
    "20_seconds": number;
  };
}

export default function Usage() {
  const [usage, setUsage] = useState<DetailedUsage | null>(null);
  const [pricing, setPricing] = useState<PricingInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState({
    start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    end: new Date().toISOString().split('T')[0],
  });

  useEffect(() => {
    loadData();
  }, [dateRange]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [usageRes, pricingRes] = await Promise.all([
        api.getDetailedUsage(dateRange.start, dateRange.end),
        api.getPricing(),
      ]);
      setUsage(usageRes);
      setPricing(pricingRes.pricing || []);
    } catch (err) {
      console.error('加载用量数据失败:', err);
      setError(err instanceof Error ? err.message : '加载数据失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  const currencyLabel = (provider: string) => {
    return provider === 'seedance' ? '¥' : '$';
  };

  const providerDisplayName = (provider: string) => {
    switch (provider) {
      case 'seedance': return 'Seedance 2.0 (火山引擎)';
      case 'openai-image': return 'OpenAI 图片生成';
      default: return provider;
    }
  };

  // Skeleton loading
  if (loading) {
    return (
      <div className="container mx-auto py-6 md:py-8 px-4">
        <div className="mb-8">
          <Skeleton className="h-9 w-40 mb-2" />
          <Skeleton className="h-4 w-60" />
        </div>

        {/* Date range skeleton */}
        <Card className="mb-6">
          <CardHeader>
            <Skeleton className="h-5 w-24" />
          </CardHeader>
          <CardContent>
            <div className="flex gap-4 items-end">
              <Skeleton className="h-10 flex-1" />
              <Skeleton className="h-10 flex-1" />
              <Skeleton className="h-10 w-16" />
            </div>
          </CardContent>
        </Card>

        {/* Summary cards skeleton */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <CardHeader className="pb-2">
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-8 w-32 mt-1" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-3 w-40" />
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Provider stats skeleton */}
        <Card className="mb-6">
          <CardHeader>
            <Skeleton className="h-5 w-32" />
            <Skeleton className="h-4 w-48 mt-1" />
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {[1, 2].map((i) => (
                <div key={i} className="border-b pb-4 last:border-0">
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <Skeleton className="h-5 w-48" />
                      <Skeleton className="h-4 w-36 mt-1" />
                    </div>
                    <Skeleton className="h-7 w-24" />
                  </div>
                  <Skeleton className="h-2 w-full rounded-full" />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="container mx-auto py-6 md:py-8 px-4">
        <div className="mb-8">
          <h1 className="text-3xl md:text-4xl font-bold mb-2">用量统计</h1>
          <p className="text-muted-foreground">跟踪您的生成用量与费用</p>
        </div>
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <div className="w-16 h-16 rounded-full bg-destructive/10 flex items-center justify-center mb-4">
              <AlertCircle className="h-8 w-8 text-destructive" />
            </div>
            <h3 className="text-lg font-semibold mb-2">加载失败</h3>
            <p className="text-sm text-muted-foreground mb-4">{error}</p>
            <Button onClick={loadData} variant="outline" size="sm">
              <RefreshCw className="h-4 w-4 mr-2" />
              重试
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6 md:py-8 px-4">
      <div className="mb-8">
        <h1 className="text-3xl md:text-4xl font-bold mb-2">用量统计</h1>
        <p className="text-muted-foreground">
          跟踪您的生成用量与费用
        </p>
      </div>

      {/* 日期范围 */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-base">日期范围</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 items-stretch sm:items-end">
            <div className="flex-1">
              <label className="block text-sm font-medium mb-2">开始日期</label>
              <input
                type="date"
                className="w-full h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={dateRange.start}
                onChange={(e) => setDateRange({ ...dateRange, start: e.target.value })}
              />
            </div>
            <div className="flex-1">
              <label className="block text-sm font-medium mb-2">结束日期</label>
              <input
                type="date"
                className="w-full h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={dateRange.end}
                onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })}
              />
            </div>
            <Button onClick={loadData} className="sm:w-auto">
              <RefreshCw className="h-4 w-4 mr-2" />
              刷新
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 概览卡片 */}
      {usage && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <Card>
              <CardHeader className="pb-2">
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-green-600" />
                  <CardDescription>总费用</CardDescription>
                </div>
                <CardTitle className="text-2xl md:text-3xl text-green-600">
                  &yen;{usage.summary.total_cost.toFixed(2)}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-muted-foreground">
                  平均：&yen;{usage.summary.average_cost_per_generation.toFixed(4)}/次
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <div className="flex items-center gap-2">
                  <Zap className="h-4 w-4 text-blue-600" />
                  <CardDescription>总生成次数</CardDescription>
                </div>
                <CardTitle className="text-2xl md:text-3xl">{usage.summary.total_generations}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-muted-foreground">
                  日期范围内的生成总数
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <div className="flex items-center gap-2">
                  <Film className="h-4 w-4 text-purple-600" />
                  <CardDescription>总视频时长</CardDescription>
                </div>
                <CardTitle className="text-2xl md:text-3xl">{usage.summary.total_video_duration.toFixed(1)}s</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-muted-foreground">
                  输出视频总时长
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-orange-600" />
                  <CardDescription>总处理时间</CardDescription>
                </div>
                <CardTitle className="text-2xl md:text-3xl">{(usage.summary.total_processing_time / 60).toFixed(1)} 分钟</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-muted-foreground">
                  累计生成耗时
                </p>
              </CardContent>
            </Card>
          </div>

          {/* 按服务商统计 */}
          <Card className="mb-6">
            <CardHeader>
              <CardTitle className="text-base">按服务商统计</CardTitle>
              <CardDescription>各服务商的费用明细</CardDescription>
            </CardHeader>
            <CardContent>
              {usage.by_provider.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">暂无数据</p>
              ) : (
                <div className="space-y-4">
                  {usage.by_provider.map((provider) => (
                    <div key={provider.provider} className="border-b pb-4 last:border-0">
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <h3 className="font-semibold text-sm md:text-base">{providerDisplayName(provider.provider)}</h3>
                          <p className="text-xs md:text-sm text-muted-foreground">
                            {provider.count} 次生成 · {provider.duration.toFixed(1)}s 总时长
                          </p>
                        </div>
                        <div className="text-right">
                          <div className="text-xl md:text-2xl font-bold text-green-600">
                            {currencyLabel(provider.provider)}{provider.cost.toFixed(2)}
                          </div>
                          {provider.duration > 0 && (
                            <p className="text-xs text-muted-foreground">
                              {currencyLabel(provider.provider)}{provider.avg_cost_per_second.toFixed(4)}/秒
                            </p>
                          )}
                        </div>
                      </div>
                      {usage.summary.total_cost > 0 && (
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-green-600 h-2 rounded-full transition-all"
                            style={{
                              width: `${(provider.cost / usage.summary.total_cost) * 100}%`,
                            }}
                          />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* 每日用量 */}
          <Card className="mb-6">
            <CardHeader>
              <CardTitle className="text-base">每日用量</CardTitle>
              <CardDescription>按天统计明细</CardDescription>
            </CardHeader>
            <CardContent>
              {usage.daily.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">暂无数据</p>
              ) : (
                <div className="space-y-2">
                  {usage.daily.slice(-7).reverse().map((day) => (
                    <div key={day.date} className="flex justify-between items-center py-2 border-b last:border-0">
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-sm">{day.date}</div>
                        <div className="text-xs text-muted-foreground">
                          {day.count} 次生成 · {day.success} 成功 · {day.failed} 失败
                        </div>
                      </div>
                      <div className="text-right flex-shrink-0 ml-4">
                        <div className="font-semibold text-green-600 text-sm">&yen;{day.cost.toFixed(2)}</div>
                        <div className="text-xs text-muted-foreground">{day.duration.toFixed(1)}s</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}

      {/* 当前定价 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">当前定价</CardTitle>
          <CardDescription>各服务商与模型的计费标准</CardDescription>
        </CardHeader>
        <CardContent>
          {pricing.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">暂无定价数据</p>
          ) : (
            <div className="space-y-4">
              {pricing.map((price) => (
                <div key={`${price.provider}-${price.model}`} className="border rounded-lg p-4">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h3 className="font-semibold text-sm md:text-base">
                        {providerDisplayName(price.provider)} - {price.model}
                      </h3>
                      {price.pricing_type === 'per_image' && price.per_image ? (
                        <p className="text-xl md:text-2xl font-bold text-green-600 mt-1">
                          {currencyLabel(price.provider)}{price.per_image}/张
                        </p>
                      ) : price.per_second ? (
                        <p className="text-xl md:text-2xl font-bold text-green-600 mt-1">
                          {currencyLabel(price.provider)}{price.per_second}/秒
                        </p>
                      ) : null}
                    </div>
                    <span className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-600 flex-shrink-0">
                      {price.currency === 'CNY' ? '人民币' : '美元'}
                    </span>
                  </div>

                  {price.pricing_type === 'per_image' ? (
                    <div className="text-sm text-muted-foreground">
                      按张计费，每张图片 {currencyLabel(price.provider)}{price.per_image}
                    </div>
                  ) : price.examples ? (
                    <div className="grid grid-cols-3 gap-3 md:gap-4 text-sm">
                      <div className="text-center p-2 bg-gray-50 rounded">
                        <div className="text-muted-foreground text-xs">5 秒</div>
                        <div className="font-semibold">{currencyLabel(price.provider)}{price.examples["5_seconds"]}</div>
                      </div>
                      <div className="text-center p-2 bg-gray-50 rounded">
                        <div className="text-muted-foreground text-xs">10 秒</div>
                        <div className="font-semibold">{currencyLabel(price.provider)}{price.examples["10_seconds"]}</div>
                      </div>
                      <div className="text-center p-2 bg-gray-50 rounded">
                        <div className="text-muted-foreground text-xs">20 秒</div>
                        <div className="font-semibold">{currencyLabel(price.provider)}{price.examples["20_seconds"]}</div>
                      </div>
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
