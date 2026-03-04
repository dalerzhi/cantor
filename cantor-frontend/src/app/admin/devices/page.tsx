'use client';

import { useState, useEffect } from 'react';
import DashboardLayout from '@/components/DashboardLayout';
import { Smartphone, Users, Check, X, RefreshCw } from 'lucide-react';
import { api } from '@/lib/api';
// import { useSearchParams } from 'next/navigation';

interface Device {
  id: string;
  name: string;
  serialNumber: string;
  status: 'available' | 'allocated' | 'offline' | 'maintenance';
  tenantId?: string;
  tenantName?: string;
  specs?: {
    cpu?: string;
    memory?: string;
    storage?: string;
    androidVersion?: string;
  };
  createdAt: string;
}

interface Tenant {
  id: string;
  name: string;
  deviceCount: number;
  maxDevices: number;
}

export default function DeviceAllocationPage() {
  // const searchParams = useSearchParams();
  const preselectedTenant = null;

  const [devices, setDevices] = useState<Device[]>([]);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTenant, setSelectedTenant] = useState<string>(
    preselectedTenant || ''
  );
  const [selectedDevices, setSelectedDevices] = useState<Set<string>>(new Set());
  const [showAllocateModal, setShowAllocateModal] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      // 获取未分配的设备列表和租户列表
      const [devicesRes, tenantsRes] = await Promise.all([
        api.get('/admin/devices?status=available'),
        api.get('/admin/tenants?status=active'),
      ]);

      if (devicesRes.data?.items) {
        setDevices(devicesRes.data.items);
      }
      if (tenantsRes.data?.items) {
        setTenants(tenantsRes.data.items);
      }
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAllocate = async () => {
    if (!selectedTenant || selectedDevices.size === 0) return;

    try {
      await api.post('/admin/devices/allocate', {
        tenantId: selectedTenant,
        deviceIds: Array.from(selectedDevices),
      });
      alert(`成功分配 ${selectedDevices.size} 台设备`);
      setSelectedDevices(new Set());
      setShowAllocateModal(false);
      fetchData();
    } catch (error) {
      console.error('Failed to allocate devices:', error);
      alert('分配失败，请重试');
    }
  };

  const toggleDeviceSelection = (deviceId: string) => {
    const newSelected = new Set(selectedDevices);
    if (newSelected.has(deviceId)) {
      newSelected.delete(deviceId);
    } else {
      newSelected.add(deviceId);
    }
    setSelectedDevices(newSelected);
  };

  const getStatusBadge = (status: string) => {
    const configs: Record<
      string,
      { label: string; className: string }
    > = {
      available: {
        label: '可分配',
        className: 'bg-green-100 text-green-700',
      },
      allocated: {
        label: '已分配',
        className: 'bg-blue-100 text-blue-700',
      },
      offline: {
        label: '离线',
        className: 'bg-gray-100 text-gray-700',
      },
      maintenance: {
        label: '维护中',
        className: 'bg-yellow-100 text-yellow-700',
      },
    };
    const config = configs[status] || configs.offline;
    return (
      <span
        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.className}`}
      >
        {config.label}
      </span>
    );
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* 页面标题 */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">设备分配</h1>
            <p className="text-gray-500 mt-1">将云手机资源分配给租户进行测试</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={fetchData}
              className="inline-flex items-center gap-2 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              刷新
            </button>
            <button
              onClick={() => setShowAllocateModal(true)}
              disabled={selectedDevices.size === 0}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Smartphone className="w-5 h-5" />
              分配所选设备 ({selectedDevices.size})
            </button>
          </div>
        </div>

        {/* 统计信息 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-green-100 rounded-lg">
                <Smartphone className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">可分配设备</p>
                <p className="text-2xl font-bold text-gray-900">
                  {devices.filter((d) => d.status === 'available').length}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-blue-100 rounded-lg">
                <Smartphone className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">已分配设备</p>
                <p className="text-2xl font-bold text-gray-900">
                  {devices.filter((d) => d.status === 'allocated').length}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-purple-100 rounded-lg">
                <Users className="w-6 h-6 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">活跃租户</p>
                <p className="text-2xl font-bold text-gray-900">{tenants.length}</p>
              </div>
            </div>
          </div>
        </div>

        {/* 设备列表 */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-900">可分配设备</h2>
          </div>

          {loading ? (
            <div className="p-8 text-center text-gray-400">加载中...</div>
          ) : devices.length === 0 ? (
            <div className="p-8 text-center">
              <p className="text-gray-400 mb-4">暂无可用设备</p>
              <p className="text-sm text-gray-500">请先从IaaS平台同步设备</p>
            </div>
          ) : (
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left">
                    <input
                      type="checkbox"
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      checked={
                        selectedDevices.size === devices.length &&
                        devices.length > 0
                      }
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedDevices(
                            new Set(devices.map((d) => d.id))
                          );
                        } else {
                          setSelectedDevices(new Set());
                        }
                      }}
                    />
                  </th>
                  <th className="px-6 py-3 text-left text-sm font-medium text-gray-500">设备信息</th>
                  <th className="px-6 py-3 text-left text-sm font-medium text-gray-500">规格</th>
                  <th className="px-6 py-3 text-left text-sm font-medium text-gray-500">状态</th>
                  <th className="px-6 py-3 text-left text-sm font-medium text-gray-500">当前租户</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {devices.map((device) => (
                  <tr
                    key={device.id}
                    className={`hover:bg-gray-50 ${
                      selectedDevices.has(device.id) ? 'bg-blue-50' : ''
                    }`}
                  >
                    <td className="px-6 py-4">
                      <input
                        type="checkbox"
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        checked={selectedDevices.has(device.id)}
                        onChange={() => toggleDeviceSelection(device.id)}
                      />
                    </td>
                    <td className="px-6 py-4">
                      <div>
                        <p className="font-medium text-gray-900">{device.name}</p>
                        <p className="text-sm text-gray-500">{device.serialNumber}</p>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-600">
                        {device.specs?.androidVersion && (
                          <span className="inline-block mr-2">
                            Android {device.specs.androidVersion}
                          </span>
                        )}
                        {device.specs?.memory && (
                          <span className="inline-block mr-2">
                            {device.specs.memory} RAM
                          </span>
                        )}
                        {device.specs?.storage && (
                          <span className="inline-block">
                            {device.specs.storage} ROM
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      {getStatusBadge(device.status)}
                    </td>
                    <td className="px-6 py-4">
                      {device.tenantName ? (
                        <span className="text-sm text-gray-900">{device.tenantName}</span>
                      ) : (
                        <span className="text-sm text-gray-400">未分配</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* 分配弹窗 */}
      {showAllocateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl w-full max-w-md mx-4 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100">
              <h3 className="font-semibold text-gray-900">分配设备</h3>
              <p className="text-sm text-gray-500 mt-1">
                已选择 {selectedDevices.size} 台设备
              </p>
            </div>

            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">选择租户</label>
                <select
                  value={selectedTenant}
                  onChange={(e) => setSelectedTenant(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">请选择租户...</option>
                  {tenants.map((tenant) => (
                    <option key={tenant.id} value={tenant.id}>
                      {tenant.name} ({tenant.deviceCount}/{tenant.maxDevices})
                    </option>
                  ))}
                </select>
              </div>

              {selectedTenant && (
                <div className="bg-gray-50 rounded-lg p-4">
                  {
                    (tenants.find((t) => t.id === selectedTenant)?.deviceCount || 0) +
                      selectedDevices.size >
                    (tenants.find((t) => t.id === selectedTenant)?.maxDevices || 0) ? (
                      <p className="text-sm text-red-600">
                        ⚠️ 超出配额限制！该租户最多可拥有{' '}
                        {tenants.find((t) => t.id === selectedTenant)?.maxDevices}{' '}
                        台设备
                      </p>
                    ) : (
                      <p className="text-sm text-green-600">
                        ✅ 分配后该租户将拥有{' '}
                        {(tenants.find((t) => t.id === selectedTenant)?.deviceCount ||
                          0) + selectedDevices.size}{' '}
                        /{tenants.find((t) => t.id === selectedTenant)?.maxDevices} 台设备
                      </p>
                    )
                  }
                </div>
              )}

              <div className="flex gap-3 pt-4">
                <button
                  onClick={() => setShowAllocateModal(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                >
                  取消
                </button>
                <button
                  onClick={handleAllocate}
                  disabled={
                    !selectedTenant ||
                    (tenants.find((t) => t.id === selectedTenant)?.deviceCount ||
                      0) +
                      selectedDevices.size >
                      (tenants.find((t) => t.id === selectedTenant)
                        ?.maxDevices || 0)
                  }
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  确认分配
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
