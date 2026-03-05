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
    instance_id: str
    region: str = "cn-east-1"
    image_quality: int = 1  # 1=高清, 2=普通, 3=高速, 4=急速
    mode: int = 1  # 1=保持帧率, 2=保持分辨率, 3=平衡


class EncryptedKeyResponse(BaseModel):
    """获取加密串响应"""
    encrypted_key: str
    line_information: Optional[dict] = None
    trace_id: Optional[str] = None


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
        result = await client.get_encrypted_key_v4(
            instance_id=request.instance_id,
            region=request.region,
            image_quality=request.image_quality,
            mode=request.mode
        )
        
        return EncryptedKeyResponse(
            encrypted_key=result.get("base64Str", ""),
            line_information=result.get("lineInformation"),
            trace_id=result.get("traceId")
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取加密串失败: {str(e)}"
        )
