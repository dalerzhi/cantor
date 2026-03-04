'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Loader2, Wifi, WifiOff, Smartphone } from 'lucide-react';
import { toast } from 'sonner';
import { loadCheersuSDK, initCloudPhoneSDK } from '@/lib/cheersu-sdk-loader';

interface CloudPhoneInstance {
  sn: string;
  name: string;
  status: 'idle' | 'connected' | 'error' | 'connecting';
}

interface CloudPhoneViewerProps {
  instance: CloudPhoneInstance;
  encryptedKey: string;
  onDisconnect?: () => void;
}

export const CloudPhoneViewer: React.FC<CloudPhoneViewerProps> = ({
  instance,
  encryptedKey,
  onDisconnect,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const sdkRef = useRef<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isConnected, setIsConnected] = useState(false);
  const [networkInfo, setNetworkInfo] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!encryptedKey || !containerRef.current) return;

    const initSDK = async () => {
      try {
        setIsLoading(true);
        setError(null);

        // 1. 加载SDK
        await loadCheersuSDK();
        console.log('[CloudPhone] SDK加载成功');

        // 2. 初始化SDK
        const sdk = initCloudPhoneSDK(
          encryptedKey,
          containerRef.current!.id,
          {
            onLifecycle: (info: any) => {
              console.log('[CloudPhone] Lifecycle:', info);
              
              switch (info.type) {
                case 'join-room':
                  setIsConnected(true);
                  setIsLoading(false);
                  toast.success('云手机连接成功');
                  break;
                case 'media-stream-added':
                  toast.success('视频流已加载');
                  break;
                case 'leave-room':
                  setIsConnected(false);
                  break;
              }
            },
            onError: (err: any) => {
              console.error('[CloudPhone] Error:', err);
              setError(err.message || '连接错误');
              setIsLoading(false);
              toast.error(`连接错误: ${err.message || '未知错误'}`);
            },
            onNetworkInfo: (info: any) => {
              setNetworkInfo(info);
            },
            enableKeyboard: true,
            createButtons: true,
          }
        );

        sdkRef.current = sdk;
        console.log('[CloudPhone] SDK初始化完成');

      } catch (err: any) {
        console.error('[CloudPhone] 初始化失败:', err);
        setError(err.message || '初始化失败');
        setIsLoading(false);
        toast.error('初始化云手机SDK失败');
      }
    };

    initSDK();

    return () => {
      // 清理
      if (sdkRef.current) {
        try {
          sdkRef.current.leave();
        } catch (e) {
          console.error('[CloudPhone] 清理失败:', e);
        }
      }
    };
  }, [encryptedKey, instance.sn]);

  const handleDisconnect = () => {
    if (sdkRef.current) {
      try {
        sdkRef.current.leave();
      } catch (e) {
        console.error('[CloudPhone] 断开失败:', e);
      }
      sdkRef.current = null;
    }
    setIsConnected(false);
    onDisconnect?.();
    toast.info('已断开云手机连接');
  };

  return (
    <Card className="w-full h-full flex flex-col border-0 shadow-lg">
      <CardHeader className="flex flex-row items-center justify-between py-3 px-4 bg-gradient-to-r from-slate-900 to-slate-800">
        <div className="flex items-center gap-3">
          <Smartphone className="w-5 h-5 text-cyan-400" />
          <div>
            <CardTitle className="text-sm font-medium text-white">{instance.name}</CardTitle>
            <p className="text-xs text-slate-400">{instance.sn}</p>
          </div>
          <Badge 
            variant={isConnected ? 'default' : 'secondary'}
            className={isConnected ? 'bg-green-500/20 text-green-400 border-green-500/30' : 'bg-slate-700 text-slate-400'}
          >
            {isConnected ? '已连接' : isLoading ? '连接中' : '未连接'}
          </Badge>
        </div>
        
        <div className="flex items-center gap-2">
          {networkInfo && (
            <div className="flex items-center gap-1 text-xs text-slate-400">
              {networkInfo.rrt ? (
                <>
                  <Wifi className="w-3 h-3" />
                  <span>{networkInfo.rrt}ms</span>
                </>
              ) : (
                <WifiOff className="w-3 h-3" />
              )}
            </div>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={handleDisconnect}
            className="border-slate-600 text-slate-300 hover:bg-slate-700 hover:text-white"
          >
            断开
          </Button>
        </div>
      </CardHeader>
      
      <CardContent className="flex-1 relative p-0 overflow-hidden bg-slate-950">
        {isLoading && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-900/95 z-10">
            <Loader2 className="w-10 h-10 animate-spin text-cyan-400 mb-4" />
            <div className="text-center">
              <p className="text-sm text-slate-300 mb-1">正在连接云手机...{instance.sn}</p>
              <p className="text-xs text-slate-500">初始化SDK并建立连接</p>
            </div>
          </div>
        )}

        {error && !isLoading && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-900/95 z-10">
            <div className="text-center max-w-md">
              <div className="w-16 h-16 rounded-full bg-red-500/10 flex items-center justify-center mx-auto mb-4">
                <span className="text-3xl">⚠️</span>
              </div>
              <p className="text-sm text-red-400 mb-2">连接失败</p>
              <p className="text-xs text-slate-500">{error}</p>
            </div>
          </div>
        )}
        
        <div
          ref={containerRef}
          id={`cloudphone-${instance.sn}`}
          className="w-full h-full min-h-[500px]"
        />
        
        {networkInfo && networkInfo.bitrate && (
          <div className="absolute bottom-4 right-4 bg-black/60 backdrop-blur-sm text-white text-xs px-3 py-2 rounded-lg border border-white/10">
            <div className="flex items-center gap-2">
              <span>延迟: {networkInfo.rrt || '-'}ms</span>
              <span className="text-slate-500">|</span>
              <span>码率: {networkInfo.bitrate || '-'}kbps</span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
