'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { CloudPhoneViewer } from '@/components/cloudphone/CloudPhoneViewer';
import { getCloudPhoneInstances, getEncryptedKey } from '@/lib/cloudphone-api';
import { toast } from 'sonner';
import { Smartphone, RefreshCw, Plus } from 'lucide-react';

export default function CloudPhonePage() {
  const [instances, setInstances] = useState<Array<{
    sn: string;
    name: string;
    region: string;
    status: string;
  }>>([]);
  
  const [selectedInstance, setSelectedInstance] = useState<string | null>(null);
  const [encryptedKey, setEncryptedKey] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingList, setIsLoadingList] = useState(false);

  useEffect(() => {
    loadInstances();
  }, []);

  const loadInstances = async () => {
    try {
      setIsLoadingList(true);
      const data = await getCloudPhoneInstances();
      setInstances(data);
      
      // 如果没有实例，添加一个测试实例
      if (data.length === 0) {
        setInstances([
          {
            sn: 'qishuo-changsha-1-xya7ob6vt7d3hpme',
            name: '长沙云手机-01',
            region: 'changsha',
            status: 'idle',
          },
        ]);
      }
    } catch (error) {
      console.error('加载实例失败:', error);
      // 使用测试数据
      setInstances([
        {
          sn: 'qishuo-changsha-1-xya7ob6vt7d3hpme',
          name: '长沙云手机-01',
          region: 'changsha',
          status: 'idle',
        },
      ]);
    } finally {
      setIsLoadingList(false);
    }
  };

  const handleConnect = async (instance: typeof instances[0]) => {
    try {
      setIsLoading(true);
      setSelectedInstance(instance.sn);
      
      // 获取加密串
      const result = await getEncryptedKey({
        instanceId: instance.sn,
      });
      
      setEncryptedKey(result.encryptedKey);
      toast.success('已获取连接凭证');
    } catch (error: any) {
      console.error('连接失败:', error);
      toast.error('获取连接凭证失败: ' + error.message);
      setSelectedInstance(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDisconnect = () => {
    setSelectedInstance(null);
    setEncryptedKey(null);
    toast.info('已断开连接');
  };

  return (
    <div className="container mx-auto py-6 max-w-7xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
          ☁️ 云手机管理
        </h1>
        <p className="text-slate-400 mt-2">
          连接和管理云手机实例，实现远程控制和推流
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* 实例列表 */}
        <div className="lg:col-span-1">
          <Card className="border-slate-800 bg-slate-900/50">
            <CardHeader className="pb-4">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg text-white flex items-center gap-2">
                  <Smartphone className="w-5 h-5 text-cyan-400" />
                  可用实例
                </CardTitle>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={loadInstances}
                  disabled={isLoadingList}
                >
                  <RefreshCw className={`w-4 h-4 text-slate-400 ${isLoadingList ? 'animate-spin' : ''}`} />
                </Button>
              </div>
            </CardHeader>
            
            <CardContent className="space-y-3">
              {instances.map((instance) => (
                <Card
                  key={instance.sn}
                  className={`cursor-pointer transition-all duration-200 border ${
                    selectedInstance === instance.sn
                      ? 'border-cyan-500/50 bg-cyan-500/10'
                      : 'border-slate-700 bg-slate-800/50 hover:border-slate-600'
                  }`}
                  onClick={() => handleConnect(instance)}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-white truncate">{instance.name}</p>
                        <p className="text-xs text-slate-500 truncate mt-1">
                          {instance.sn}
                        </p>
                        <div className="flex items-center gap-2 mt-2">
                          <span className="text-xs px-2 py-0.5 rounded-full bg-slate-700 text-slate-300">
                            {instance.region}
                          </span>
                        </div>
                      </div>
                      
                      <Button
                        size="sm"
                        disabled={isLoading || selectedInstance === instance.sn}
                        className={selectedInstance === instance.sn 
                          ? 'bg-green-500/20 text-green-400 border-green-500/30' 
                          : ''}
                      >
                        {selectedInstance === instance.sn ? '已连接' : '连接'}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
              
              
              {instances.length === 0 && !isLoadingList && (
                <div className="text-center py-8">
                  <p className="text-slate-500 text-sm">暂无可用实例</p>
                  <Button variant="outline" className="mt-4" onClick={loadInstances}>
                    <Plus className="w-4 h-4 mr-2" />
                    刷新列表
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* 视频显示区域 */}
        <div className="lg:col-span-3">
          {selectedInstance && encryptedKey ? (
            <CloudPhoneViewer
              instance={{
                sn: selectedInstance,
                name: instances.find((i) => i.sn === selectedInstance)?.name || '',
                status: 'connected',
              }}
              encryptedKey={encryptedKey}
              onDisconnect={handleDisconnect}
            />
          ) : (
            <Card className="h-full min-h-[500px] flex items-center justify-center border-slate-800 bg-slate-900/50">
              <CardContent className="text-center">
                <div className="w-20 h-20 rounded-full bg-slate-800 flex items-center justify-center mx-auto mb-4">
                  <Smartphone className="w-10 h-10 text-slate-600" />
                </div>
                <p className="text-slate-400">选择一个云手机实例开始连接</p>
                <p className="text-slate-600 text-sm mt-2">连接后将显示实时画面和控制界面</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
