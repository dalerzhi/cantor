'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/store';
import DashboardLayout from '@/components/DashboardLayout';
import { 
  Smartphone, 
  RefreshCw, 
  Play, 
  Square, 
  RotateCcw,
  Server,
  Layers,
  Monitor,
  AlertCircle,
  CheckCircle,
  XCircle,
  Clock,
  ChevronRight
} from 'lucide-react';

interface CloudPhoneSummary {
  total: number;
  running: number;
  stopped: number;
  creating: number;
  error: number;
}

interface NodeDistribution {
  node_name: string;
  total: number;
  running: number;
  stopped: number;
  cards: number;
}

interface ProjectDistribution {
  project_name: string;
  project_id: string;
  total: number;
  running: number;
  stopped: number;
  cards: number;
}

interface CloudPhoneDashboard {
  summary: CloudPhoneSummary;
  nodes: NodeDistribution[];
  projects: ProjectDistribution[];
  last_synced: string | null;
}

interface CloudPhone {
  id: string;
  name: string;
  ip: string | null;
  project_name: string;
  node_name: string | null;
  card_sn: string | null;
  status: number;
  status_text: string;
  resolution: string | null;
  synced_at: string;
}

export default function CloudPhonesPage() {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const [dashboard, setDashboard] = useState<CloudPhoneDashboard | null>(null);
  const [phones, setPhones] = useState<CloudPhone[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [selectedProject, setSelectedProject] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<number | null>(null);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated) {
      fetchDashboard();
      fetchPhones();
    }
  }, [isAuthenticated, selectedProject, selectedNode, statusFilter]);

  const fetchDashboard = async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch('http://localhost:8000/api/cloud-phones/dashboard', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (res.ok) {
        const data = await res.json();
        setDashboard(data);
      }
    } catch (error) {
      console.error('Failed to fetch dashboard:', error);
    }
  };

  const fetchPhones = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const params = new URLSearchParams();
      if (selectedProject) params.append('project_id', selectedProject);
      if (selectedNode) params.append('node_name', selectedNode);
      if (statusFilter !== null) params.append('status', statusFilter.toString());
      params.append('page', '1');
      params.append('page_size', '100');

      const res = await fetch(`http://localhost:8000/api/cloud-phones?${params}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (res.ok) {
        const data = await res.json();
        setPhones(data);
      }
    } catch (error) {
      console.error('Failed to fetch phones:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    try {
      setSyncing(true);
      setSyncMessage(null);
      const token = localStorage.getItem('token');
      const res = await fetch('http://localhost:8000/api/cloud-phones/sync', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (res.ok) {
        const data = await res.json();
        setSyncMessage(data.message);
        fetchDashboard();
        fetchPhones();
      } else {
        const error = await res.json();
        setSyncMessage(`同步失败: ${error.detail}`);
      }
    } catch (error) {
      setSyncMessage('同步失败，请检查网络连接');
    } finally {
      setSyncing(false);
    }
  };

  const handleAction = async (phoneId: string, action: 'start' | 'stop' | 'restart') => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`http://localhost:8000/api/cloud-phones/${phoneId}/${action}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (res.ok) {
        // 刷新列表
        setTimeout(() => fetchPhones(), 2000);
      }
    } catch (error) {
      console.error('Action failed:', error);
    }
  };

  const getStatusIcon = (status: number) => {
    switch (status) {
      case 1:
      case 4:
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 2:
        return <Square className="w-4 h-4 text-gray-400" />;
      case 0:
        return <Clock className="w-4 h-4 text-yellow-500" />;
      case 3:
        return <XCircle className="w-4 h-4 text-red-500" />;
      default:
        return <AlertCircle className="w-4 h-4 text-gray-400" />;
    }
  };

  const getStatusColor = (status: number) => {
    switch (status) {
      case 1:
      case 4:
        return 'bg-green-100 text-green-600';
      case 2:
        return 'bg-gray-100 text-gray-600';
      case 0:
        return 'bg-yellow-100 text-yellow-600';
      case 3:
        return 'bg-red-100 text-red-600';
      default:
        return 'bg-gray-100 text-gray-600';
    }
  };

  if (!isAuthenticated) {
    return null;
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* 页面标题 */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">云手机管理</h1>
            <p className="text-gray-500 mt-1">从 IaaS 平台同步和管理云手机实例</p>
          </div>
          <button
            onClick={handleSync}
            disabled={syncing}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
            {syncing ? '同步中...' : '同步云手机'}
          </button>
        </div>

        {/* 同步消息 */}
        {syncMessage && (
          <div className={`p-4 rounded-lg ${syncMessage.includes('成功') ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
            {syncMessage}
          </div>
        )}

        {/* 统计卡片 */}
        {dashboard && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
              <div className="flex items-center gap-2 text-gray-500 mb-1">
                <Smartphone className="w-4 h-4" />
                <span className="text-sm">总实例</span>
              </div>
              <p className="text-2xl font-bold text-gray-900">{dashboard.summary.total}</p>
            </div>
            <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
              <div className="flex items-center gap-2 text-green-500 mb-1">
                <CheckCircle className="w-4 h-4" />
                <span className="text-sm">运行中</span>
              </div>
              <p className="text-2xl font-bold text-green-600">{dashboard.summary.running}</p>
            </div>
            <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
              <div className="flex items-center gap-2 text-gray-400 mb-1">
                <Square className="w-4 h-4" />
                <span className="text-sm">已关机</span>
              </div>
              <p className="text-2xl font-bold text-gray-600">{dashboard.summary.stopped}</p>
            </div>
            <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
              <div className="flex items-center gap-2 text-yellow-500 mb-1">
                <Clock className="w-4 h-4" />
                <span className="text-sm">创建中</span>
              </div>
              <p className="text-2xl font-bold text-yellow-600">{dashboard.summary.creating}</p>
            </div>
            <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
              <div className="flex items-center gap-2 text-red-500 mb-1">
                <XCircle className="w-4 h-4" />
                <span className="text-sm">异常</span>
              </div>
              <p className="text-2xl font-bold text-red-600">{dashboard.summary.error}</p>
            </div>
          </div>
        )}

        {/* 分布信息 */}
        {dashboard && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 节点分布 */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100">
              <div className="p-4 border-b border-gray-100 flex items-center gap-2">
                <Server className="w-5 h-5 text-gray-500" />
                <h2 className="font-semibold text-gray-900">节点分布</h2>
              </div>
              <div className="divide-y divide-gray-100">
                {dashboard.nodes.length > 0 ? (
                  dashboard.nodes.map((node) => (
                    <div 
                      key={node.node_name}
                      className="p-4 flex items-center justify-between cursor-pointer hover:bg-gray-50"
                      onClick={() => setSelectedNode(selectedNode === node.node_name ? null : node.node_name)}
                    >
                      <div className="flex items-center gap-3">
                        <Monitor className="w-5 h-5 text-gray-400" />
                        <div>
                          <p className="font-medium text-gray-900">{node.node_name}</p>
                          <p className="text-sm text-gray-500">{node.cards} 张板卡</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-4 text-sm">
                        <span className="text-gray-600">共 {node.total}</span>
                        <span className="text-green-600">{node.running} 运行</span>
                        <span className="text-gray-400">{node.stopped} 关机</span>
                        <ChevronRight className="w-4 h-4 text-gray-400" />
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="p-8 text-center text-gray-500">
                    暂无节点数据，请先同步
                  </div>
                )}
              </div>
            </div>

            {/* 项目分布 */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100">
              <div className="p-4 border-b border-gray-100 flex items-center gap-2">
                <Layers className="w-5 h-5 text-gray-500" />
                <h2 className="font-semibold text-gray-900">项目分布</h2>
              </div>
              <div className="divide-y divide-gray-100">
                {dashboard.projects.length > 0 ? (
                  dashboard.projects.map((project) => (
                    <div 
                      key={project.project_id}
                      className="p-4 flex items-center justify-between cursor-pointer hover:bg-gray-50"
                      onClick={() => setSelectedProject(selectedProject === project.project_id ? null : project.project_id)}
                    >
                      <div className="flex items-center gap-3">
                        <Layers className="w-5 h-5 text-gray-400" />
                        <div>
                          <p className="font-medium text-gray-900">{project.project_name}</p>
                          <p className="text-sm text-gray-500">{project.cards} 张板卡</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-4 text-sm">
                        <span className="text-gray-600">共 {project.total}</span>
                        <span className="text-green-600">{project.running} 运行</span>
                        <span className="text-gray-400">{project.stopped} 关机</span>
                        <ChevronRight className="w-4 h-4 text-gray-400" />
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="p-8 text-center text-gray-500">
                    暂无项目数据，请先同步
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* 过滤器 */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">状态:</span>
            <select
              value={statusFilter ?? ''}
              onChange={(e) => setStatusFilter(e.target.value ? parseInt(e.target.value) : null)}
              className="px-3 py-1 border rounded-lg text-sm"
            >
              <option value="">全部</option>
              <option value="1">运行中</option>
              <option value="2">已关机</option>
              <option value="0">创建中</option>
              <option value="3">异常</option>
            </select>
          </div>
          {(selectedProject || selectedNode || statusFilter !== null) && (
            <button
              onClick={() => {
                setSelectedProject(null);
                setSelectedNode(null);
                setStatusFilter(null);
              }}
              className="text-sm text-blue-600 hover:text-blue-700"
            >
              清除过滤
            </button>
          )}
          {dashboard?.last_synced && (
            <span className="text-sm text-gray-400 ml-auto">
              上次同步: {new Date(dashboard.last_synced).toLocaleString()}
            </span>
          )}
        </div>

        {/* 实例列表 */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="p-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-900">实例列表 ({phones.length})</h2>
          </div>
          {loading ? (
            <div className="p-8 text-center text-gray-500">加载中...</div>
          ) : phones.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">名称</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">项目</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">节点</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">IP</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">板卡</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">分辨率</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">状态</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">操作</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {phones.map((phone) => (
                    <tr key={phone.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <Smartphone className="w-4 h-4 text-gray-400" />
                          <span className="font-medium text-gray-900">{phone.name}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">{phone.project_name}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{phone.node_name || '-'}</td>
                      <td className="px-4 py-3 text-sm text-gray-600 font-mono">{phone.ip || '-'}</td>
                      <td className="px-4 py-3 text-sm text-gray-600 font-mono">{phone.card_sn?.slice(-8) || '-'}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{phone.resolution || '-'}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs ${getStatusColor(phone.status)}`}>
                          {getStatusIcon(phone.status)}
                          {phone.status_text}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1">
                          {phone.status === 2 && (
                            <button
                              onClick={() => handleAction(phone.id, 'start')}
                              className="p-1 text-green-600 hover:bg-green-50 rounded"
                              title="启动"
                            >
                              <Play className="w-4 h-4" />
                            </button>
                          )}
                          {(phone.status === 1 || phone.status === 4) && (
                            <button
                              onClick={() => handleAction(phone.id, 'stop')}
                              className="p-1 text-gray-600 hover:bg-gray-100 rounded"
                              title="关机"
                            >
                              <Square className="w-4 h-4" />
                            </button>
                          )}
                          <button
                            onClick={() => handleAction(phone.id, 'restart')}
                            className="p-1 text-blue-600 hover:bg-blue-50 rounded"
                            title="重启"
                          >
                            <RotateCcw className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-8 text-center text-gray-500">
              暂无实例数据，请先同步云手机
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}
