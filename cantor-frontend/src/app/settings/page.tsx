'use client';

import { useState } from 'react';
import DashboardLayout from '@/components/DashboardLayout';
import { User, Building, Key, Bell, Shield, Database } from 'lucide-react';

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('profile');

  const tabs = [
    { id: 'profile', label: '个人资料', icon: User },
    { id: 'org', label: '组织设置', icon: Building },
    { id: 'api', label: 'API 密钥', icon: Key },
    { id: 'notifications', label: '通知设置', icon: Bell },
    { id: 'security', label: '安全设置', icon: Shield },
    { id: 'data', label: '数据管理', icon: Database },
  ];

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* 头部 */}
        <div>
          <h1 className="text-2xl font-bold text-gray-900">设置</h1>
          <p className="text-gray-500 mt-1">管理你的账号和系统设置</p>
        </div>

        <div className="flex gap-6">
          {/* 侧边导航 */}
          <div className="w-48 flex-shrink-0">
            <nav className="space-y-1">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left transition ${
                      activeTab === tab.id
                        ? 'bg-blue-50 text-blue-600'
                        : 'text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    <Icon size={18} />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </nav>
          </div>

          {/* 内容区 */}
          <div className="flex-1 bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            {activeTab === 'profile' && (
              <div className="space-y-6">
                <h2 className="text-lg font-semibold">个人资料</h2>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">姓名</label>
                    <input
                      type="text"
                      defaultValue="Bill"
                      className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">邮箱</label>
                    <input
                      type="email"
                      defaultValue="bill@example.com"
                      className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">时区</label>
                  <select className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none">
                    <option>Asia/Shanghai (GMT+8)</option>
                    <option>UTC (GMT+0)</option>
                  </select>
                </div>
                <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition">
                  保存更改
                </button>
              </div>
            )}

            {activeTab === 'org' && (
              <div className="space-y-6">
                <h2 className="text-lg font-semibold">组织设置</h2>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">组织名称</label>
                    <input
                      type="text"
                      defaultValue="Bill Company"
                      className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">组织标识</label>
                    <input
                      type="text"
                      defaultValue="bill-co"
                      disabled
                      className="w-full px-4 py-2 border border-gray-200 rounded-lg bg-gray-50 text-gray-500"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">套餐</label>
                  <div className="flex items-center gap-4">
                    <span className="px-3 py-1 bg-blue-100 text-blue-600 rounded-full text-sm">企业版</span>
                    <span className="text-gray-500">设备上限: 100 台</span>
                  </div>
                </div>
                <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition">
                  保存更改
                </button>
              </div>
            )}

            {activeTab === 'api' && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold">API 密钥</h2>
                  <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition text-sm">
                    创建新密钥
                  </button>
                </div>
                <div className="border border-gray-200 rounded-lg divide-y">
                  <div className="p-4 flex items-center justify-between">
                    <div>
                      <p className="font-medium">cantor_xxxx...xxxx</p>
                      <p className="text-sm text-gray-500">创建于 2026-03-01</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs bg-green-100 text-green-600 px-2 py-1 rounded">活跃</span>
                      <button className="text-red-600 hover:underline text-sm">撤销</button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'security' && (
              <div className="space-y-6">
                <h2 className="text-lg font-semibold">安全设置</h2>
                <div className="space-y-4">
                  <div>
                    <h3 className="font-medium mb-2">修改密码</h3>
                    <div className="grid grid-cols-2 gap-4">
                      <input
                        type="password"
                        placeholder="当前密码"
                        className="px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                      />
                      <div></div>
                      <input
                        type="password"
                        placeholder="新密码"
                        className="px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                      />
                      <input
                        type="password"
                        placeholder="确认新密码"
                        className="px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                      />
                    </div>
                  </div>
                  <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition">
                    更新密码
                  </button>
                </div>
              </div>
            )}

            {activeTab === 'notifications' && (
              <div className="space-y-6">
                <h2 className="text-lg font-semibold">通知设置</h2>
                <div className="space-y-4">
                  {['任务完成通知', '任务失败通知', '设备离线通知', '系统更新通知'].map((item) => (
                    <label key={item} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                      <span>{item}</span>
                      <input type="checkbox" defaultChecked className="w-5 h-5" />
                    </label>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'data' && (
              <div className="space-y-6">
                <h2 className="text-lg font-semibold">数据管理</h2>
                <div className="space-y-4">
                  <div className="p-4 bg-gray-50 rounded-lg flex items-center justify-between">
                    <div>
                      <p className="font-medium">导出数据</p>
                      <p className="text-sm text-gray-500">导出所有任务和设备数据</p>
                    </div>
                    <button className="border border-gray-200 px-4 py-2 rounded-lg hover:bg-white transition">
                      导出
                    </button>
                  </div>
                  <div className="p-4 bg-red-50 rounded-lg flex items-center justify-between">
                    <div>
                      <p className="font-medium text-red-600">删除所有数据</p>
                      <p className="text-sm text-red-400">此操作不可恢复</p>
                    </div>
                    <button className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition">
                      删除
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
