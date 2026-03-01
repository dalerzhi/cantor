'use client';

import DashboardLayout from '@/components/DashboardLayout';
import { Search, Filter, CheckCircle, Clock, XCircle, Loader2 } from 'lucide-react';

const mockTasks = [
  { id: 'task-001', name: '抖音点赞任务 #1024', cantor: '抖音点赞助手', status: 'running', progress: 75, devices: 50, completed: 38 },
  { id: 'task-002', name: '小红书评论采集 #512', cantor: '小红书采集器', status: 'completed', progress: 100, devices: 30, completed: 30 },
  { id: 'task-003', name: '微信消息群发 #256', cantor: '微信营销助手', status: 'pending', progress: 0, devices: 20, completed: 0 },
  { id: 'task-004', name: '抖音直播监控 #128', cantor: '抖音点赞助手', status: 'failed', progress: 30, devices: 10, completed: 3 },
  { id: 'task-005', name: '微博转发任务 #64', cantor: '微博助手', status: 'running', progress: 45, devices: 15, completed: 7 },
];

export default function TasksPage() {
  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* 头部 */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">任务监控</h1>
            <p className="text-gray-500 mt-1">查看所有任务执行状态</p>
          </div>
        </div>

        {/* 筛选 */}
        <div className="flex items-center gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
            <input
              type="text"
              placeholder="搜索任务..."
              className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
            />
          </div>
          <button className="flex items-center gap-2 border border-gray-200 px-4 py-2 rounded-lg hover:bg-gray-50">
            <Filter size={18} />
            <span>筛选</span>
          </button>
        </div>

        {/* 任务列表 */}
        <div className="space-y-4">
          {mockTasks.map((task) => (
            <div key={task.id} className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  {task.status === 'completed' ? (
                    <CheckCircle className="w-6 h-6 text-green-500" />
                  ) : task.status === 'running' ? (
                    <Loader2 className="w-6 h-6 text-blue-500 animate-spin" />
                  ) : task.status === 'failed' ? (
                    <XCircle className="w-6 h-6 text-red-500" />
                  ) : (
                    <Clock className="w-6 h-6 text-gray-400" />
                  )}
                  <div>
                    <h3 className="font-semibold text-gray-900">{task.name}</h3>
                    <p className="text-sm text-gray-500">{task.cantor}</p>
                  </div>
                </div>
                <span
                  className={`text-xs px-3 py-1 rounded-full ${
                    task.status === 'completed'
                      ? 'bg-green-100 text-green-600'
                      : task.status === 'running'
                      ? 'bg-blue-100 text-blue-600'
                      : task.status === 'failed'
                      ? 'bg-red-100 text-red-600'
                      : 'bg-gray-100 text-gray-600'
                  }`}
                >
                  {task.status === 'completed' ? '已完成' : task.status === 'running' ? '执行中' : task.status === 'failed' ? '失败' : '等待中'}
                </span>
              </div>

              <div className="mb-3">
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className="text-gray-500">进度</span>
                  <span className="font-medium">{task.completed}/{task.devices} 设备</span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all ${
                      task.status === 'completed'
                        ? 'bg-green-500'
                        : task.status === 'failed'
                        ? 'bg-red-500'
                        : 'bg-blue-500'
                    }`}
                    style={{ width: `${task.progress}%` }}
                  />
                </div>
              </div>

              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-500">ID: {task.id}</span>
                <button className="text-blue-600 hover:underline">查看详情</button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </DashboardLayout>
  );
}
