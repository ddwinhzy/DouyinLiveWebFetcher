"""
数据库管理模块 - SQLite弹幕录制
"""
import sqlite3
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager


class Database:
    """SQLite数据库管理类"""

    def __init__(self, db_path: str = 'douyin_live.db'):
        """
        初始化数据库
        :param db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        """创建数据库表"""
        cursor = self.conn.cursor()

        # 直播间表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS live_rooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id TEXT NOT NULL UNIQUE,
                live_id TEXT,
                title TEXT,
                anchor_name TEXT,
                anchor_id TEXT,
                create_time TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 消息总表(去重)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id INTEGER NOT NULL,
                msg_type TEXT NOT NULL,
                msg_unique_key TEXT NOT NULL UNIQUE,
                user_id TEXT,
                user_name TEXT,
                create_time TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (room_id) REFERENCES live_rooms(id)
            )
        ''')

        # 聊天消息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id INTEGER NOT NULL,
                user_id TEXT,
                user_name TEXT,
                content TEXT,
                msg_unique_key TEXT NOT NULL UNIQUE,
                create_time TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (room_id) REFERENCES live_rooms(id)
            )
        ''')

        # 礼物消息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gift_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id INTEGER NOT NULL,
                user_id TEXT,
                user_name TEXT,
                gift_id INTEGER DEFAULT 0,
                gift_name TEXT,
                gift_count INTEGER DEFAULT 1,
                msg_unique_key TEXT NOT NULL UNIQUE,
                create_time TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (room_id) REFERENCES live_rooms(id)
            )
        ''')

        # 点赞消息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS like_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id INTEGER NOT NULL,
                user_id TEXT,
                user_name TEXT,
                like_count INTEGER DEFAULT 1,
                msg_unique_key TEXT NOT NULL UNIQUE,
                create_time TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (room_id) REFERENCES live_rooms(id)
            )
        ''')

        # 进房消息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS member_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id INTEGER NOT NULL,
                user_id TEXT,
                user_name TEXT,
                gender INTEGER DEFAULT 0,
                msg_unique_key TEXT NOT NULL UNIQUE,
                create_time TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (room_id) REFERENCES live_rooms(id)
            )
        ''')

        # 关注消息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS social_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id INTEGER NOT NULL,
                user_id TEXT,
                user_name TEXT,
                action INTEGER DEFAULT 0,
                msg_unique_key TEXT NOT NULL UNIQUE,
                create_time TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (room_id) REFERENCES live_rooms(id)
            )
        ''')

        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_room ON messages(room_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_unique ON messages(msg_unique_key)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_room ON chat_messages(room_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_gift_room ON gift_messages(room_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_like_room ON like_messages(room_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_member_room ON member_messages(room_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_social_room ON social_messages(room_id)')

        self.conn.commit()

    def _generate_message_unique_key(
        self,
        room_id: int,
        msg_type: str,
        user_id: str,
        content: str
    ) -> str:
        """
        生成消息唯一键
        :param room_id: 直播间ID
        :param msg_type: 消息类型
        :param user_id: 用户ID
        :param content: 消息内容
        :return: 唯一键
        """
        raw = f"{room_id}:{msg_type}:{user_id}:{content}"
        return hashlib.md5(raw.encode('utf-8')).hexdigest()

    def _message_exists(self, msg_unique_key: str) -> bool:
        """
        检查消息是否已存在
        :param msg_unique_key: 消息唯一键
        :return: 是否存在
        """
        cursor = self.conn.execute(
            'SELECT 1 FROM messages WHERE msg_unique_key = ?',
            (msg_unique_key,)
        )
        return cursor.fetchone() is not None

    def _insert_message_record(
        self,
        room_id: int,
        msg_type: str,
        msg_unique_key: str,
        user_id: str,
        user_name: str
    ) -> Optional[int]:
        """
        插入消息记录到总表
        :param room_id: 直播间ID
        :param msg_type: 消息类型
        :param msg_unique_key: 消息唯一键
        :param user_id: 用户ID
        :param user_name: 用户名
        :return: 插入的记录ID
        """
        if self._message_exists(msg_unique_key):
            return None

        cursor = self.conn.execute(
            '''INSERT INTO messages (room_id, msg_type, msg_unique_key, user_id, user_name)
               VALUES (?, ?, ?, ?, ?)''',
            (room_id, msg_type, msg_unique_key, user_id or '', user_name or '')
        )
        self.conn.commit()
        return cursor.lastrowid

    # ==================== 直播间操作 ====================

    def insert_live_room(
        self,
        room_id: str,
        live_id: str = '',
        title: str = '',
        anchor_name: str = '',
        anchor_id: str = ''
    ) -> int:
        """
        插入或更新直播间
        :param room_id: 直播间ID
        :param live_id: 直播ID
        :param title: 标题
        :param anchor_name: 主播名称
        :param anchor_id: 主播ID
        :return: 直播间记录ID
        """
        cursor = self.conn.execute(
            '''INSERT OR REPLACE INTO live_rooms
               (room_id, live_id, title, anchor_name, anchor_id, create_time)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (room_id, live_id, title, anchor_name, anchor_id, datetime.now().isoformat())
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_live_room_by_room_id(self, room_id: str) -> Optional[Dict[str, Any]]:
        """
        根据room_id获取直播间
        :param room_id: 直播间ID
        :return: 直播间信息字典
        """
        cursor = self.conn.execute(
            'SELECT * FROM live_rooms WHERE room_id = ?',
            (room_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_live_room_by_id(self, room_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取直播间
        :param room_id: 直播间记录ID
        :return: 直播间信息字典
        """
        cursor = self.conn.execute(
            'SELECT * FROM live_rooms WHERE id = ?',
            (room_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    # ==================== 聊天消息操作 ====================

    def insert_chat_message(
        self,
        room_id: int,
        user_id: str,
        user_name: str,
        content: str,
        msg_unique_key: str = ''
    ) -> Optional[int]:
        """
        插入聊天消息
        :param room_id: 直播间ID
        :param user_id: 用户ID
        :param user_name: 用户名
        :param content: 消息内容
        :param msg_unique_key: 消息唯一键
        :return: 插入的记录ID，如果重复则返回None
        """
        if not msg_unique_key:
            msg_unique_key = self._generate_message_unique_key(
                room_id, 'chat', user_id, content or ''
            )

        # 先检查总表
        if self._message_exists(msg_unique_key):
            return None

        # 插入总表
        self._insert_message_record(
            room_id, 'chat', msg_unique_key, user_id, user_name
        )

        # 插入详细表
        cursor = self.conn.execute(
            '''INSERT OR IGNORE INTO chat_messages
               (room_id, user_id, user_name, content, msg_unique_key, create_time)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (room_id, user_id or '', user_name or '', content or '',
             msg_unique_key, datetime.now().isoformat())
        )
        self.conn.commit()
        return cursor.lastrowid if cursor.lastrowid else None

    def get_chat_messages_by_room(
        self,
        room_id: int,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取聊天消息
        :param room_id: 直播间ID
        :param limit: 返回数量限制
        :return: 消息列表
        """
        cursor = self.conn.execute(
            'SELECT * FROM chat_messages WHERE room_id = ? ORDER BY id DESC LIMIT ?',
            (room_id, limit)
        )
        return [dict(row) for row in cursor.fetchall()]

    # ==================== 礼物消息操作 ====================

    def insert_gift_message(
        self,
        room_id: int,
        user_id: str,
        user_name: str,
        gift_id: int,
        gift_name: str,
        gift_count: int = 1,
        msg_unique_key: str = ''
    ) -> Optional[int]:
        """
        插入礼物消息
        :param room_id: 直播间ID
        :param user_id: 用户ID
        :param user_name: 用户名
        :param gift_id: 礼物ID
        :param gift_name: 礼物名称
        :param gift_count: 礼物数量
        :param msg_unique_key: 消息唯一键
        :return: 插入的记录ID，如果重复则返回None
        """
        content = f"{gift_id}:{gift_count}"
        if not msg_unique_key:
            msg_unique_key = self._generate_message_unique_key(
                room_id, 'gift', user_id, content
            )

        if self._message_exists(msg_unique_key):
            return None

        self._insert_message_record(
            room_id, 'gift', msg_unique_key, user_id, user_name
        )

        cursor = self.conn.execute(
            '''INSERT OR IGNORE INTO gift_messages
               (room_id, user_id, user_name, gift_id, gift_name, gift_count,
                msg_unique_key, create_time)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (room_id, user_id or '', user_name or '', gift_id, gift_name or '',
             gift_count, msg_unique_key, datetime.now().isoformat())
        )
        self.conn.commit()
        return cursor.lastrowid if cursor.lastrowid else None

    def get_gift_messages_by_room(
        self,
        room_id: int,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取礼物消息
        :param room_id: 直播间ID
        :param limit: 返回数量限制
        :return: 消息列表
        """
        cursor = self.conn.execute(
            'SELECT * FROM gift_messages WHERE room_id = ? ORDER BY id DESC LIMIT ?',
            (room_id, limit)
        )
        return [dict(row) for row in cursor.fetchall()]

    # ==================== 点赞消息操作 ====================

    def insert_like_message(
        self,
        room_id: int,
        user_id: str,
        user_name: str,
        like_count: int = 1,
        msg_unique_key: str = ''
    ) -> Optional[int]:
        """
        插入点赞消息
        :param room_id: 直播间ID
        :param user_id: 用户ID
        :param user_name: 用户名
        :param like_count: 点赞数量
        :param msg_unique_key: 消息唯一键
        :return: 插入的记录ID，如果重复则返回None
        """
        content = str(like_count)
        if not msg_unique_key:
            msg_unique_key = self._generate_message_unique_key(
                room_id, 'like', user_id, content
            )

        if self._message_exists(msg_unique_key):
            return None

        self._insert_message_record(
            room_id, 'like', msg_unique_key, user_id, user_name
        )

        cursor = self.conn.execute(
            '''INSERT OR IGNORE INTO like_messages
               (room_id, user_id, user_name, like_count, msg_unique_key, create_time)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (room_id, user_id or '', user_name or '', like_count,
             msg_unique_key, datetime.now().isoformat())
        )
        self.conn.commit()
        return cursor.lastrowid if cursor.lastrowid else None

    def get_like_messages_by_room(
        self,
        room_id: int,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取点赞消息
        :param room_id: 直播间ID
        :param limit: 返回数量限制
        :return: 消息列表
        """
        cursor = self.conn.execute(
            'SELECT * FROM like_messages WHERE room_id = ? ORDER BY id DESC LIMIT ?',
            (room_id, limit)
        )
        return [dict(row) for row in cursor.fetchall()]

    # ==================== 进房消息操作 ====================

    def insert_member_message(
        self,
        room_id: int,
        user_id: str,
        user_name: str,
        gender: int = 0,
        msg_unique_key: str = ''
    ) -> Optional[int]:
        """
        插入进房消息
        :param room_id: 直播间ID
        :param user_id: 用户ID
        :param user_name: 用户名
        :param gender: 性别 0未知 1男 2女
        :param msg_unique_key: 消息唯一键
        :return: 插入的记录ID，如果重复则返回None
        """
        if not msg_unique_key:
            msg_unique_key = self._generate_message_unique_key(
                room_id, 'member', user_id, ''
            )

        if self._message_exists(msg_unique_key):
            return None

        self._insert_message_record(
            room_id, 'member', msg_unique_key, user_id, user_name
        )

        cursor = self.conn.execute(
            '''INSERT OR IGNORE INTO member_messages
               (room_id, user_id, user_name, gender, msg_unique_key, create_time)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (room_id, user_id or '', user_name or '', gender,
             msg_unique_key, datetime.now().isoformat())
        )
        self.conn.commit()
        return cursor.lastrowid if cursor.lastrowid else None

    def get_member_messages_by_room(
        self,
        room_id: int,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取进房消息
        :param room_id: 直播间ID
        :param limit: 返回数量限制
        :return: 消息列表
        """
        cursor = self.conn.execute(
            'SELECT * FROM member_messages WHERE room_id = ? ORDER BY id DESC LIMIT ?',
            (room_id, limit)
        )
        return [dict(row) for row in cursor.fetchall()]

    # ==================== 关注消息操作 ====================

    def insert_social_message(
        self,
        room_id: int,
        user_id: str,
        user_name: str,
        action: int = 0,
        msg_unique_key: str = ''
    ) -> Optional[int]:
        """
        插入关注消息
        :param room_id: 直播间ID
        :param user_id: 用户ID
        :param user_name: 用户名
        :param action: 动作类型
        :param msg_unique_key: 消息唯一键
        :return: 插入的记录ID，如果重复则返回None
        """
        content = str(action)
        if not msg_unique_key:
            msg_unique_key = self._generate_message_unique_key(
                room_id, 'social', user_id, content
            )

        if self._message_exists(msg_unique_key):
            return None

        self._insert_message_record(
            room_id, 'social', msg_unique_key, user_id, user_name
        )

        cursor = self.conn.execute(
            '''INSERT OR IGNORE INTO social_messages
               (room_id, user_id, user_name, action, msg_unique_key, create_time)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (room_id, user_id or '', user_name or '', action,
             msg_unique_key, datetime.now().isoformat())
        )
        self.conn.commit()
        return cursor.lastrowid if cursor.lastrowid else None

    def get_social_messages_by_room(
        self,
        room_id: int,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取关注消息
        :param room_id: 直播间ID
        :param limit: 返回数量限制
        :return: 消息列表
        """
        cursor = self.conn.execute(
            'SELECT * FROM social_messages WHERE room_id = ? ORDER BY id DESC LIMIT ?',
            (room_id, limit)
        )
        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
