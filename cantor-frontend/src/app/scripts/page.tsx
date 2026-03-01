'use client';

import { useState } from 'react';
import DashboardLayout from '@/components/DashboardLayout';
import { FileCode, Search, Plus, Play, Edit, Trash2, Copy } from 'lucide-react';

const mockScripts = [
  { id: 'script-001', name: '抖音点赞脚本', version: '1.2.0', apps: ['抖音'], uses: 1250, status: 'active' },
  { id: 'script-002', name: '小红书评论采集', version: '2.0.1', apps: ['小红书'], uses: 890, status: 'active' },
  { id: 'script-003', name: '微信消息发送', version: '1.0.5', apps: ['微信'], uses: 456, status: 'active' },
  { id: 'script-004', name: '微博转发脚本', version: '0.9.0', apps: ['微博'], uses: 123, status: 'draft' },
  { id: 'script-005', name: 'B站点赞脚本', version: '1.1.0', apps: ['B站'], uses: 678, status: 'active' },
];

export default function ScriptsPage() {
  const [search, setSearch] = useState('');

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* 头部 */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">脚本库</h1>
            <p className="text-gray-500 mt-1">Script Forge 生成的快引擎脚本</p>
          </div>
          <button className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition">
            <Plus size={20} />
            <span>新建脚本</span>
          </button>
        </div>

        {/* 搜索 */}
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="搜索脚本..."
            className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
          />
        </div>

        {/* 脚本列表 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {mockScripts.map((script) => (
            <div
              key={script.id}
              className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 hover:shadow-md transition"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-purple-100 rounded-lg">
                    <FileCode className="w-5 h-5 text-purple-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">{script.name}</h3>
                    <p className="text-xs text-gray-500">v{script.version}</p>
                  </div>
                </div>
                <span
                  className={`text-xs px-2 py-1 rounded-full ${
                    script.status === 'active'
                      ? 'bg-green-100 text-green-600'
                      : 'bg-gray-100 text-gray-600'
                  }`}
                >
                  {script.status === 'active' ? '启用' : '草稿'}
                </span>
              </div>

              <div className="flex flex-wrap gap-1 mb-3">
                {script.apps.map((app) => (
                  <span key={app} className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
                    {app}
                  </span>
                ))}
              </div>

              <div className="flex items-center justify-between text-sm text-gray-500 mb-4">
                <span>使用次数</span>
                <span className="font-medium text-gray-900">{script.uses.toLocaleString()}</span>
              </div>

              <div className="flex items-center gap-2 pt-3 border-t border-gray-100">
                <button className="flex-1 flex items-center justify-center gap-1 py-2 text-blue-600 hover:bg-blue-50 rounded-lg transition">
                  <Play size={16} />
                  <span>测试</span>
                </button>
                <button className="flex-1 flex items-center justify-center gap-1 py-2 text-gray-600 hover:bg-gray-50 rounded-lg transition">
                  <Edit size={16} />
                  <span>编辑</span>
                </button>
                <button className="p-2 text-gray-400 hover:bg-gray-50 rounded-lg transition">
                  <Copy size={16} />
                </button>
                <button className="p-2 text-red-400 hover:bg-red-50 rounded-lg transition">
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </DashboardLayout>
  );
}
