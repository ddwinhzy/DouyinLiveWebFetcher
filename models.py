"""
数据模型定义 - SQLite弹幕录制
"""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class LiveRoom:
    """直播间"""
    id: Optional[int] = None
    room_id: str = ''
    live_id: str = ''
    title: str = ''
    anchor_name: str = ''
    anchor_id: str = ''
    create_time: Optional[str] = None


@dataclass
class Message:
    """消息基类(用于去重)"""
    id: Optional[int] = None
    room_id: int = 0
    msg_type: str = ''
    msg_unique_key: str = ''
    user_id: str = ''
    user_name: str = ''
    create_time: Optional[str] = None


@dataclass
class ChatMessageModel:
    """聊天消息"""
    id: Optional[int] = None
    room_id: int = 0
    user_id: str = ''
    user_name: str = ''
    content: str = ''
    msg_unique_key: str = ''
    create_time: Optional[str] = None


@dataclass
class GiftMessageModel:
    """礼物消息"""
    id: Optional[int] = None
    room_id: int = 0
    user_id: str = ''
    user_name: str = ''
    gift_id: int = 0
    gift_name: str = ''
    gift_count: int = 1
    msg_unique_key: str = ''
    create_time: Optional[str] = None


@dataclass
class LikeMessageModel:
    """点赞消息"""
    id: Optional[int] = None
    room_id: int = 0
    user_id: str = ''
    user_name: str = ''
    like_count: int = 1
    msg_unique_key: str = ''
    create_time: Optional[str] = None


@dataclass
class MemberMessageModel:
    """进房消息"""
    id: Optional[int] = None
    room_id: int = 0
    user_id: str = ''
    user_name: str = ''
    gender: int = 0
    msg_unique_key: str = ''
    create_time: Optional[str] = None


@dataclass
class SocialMessageModel:
    """关注消息"""
    id: Optional[int] = None
    room_id: int = 0
    user_id: str = ''
    user_name: str = ''
    action: int = 0
    msg_unique_key: str = ''
    create_time: Optional[str] = None
