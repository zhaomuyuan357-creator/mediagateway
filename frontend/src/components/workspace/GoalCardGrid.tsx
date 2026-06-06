/**
 * GoalCardGrid.tsx — 业务目标模板选择网格
 *
 * 功能：
 *   - 展示预设目标卡片（电商主图 / 产品详情 / 社交媒体 / 广告Banner / 节日主题）
 *   - 点击切换选中状态
 *   - 通过 store.setSelectedTemplate() 更新状态
 */

import { useTaskStore, type Template } from '../../lib/store';

// 预设目标模板
const PRESET_TEMPLATES: Template[] = [
  {
    id: 'ecommerce-hero',
    name: '电商主图',
    description: '适配淘宝/京东等平台主图规格，突出产品卖点',
  },
  {
    id: 'product-detail',
    name: '产品详情页',
    description: '多角度展示产品细节，提升转化率',
  },
  {
    id: 'social-media',
    name: '社交媒体图',
    description: '适配小红书/抖音等平台尺寸，吸睛封面',
  },
  {
    id: 'ad-banner',
    name: '广告Banner',
    description: '高点击率广告素材，适配信息流投放',
  },
  {
    id: 'holiday-theme',
    name: '节日活动主题',
    description: '节日促销氛围设计，营造活动感',
  },
];

export function GoalCardGrid() {
  const { selectedTemplate, setSelectedTemplate } = useTaskStore();

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-slate-300">选择商业目标</h3>
        {selectedTemplate && (
          <span className="text-xs text-blue-400">已选：{selectedTemplate.name}</span>
        )}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {PRESET_TEMPLATES.map((template) => {
          const isSelected = selectedTemplate?.id === template.id;

          return (
            <button
              key={template.id}
              onClick={() => setSelectedTemplate(template)}
              className={`
                relative rounded-xl p-4 text-left transition-all duration-200
                ${
                  isSelected
                    ? 'bg-blue-600/20 border-2 border-blue-500 shadow-lg shadow-blue-500/10'
                    : 'bg-slate-900/40 border border-slate-700/50 hover:border-slate-600 hover:bg-slate-800/40'
                }
              `}
            >
              {/* 选中标记 */}
              {isSelected && (
                <div className="absolute top-2 right-2 w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center">
                  <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                </div>
              )}

              <p
                className={`text-sm font-medium ${
                  isSelected ? 'text-blue-300' : 'text-white'
                }`}
              >
                {template.name}
              </p>
              <p
                className={`text-xs mt-1 leading-relaxed ${
                  isSelected ? 'text-blue-400/70' : 'text-slate-500'
                }`}
              >
                {template.description}
              </p>
            </button>
          );
        })}
      </div>
    </div>
  );
}
