'use client';

import { useState } from 'react';
import DashboardLayout from '@/components/DashboardLayout';
import { Plus, Search, MoreVertical, Bot, Power, Trash2 } from 'lucide-react';

const mockCantors = [
  {
    id: 'cantor-001',
    name: '抖音点赞助手',
    model: 'GPT-4o',
    devices: 50,
    status: 'running',
    tasks: 12,
  },
  {
    id: 'cantor-002',
    name: '小红书采集器',
    model: 'Claude-3',
    devices: 30,
    status: 'paused',
    tasks: 5,
  },
  {
    id: 'cantor-003',
    name: '微信营销助手',
    model: 'Qwen-Max',
    devices: 20,
    status: 'stopped',
    tasks: 0,
  },
];

export default function CantorsPage() {
  const [search, setSearch] = useState('');

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* 头部 */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Cantor 实例</h1>
            <p className="text-gray-500 mt-1">管理你的智能调度大脑</p>
          </div>
          <button className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition">
            <Plus size={20} />
            <span>创建实例</span>
          </button>
        </div>

        {/* 搜索 */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="搜索 Cantor 实例..."
            className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
          />
        </div>

        {/* 列表 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {mockCantors.map((cantor) => (
            <div
              key={cantor.id}
              className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 hover:shadow-md transition"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-blue-100 rounded-lg">
                    <Bot className="w-6 h-6 text-blue-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">{cantor.name}</h3>
                    <p className="text-sm text-gray-500">{cantor.id}</p>
                  </div>
                </div>
                <button className="p-1 hover:bg-gray-100 rounded">
                  <MoreVertical size={20} className="text-gray-400" />
                </button>
              </div>

              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">模型</span>
                  <span className="font-medium">{cantor.model}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">绑定设备</span>
                  <span className="font-medium">{cantor.devices} 台</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">执行任务</span>
                  <span className="font-medium">{cantor.tasks} 个</span>
                </div>
              </div>

              <div className="mt-4 pt-4 border-t border-gray-100 flex items-center justify-between">
                <span
                  className={`text-xs px-2 py-1 rounded-full ${
                    cantor.status === 'running'
                      ? 'bg-green-100 text-green-600'
                      : cantor.status === 'paused'
                      ? 'bg-yellow-100 text-yellow-600'
                      : 'bg-gray-100 text-gray-600'
                  }`}
                >
                  {cantor.status === 'running' ? '运行中' : cantor.status === 'paused' ? '已暂停' : '已停止'}
                </span>
                <div className="flex items-center gap-2">
                  <button className="p-2 hover:bg-gray-100 rounded-lg">
                    <Power size={18} className="text-gray-600" />
                  </button>
                  <button className="p-2 hover:bg-red-50 rounded-lg">
                    <Trash2 size={18} className="text-red-500" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </DashboardLayout>
  );
}
