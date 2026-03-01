'use client';

import { useState } from 'react';
import DashboardLayout from '@/components/DashboardLayout';
import { Smartphone, Search, RefreshCw, MoreVertical, Wifi, WifiOff, Pause } from 'lucide-react';

const mockDevices = Array.from({ length: 10 }, (_, i) => ({
  id: `device-${String(i + 1).padStart(3, '0')}`,
  name: `云手机 #${i + 1}`,
  status: i < 6 ? 'online' : i < 8 ? 'idle' : 'offline',
  cantor: i < 6 ? '抖音点赞助手' : '-',
  task: i < 6 ? '点赞任务 #1024' : '-',
  lastSeen: '刚刚',
  ip: `192.168.1.${100 + i}`,
}));

export default function DevicesPage() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  const filteredDevices = mockDevices.filter((device) => {
    const matchesSearch = device.name.includes(search) || device.id.includes(search);
    const matchesStatus = statusFilter === 'all' || device.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* 头部 */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">设备舰队</h1>
            <p className="text-gray-500 mt-1">管理所有云手机设备</p>
          </div>
          <button className="flex items-center gap-2 border border-gray-200 px-4 py-2 rounded-lg hover:bg-gray-50 transition">
            <RefreshCw size={20} />
            <span>刷新状态</span>
          </button>
        </div>

        {/* 统计 */}
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-100 rounded-lg">
                <Wifi className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">在线</p>
                <p className="text-xl font-bold">6</p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-yellow-100 rounded-lg">
                <Pause className="w-5 h-5 text-yellow-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">空闲</p>
                <p className="text-xl font-bold">2</p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-gray-100 rounded-lg">
                <WifiOff className="w-5 h-5 text-gray-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">离线</p>
                <p className="text-xl font-bold">2</p>
              </div>
            </div>
          </div>
        </div>

        {/* 筛选 */}
        <div className="flex items-center gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="搜索设备..."
              className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-4 py-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
          >
            <option value="all">全部状态</option>
            <option value="online">在线</option>
            <option value="idle">空闲</option>
            <option value="offline">离线</option>
          </select>
        </div>

        {/* 设备列表 */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-500">设备</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-500">状态</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-500">Cantor</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-500">当前任务</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-500">IP 地址</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-500">最后活跃</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredDevices.map((device) => (
                <tr key={device.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <Smartphone className="w-5 h-5 text-gray-400" />
                      <div>
                        <p className="font-medium text-gray-900">{device.name}</p>
                        <p className="text-sm text-gray-500">{device.id}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full ${
                        device.status === 'online'
                          ? 'bg-green-100 text-green-600'
                          : device.status === 'idle'
                          ? 'bg-yellow-100 text-yellow-600'
                          : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      <span
                        className={`w-1.5 h-1.5 rounded-full ${
                          device.status === 'online'
                            ? 'bg-green-500'
                            : device.status === 'idle'
                            ? 'bg-yellow-500'
                            : 'bg-gray-400'
                        }`}
                      />
                      {device.status === 'online' ? '在线' : device.status === 'idle' ? '空闲' : '离线'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{device.cantor}</td>
                  <td className="px-4 py-3 text-gray-600">{device.task}</td>
                  <td className="px-4 py-3 text-gray-500 text-sm">{device.ip}</td>
                  <td className="px-4 py-3 text-gray-500 text-sm">{device.lastSeen}</td>
                  <td className="px-4 py-3">
                    <button className="p-1 hover:bg-gray-100 rounded">
                      <MoreVertical size={18} className="text-gray-400" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </DashboardLayout>
  );
}
