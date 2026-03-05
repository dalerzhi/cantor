'use client';

import { useEffect, useRef, useState } from 'react';
import { Loader2, AlertCircle } from 'lucide-react';

interface CloudPhonePlayerProps {
  encryptedKey: string;
  deviceName?: string;
  onError?: (error: string) => void;
  onConnected?: () => void;
}

export default function CloudPhonePlayer({
  encryptedKey,
  deviceName,
  onError,
  onConnected,
}: CloudPhonePlayerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const playerRef = useRef<any>(null);

  useEffect(() => {
    if (!encryptedKey || !containerRef.current) return;

    // 动态加载 SDK
    const loadSDK = async () => {
      try {
        // 解析加密串
        const config = JSON.parse(atob(encryptedKey));
        console.log('RTC Config:', config);

        // 加载 Cheersu SDK
        const script = document.createElement('script');
        script.src = '/assets/cheersu-sdk/lib/index.js';
        script.type = 'module';
        
        // 使用全局方式加载
        const scriptGlobal = document.createElement('script');
        scriptGlobal.src = '/assets/cheersu-sdk/public/cstreaming.min.js';
        scriptGlobal.async = true;
        
        document.body.appendChild(scriptGlobal);
        
        scriptGlobal.onload = () => {
          initializePlayer(config);
        };

        scriptGlobal.onerror = () => {
          const err = 'SDK 加载失败';
          setError(err);
          onError?.(err);
        };
      } catch (err: any) {
        const errorMsg = `初始化失败: ${err.message}`;
        setError(errorMsg);
        onError?.(errorMsg);
        setLoading(false);
      }
    };

    const initializePlayer = (config: any) => {
      try {
        // 确保容器有 ID
        if (!containerRef.current?.id) {
          containerRef.current!.id = 'cloud-phone-container';
        }

        // 创建视频元素
        const videoId = 'cloud-phone-video';
        const videoElement = document.createElement('video');
        videoElement.id = videoId;
        videoElement.className = 'w-full h-full object-contain bg-black';
        videoElement.autoplay = true;
        videoElement.playsInline = true;
        videoElement.muted = true; // 自动播放需要静音
        
        containerRef.current!.innerHTML = '';
        containerRef.current!.appendChild(videoElement);

        // 使用 SDK 初始化
        // @ts-ignore
        const cstreaming = window.cstreaming || (window as any).CStreaming;
        
        if (!cstreaming) {
          throw new Error('SDK 未加载');
        }

        const option = {
          romId: containerRef.current!.id,
          videoOption: {
            videoId: videoId,
            muted: false,
          },
          showNetworkInfo: true,
          createPButtons: true,
          noOperationTime: 300,
          terminalType: 0,
          enableKeyboard: true,
          isMouseScroll: true,
          heartBeatTime: 10000,
          inputMethodType: 1,
          callback: {
            listenLifeCycle: (event: string) => {
              console.log('Lifecycle:', event);
              if (event === 'video-loadeddata') {
                setLoading(false);
                onConnected?.();
              }
            },
            listenError: (err: any) => {
              console.error('RTC Error:', err);
              const errMsg = typeof err === 'string' ? err : err.message || '连接错误';
              setError(errMsg);
              onError?.(errMsg);
              setLoading(false);
            },
            listenNetworkInfo: (info: any) => {
              console.log('Network:', info);
            },
            listenNoOperation: () => {
              console.log('No operation timeout');
            },
          },
        };

        // 初始化播放器
        playerRef.current = new cstreaming(option);
        
        // 使用加密串启动
        playerRef.current.startEncryptedKey({
          encryptedKey: encryptedKey,
        });

        setLoading(false);
      } catch (err: any) {
        const errorMsg = `播放器初始化失败: ${err.message}`;
        setError(errorMsg);
        onError?.(errorMsg);
        setLoading(false);
      }
    };

    loadSDK();

    return () => {
      // 清理
      if (playerRef.current) {
        try {
          playerRef.current.leave();
        } catch (e) {
          console.error('Error leaving room:', e);
        }
      }
    };
  }, [encryptedKey, onError, onConnected]);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-gray-900 text-white p-8 rounded-lg">
        <AlertCircle className="w-12 h-12 text-red-500 mb-4" />
        <h3 className="text-lg font-semibold mb-2">连接失败</h3>
        <p className="text-gray-400 text-center">{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="mt-4 px-4 py-2 bg-blue-600 rounded-lg hover:bg-blue-700"
        >
          重试
        </button>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full bg-black rounded-lg overflow-hidden">
      {/* 视频容器 */}
      <div
        ref={containerRef}
        id="cloud-phone-container"
        className="w-full h-full"
        style={{ minHeight: '400px' }}
      />

      {/* 加载状态 */}
      {loading && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-900/80 text-white">
          <Loader2 className="w-8 h-8 animate-spin mb-4" />
          <p className="text-sm">正在连接云手机...</p>
          {deviceName && (
            <p className="text-xs text-gray-400 mt-2">{deviceName}</p>
          )}
        </div>
      )}

      {/* 设备信息 */}
      {deviceName && !loading && (
        <div className="absolute top-4 left-4 bg-black/50 text-white px-3 py-1 rounded text-sm">
          {deviceName}
        </div>
      )}
    </div>
  );
}
