'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/store';
import DashboardLayout from '@/components/DashboardLayout';
import { Bot, Smartphone, ListTodo, Activity, TrendingUp } from 'lucide-react';
import { api } from '@/lib/api';

interface DashboardStats {
  cantorCount: number;
  onlineDevices: number;
  runningTasks: number;
  successRate: string;
}

interface Task {
  id: string;
  name: string;
  status: 'running' | 'completed' | 'pending' | 'failed';
  progress: number;
}

interface Device {
  id: string;
  name: string;
  status: 'online' | 'idle' | 'offline';
  currentTask?: string;
}

export default function HomePage() {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentTasks, setRecentTasks] = useState<Task[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }

    // 获取真实数据
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        // 并行获取统计数据、任务列表、设备列表
        const [statsRes, tasksRes, devicesRes] = await Promise.all([
          api.get('/dashboard/stats').catch(() => null),
          api.get('/tasks?limit=5').catch(() => null),
          api.get('/devices?limit=5').catch(() => null),
        ]);

        if (statsRes?.data) {
          setStats(statsRes.data);
        }
        if (tasksRes?.data?.items) {
          setRecentTasks(tasksRes.data.items);
        }
        if (devicesRes?.data?.items) {
          setDevices(devicesRes.data.items);
        }
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
    // 每30秒刷新一次
    const interval = setInterval(fetchDashboardData, 30000);
    return () => clearInterval(interval);
  }, [isAuthenticated, router]);

  if (!isAuthenticated) {
    return null;
  }

  const statCards = [
    { label: 'Cantor 实例', value: stats?.cantorCount ?? '-', icon: Bot, color: 'bg-blue-500' },
    { label: '在线设备', value: stats?.onlineDevices ?? '-', icon: Smartphone, color: 'bg-green-500' },
    { label: '执行中任务', value: stats?.runningTasks ?? '-', icon: ListTodo, color: 'bg-orange-500' },
    { label: '成功率', value: stats?.successRate ?? '-', icon: TrendingUp, color: 'bg-purple-500' },
  ];

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* 页面标题 */}
        <div>
          <h1 className="text-2xl font-bold text-gray-900">概览</h1>
          <p className="text-gray-500 mt-1">Cantor 云手机调度平台运行状态</p>
        </div>

        {/* 统计卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {statCards.map((stat) => {
            const Icon = stat.icon;
            return (
              <div
                key={stat.label}
                className="bg-white rounded-xl p-6 shadow-sm border border-gray-100"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">{stat.label}</p>
                    <p className="text-3xl font-bold text-gray-900 mt-1">
                      {loading && stat.value === '-' ? (
                        <span className="animate-pulse">...</span>
                      ) : (
                        stat.value
                      )}
                    </p>
                  </div>
                  <div className={`p-3 rounded-lg ${stat.color}`}>
                    <Icon className="w-6 h-6 text-white" />
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 最近任务 */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100">
            <div className="p-4 border-b border-gray-100 flex items-center justify-between">
              <h2 className="font-semibold text-gray-900">最近任务</h2>
              <a href="/tasks" className="text-sm text-blue-600 hover:text-blue-700">查看全部</a>
            </div>
            <div className="divide-y divide-gray-100">
              {loading ? (
                <div className="p-8 text-center text-gray-400">加载中...</div>
              ) : recentTasks.length === 0 ? (
                <div className="p-8 text-center text-gray-400">暂无任务</div>
              ) : (
                recentTasks.map((task) => (
                  <div key={task.id} className="p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium text-gray-900">{task.name}</span>
                      <span
                        className={`text-xs px-2 py-1 rounded-full ${
                          task.status === 'completed'
                            ? 'bg-green-100 text-green-600'
                            : task.status === 'running'
                            ? 'bg-blue-100 text-blue-600'
                            : task.status === 'failed'
                            ? 'bg-red-100 text-red-600'
                            : 'bg-gray-100 text-gray-600'
                        }`}
                      >
                        {task.status === 'completed'
                          ? '已完成'
                          : task.status === 'running'
                          ? '执行中'
                          : task.status === 'failed'
                          ? '失败'
                          : '等待中'}
                      </span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full ${
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
                ))
              )}
            </div>
          </div>

          {/* 设备状态 */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100">
            <div className="p-4 border-b border-gray-100 flex items-center justify-between">
              <h2 className="font-semibold text-gray-900">设备状态</h2>
              <a href="/devices" className="text-sm text-blue-600 hover:text-blue-700">查看全部</a>
            </div>
            <div className="divide-y divide-gray-100">
              {loading ? (
                <div className="p-8 text-center text-gray-400">加载中...</div>
              ) : devices.length === 0 ? (
                <div className="p-8 text-center text-gray-400">暂无设备</div>
              ) : (
                devices.map((device) => (
                  <div key={device.id} className="p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-2 h-2 rounded-full ${
                          device.status === 'online'
                            ? 'bg-green-500'
                            : device.status === 'idle'
                            ? 'bg-yellow-500'
                            : 'bg-gray-300'
                        }`}
                      />
                      <div>
                        <p className="font-medium text-gray-900">{device.name}</p>
                        <p className="text-sm text-gray-500">{device.id}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-gray-600">{device.currentTask || '-'}</p>
                      <p
                        className={`text-xs ${
                          device.status === 'online'
                            ? 'text-green-600'
                            : device.status === 'idle'
                            ? 'text-yellow-600'
                            : 'text-gray-400'
                        }`}
                      >
                        {device.status === 'online'
                          ? '在线'
                          : device.status === 'idle'
                          ? '空闲'
                          : '离线'}
                      </p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* 系统状态 */}
        <div className="bg-gradient-to-r from-blue-500 to-indigo-600 rounded-xl p-6 text-white">
          <div className="flex items-center gap-3 mb-4">
            <Activity className="w-6 h-6" />
            <h2 className="font-semibold text-lg">系统状态</h2>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-blue-100 text-sm">Gateway</p>
              <p className="font-semibold flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-green-400"></span>
                运行中
              </p>
            </div>
            <div>
              <p className="text-blue-100 text-sm">Brain</p>
              <p className="font-semibold flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-green-400"></span>
                运行中
              </p>
            </div>
            <div>
              <p className="text-blue-100 text-sm">PostgreSQL</p>
              <p className="font-semibold flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-green-400"></span>
                运行中
              </p>
            </div>
            <div>
              <p className="text-blue-100 text-sm">Redis</p>
              <p className="font-semibold flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-green-400"></span>
                运行中
              </p>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
