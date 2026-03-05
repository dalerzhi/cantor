"""
RTC 实时视频流 API
提供获取加密串的接口，用于前端连接云手机视频流
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, get_current_user
from middleware.auth import AuthContext
from services.rtc_signaling_client import get_rtc_signaling_client

router = APIRouter(prefix="/rtc", tags=["RTC"])


class EncryptedKeyRequest(BaseModel):
    """获取加密串请求"""
    container_id: str  # 使用 containerId 不是 instanceId
    region: str = "cn-east-1"
    image_quality: int = 1  # 1=高清, 2=普通, 3=高速, 4=急速
    mode: int = 1  # 1=保持帧率, 2=保持分辨率, 3=平衡


class EncryptedKeyResponse(BaseModel):
    """获取加密串响应"""
    encrypted_key: Optional[str] = None  # V4 接口返回
    connection_info: Optional[dict] = None  # V2 接口直接返回连接信息
    success: bool = True
    message: str = "success"


@router.post("/encrypted-key", response_model=EncryptedKeyResponse)
async def get_encrypted_key(
    request: EncryptedKeyRequest,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取云手机视频流的加密串
    
    前端使用此加密串初始化 RTC SDK 连接云手机
    """
    try:
        client = get_rtc_signaling_client()
        result = await client.get_encrypted_key_v2(
            container_id=request.container_id,
            region=request.region,
            image_quality=request.image_quality,
            mode=request.mode
        )
        
        # Debug log
        print(f"RTC Result: {result}")
        
        # V2 接口返回格式不同
        if result.get("code") == 0:
            data = result.get("data", {})
            return EncryptedKeyResponse(
                encrypted_key=None,  # V2 不返回 base64Str
                connection_info=data,  # 直接返回连接信息
                success=True,
                message="success"
            )
        else:
            return EncryptedKeyResponse(
                success=False,
                message=result.get("msg", "Unknown error")
            )
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        print(f"RTC Error: {error_detail}")  # Log to console
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取加密串失败: {str(e)}"
        )
