'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Loader2 } from 'lucide-react';
import DashboardLayout from '@/components/DashboardLayout';
import CloudPhonePlayer from '@/components/CloudPhonePlayer';
import { api } from '@/lib/api';

interface RTCConnectionInfo {
  signalingServices: Array<{ id: string; wssUrl: string }>;
  secretKey: string;
  containerID: string;
  roomID: string;
  peerID: string;
  iceServers: string[];
}

interface Device {
  id: string;
  name: string;
  status: string;
  provider_instance_id?: string;
  ip?: string;
}

export default function DeviceDetailPage() {
  const params = useParams();
  const router = useRouter();
  const deviceId = params.id as string;
  
  const [device, setDevice] = useState<Device | null>(null);
  const [connectionInfo, setConnectionInfo] = useState<RTCConnectionInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDeviceAndConnect = async () => {
      try {
        setLoading(true);
        
        // 1. 获取设备详情
        const deviceData = await api.get(`/devices/${deviceId}`);
        setDevice(deviceData);
        
        // 2. 获取 RTC 连接信息 (使用 container_id，即 provider_instance_id)
        const containerId = deviceData.provider_instance_id || deviceId;
        const rtcResponse = await api.post('/rtc/encrypted-key', {
          container_id: containerId,
          region: 'cn-east-1',
          image_quality: 1,
          mode: 1,
        });
        
        if (rtcResponse.success && rtcResponse.connection_info) {
          setConnectionInfo(rtcResponse.connection_info);
        } else {
          setError(rtcResponse.message || '获取连接信息失败');
        }
      } catch (err: any) {
        console.error('Failed to connect:', err);
        setError(err.message || '连接失败');
      } finally {
        setLoading(false);
      }
    };

    if (deviceId) {
      fetchDeviceAndConnect();
    }
  }, [deviceId]);

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-96">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
          <span className="ml-2 text-gray-600">加载中...</span>
        </div>
      </DashboardLayout>
    );
  }

  if (error) {
    return (
      <DashboardLayout>
        <div className="max-w-4xl mx-auto">
          <button
            onClick={() => router.push('/devices')}
            className="flex items-center text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            返回设备列表
          </button>
          
          <div className="bg-red-50 border border-red-200 rounded-lg p-8 text-center">
            <h3 className="text-red-600 font-semibold mb-2">连接失败</h3>
            <p className="text-red-500">{error}</p>
            <button
              onClick={() => window.location.reload()}
              className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              重试
            </button>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="max-w-6xl mx-auto">
        {/* 头部 */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center">
            <button
              onClick={() => router.push('/devices')}
              className="flex items-center text-gray-600 hover:text-gray-900 mr-4"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              返回
            </button>
            <h1 className="text-2xl font-bold">{device?.name || '云手机'}</h1>
          </div>
          
          <div className="flex items-center gap-2">
            <span className={`px-3 py-1 rounded-full text-sm ${
              device?.status === 'online'
                ? 'bg-green-100 text-green-600'
                : device?.status === 'running'
                ? 'bg-blue-100 text-blue-600'
                : 'bg-gray-100 text-gray-600'
            }`}>
              {device?.status === 'online' ? '在线' : 
               device?.status === 'running' ? '运行中' : '离线'}
            </span>
          </div>
        </div>

        {/* 视频播放器 */}
        <div className="bg-gray-900 rounded-lg overflow-hidden">
          <CloudPhonePlayer
            connectionInfo={connectionInfo || undefined}
            deviceName={device?.name}
            onError={(err) => setError(err)}
            onConnected={() => console.log('Connected to cloud phone')}
          />
        </div>

        {/* 设备信息 */}
        <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white rounded-lg p-4 shadow-sm border">
            <h3 className="text-sm font-medium text-gray-500 mb-1">设备 ID</h3>
            <p className="text-gray-900 font-mono">{device?.id}</p>
          </div>
          
          <div className="bg-white rounded-lg p-4 shadow-sm border">
            <h3 className="text-sm font-medium text-gray-500 mb-1">实例 ID</h3>
            <p className="text-gray-900 font-mono text-sm truncate">{device?.provider_instance_id || '-'}</p>
          </div>
          
          <div className="bg-white rounded-lg p-4 shadow-sm border">
            <h3 className="text-sm font-medium text-gray-500 mb-1">IP 地址</h3>
            <p className="text-gray-900">{device?.ip || '-'}</p>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
