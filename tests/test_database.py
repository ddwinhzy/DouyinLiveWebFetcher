"""
测试数据库模块 - TDD方式实现SQLite弹幕录制功能
"""
import os
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到Python路径
sys.path.insert(0, '/home/ethan/cc/hxx/douyinlive/DouyinLiveWebFetcher')

from database import Database


class TestDatabaseInit(unittest.TestCase):
    """测试数据库初始化"""

    def test_database_creates_file(self):
        """测试数据库文件创建"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'test.db')
            db = Database(db_path)
            self.assertTrue(os.path.exists(db_path))

    def test_database_creates_tables(self):
        """测试数据库表创建"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'test.db')
            db = Database(db_path)
            # 验证表存在
            cursor = db.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = [row[0] for row in cursor.fetchall()]
            self.assertIn('live_rooms', tables)
            self.assertIn('messages', tables)
            self.assertIn('chat_messages', tables)
            self.assertIn('gift_messages', tables)
            self.assertIn('like_messages', tables)
            self.assertIn('member_messages', tables)
            self.assertIn('social_messages', tables)

    def test_database_has_lock_attribute(self):
        """测试数据库有线程锁属性"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'test.db')
            db = Database(db_path)
            # 应该有Lock对象用于线程安全
            self.assertTrue(hasattr(db, '_lock'))
            # 检查是threading.Lock的类型或具有acquire/release方法
            self.assertTrue(hasattr(db._lock, 'acquire'))
            self.assertTrue(hasattr(db._lock, 'release'))

    def test_database_wal_mode_enabled(self):
        """测试WAL模式已启用"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'test.db')
            db = Database(db_path)
            # 检查WAL模式是否启用
            cursor = db.conn.execute('PRAGMA journal_mode')
            journal_mode = cursor.fetchone()[0].upper()
            self.assertEqual(journal_mode, 'WAL')

    def test_database_timeout_set(self):
        """测试数据库超时设置"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'test.db')
            db = Database(db_path)
            # 检查超时是否已设置
            cursor = db.conn.execute('PRAGMA busy_timeout')
            timeout = cursor.fetchone()[0]
            # 超时应该大于0
            self.assertGreater(timeout, 0)


class TestLiveRoomOperations(unittest.TestCase):
    """测试直播间操作"""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, 'test.db')
        self.db = Database(self.db_path)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_insert_live_room(self):
        """测试插入直播间"""
        room_id = self.db.insert_live_room(
            room_id='123456',
            live_id='261378947940',
            title='测试直播间',
            anchor_name='主播A',
            anchor_id='100001'
        )
        self.assertIsNotNone(room_id)
        self.assertGreater(room_id, 0)

    def test_get_live_room_by_room_id(self):
        """测试根据room_id查询直播间"""
        inserted_id = self.db.insert_live_room(
            room_id='123456',
            live_id='261378947940',
            title='测试直播间',
            anchor_name='主播A',
            anchor_id='100001'
        )
        room = self.db.get_live_room_by_room_id('123456')
        self.assertIsNotNone(room)
        self.assertEqual(room['room_id'], '123456')
        self.assertEqual(room['anchor_name'], '主播A')


class TestChatMessageOperations(unittest.TestCase):
    """测试聊天消息操作"""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, 'test.db')
        self.db = Database(self.db_path)
        self.room_id = self.db.insert_live_room(
            room_id='123456',
            live_id='261378947940',
            title='测试直播间',
            anchor_name='主播A',
            anchor_id='100001'
        )

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_insert_chat_message(self):
        """测试插入聊天消息"""
        msg_id = self.db.insert_chat_message(
            room_id=self.room_id,
            user_id='100001',
            user_name='用户A',
            content='你好主播',
            msg_unique_key='unique_key_001'
        )
        self.assertIsNotNone(msg_id)
        self.assertGreater(msg_id, 0)

    def test_insert_duplicate_chat_message(self):
        """测试插入重复聊天消息(去重)"""
        msg_unique_key = 'unique_key_duplicate'
        msg_id1 = self.db.insert_chat_message(
            room_id=self.room_id,
            user_id='100001',
            user_name='用户A',
            content='你好主播',
            msg_unique_key=msg_unique_key
        )
        msg_id2 = self.db.insert_chat_message(
            room_id=self.room_id,
            user_id='100001',
            user_name='用户A',
            content='你好主播',
            msg_unique_key=msg_unique_key
        )
        # 重复消息应该返回None
        self.assertIsNone(msg_id2)

    def test_get_chat_messages_by_room(self):
        """测试查询聊天消息"""
        self.db.insert_chat_message(
            room_id=self.room_id,
            user_id='100001',
            user_name='用户A',
            content='消息1',
            msg_unique_key='key_001'
        )
        self.db.insert_chat_message(
            room_id=self.room_id,
            user_id='100002',
            user_name='用户B',
            content='消息2',
            msg_unique_key='key_002'
        )
        messages = self.db.get_chat_messages_by_room(self.room_id)
        self.assertEqual(len(messages), 2)


class TestGiftMessageOperations(unittest.TestCase):
    """测试礼物消息操作"""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, 'test.db')
        self.db = Database(self.db_path)
        self.room_id = self.db.insert_live_room(
            room_id='123456',
            live_id='261378947940',
            title='测试直播间',
            anchor_name='主播A',
            anchor_id='100001'
        )

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_insert_gift_message(self):
        """测试插入礼物消息"""
        msg_id = self.db.insert_gift_message(
            room_id=self.room_id,
            user_id='100001',
            user_name='用户A',
            gift_id=1,
            gift_name='小心心',
            gift_count=1,
            msg_unique_key='gift_key_001'
        )
        self.assertIsNotNone(msg_id)
        self.assertGreater(msg_id, 0)

    def test_get_gift_messages_by_room(self):
        """测试查询礼物消息"""
        self.db.insert_gift_message(
            room_id=self.room_id,
            user_id='100001',
            user_name='用户A',
            gift_id=1,
            gift_name='小心心',
            gift_count=1,
            msg_unique_key='gift_key_001'
        )
        messages = self.db.get_gift_messages_by_room(self.room_id)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]['gift_name'], '小心心')


class TestLikeMessageOperations(unittest.TestCase):
    """测试点赞消息操作"""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, 'test.db')
        self.db = Database(self.db_path)
        self.room_id = self.db.insert_live_room(
            room_id='123456',
            live_id='261378947940',
            title='测试直播间',
            anchor_name='主播A',
            anchor_id='100001'
        )

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_insert_like_message(self):
        """测试插入点赞消息"""
        msg_id = self.db.insert_like_message(
            room_id=self.room_id,
            user_id='100001',
            user_name='用户A',
            like_count=10,
            msg_unique_key='like_key_001'
        )
        self.assertIsNotNone(msg_id)
        self.assertGreater(msg_id, 0)

    def test_get_like_messages_by_room(self):
        """测试查询点赞消息"""
        self.db.insert_like_message(
            room_id=self.room_id,
            user_id='100001',
            user_name='用户A',
            like_count=10,
            msg_unique_key='like_key_001'
        )
        messages = self.db.get_like_messages_by_room(self.room_id)
        self.assertEqual(len(messages), 1)


class TestMemberMessageOperations(unittest.TestCase):
    """测试进房消息操作"""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, 'test.db')
        self.db = Database(self.db_path)
        self.room_id = self.db.insert_live_room(
            room_id='123456',
            live_id='261378947940',
            title='测试直播间',
            anchor_name='主播A',
            anchor_id='100001'
        )

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_insert_member_message(self):
        """测试插入进房消息"""
        msg_id = self.db.insert_member_message(
            room_id=self.room_id,
            user_id='100001',
            user_name='用户A',
            gender=1,
            msg_unique_key='member_key_001'
        )
        self.assertIsNotNone(msg_id)
        self.assertGreater(msg_id, 0)

    def test_get_member_messages_by_room(self):
        """测试查询进房消息"""
        self.db.insert_member_message(
            room_id=self.room_id,
            user_id='100001',
            user_name='用户A',
            gender=1,
            msg_unique_key='member_key_001'
        )
        messages = self.db.get_member_messages_by_room(self.room_id)
        self.assertEqual(len(messages), 1)


class TestSocialMessageOperations(unittest.TestCase):
    """测试关注消息操作"""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, 'test.db')
        self.db = Database(self.db_path)
        self.room_id = self.db.insert_live_room(
            room_id='123456',
            live_id='261378947940',
            title='测试直播间',
            anchor_name='主播A',
            anchor_id='100001'
        )

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_insert_social_message(self):
        """测试插入关注消息"""
        msg_id = self.db.insert_social_message(
            room_id=self.room_id,
            user_id='100001',
            user_name='用户A',
            action=1,
            msg_unique_key='social_key_001'
        )
        self.assertIsNotNone(msg_id)
        self.assertGreater(msg_id, 0)

    def test_get_social_messages_by_room(self):
        """测试查询关注消息"""
        self.db.insert_social_message(
            room_id=self.room_id,
            user_id='100001',
            user_name='用户A',
            action=1,
            msg_unique_key='social_key_001'
        )
        messages = self.db.get_social_messages_by_room(self.room_id)
        self.assertEqual(len(messages), 1)


class TestEdgeCases(unittest.TestCase):
    """测试边缘情况"""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, 'test.db')
        self.db = Database(self.db_path)
        self.room_id = self.db.insert_live_room(
            room_id='123456',
            live_id='261378947940',
            title='测试直播间',
            anchor_name='主播A',
            anchor_id='100001'
        )

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_empty_content(self):
        """测试空内容"""
        msg_id = self.db.insert_chat_message(
            room_id=self.room_id,
            user_id='100001',
            user_name='用户A',
            content='',
            msg_unique_key='empty_key'
        )
        self.assertIsNotNone(msg_id)

    def test_special_characters(self):
        """测试特殊字符"""
        special_content = "测试 emoji \U0001F600 SQL ' \" < > &"
        msg_id = self.db.insert_chat_message(
            room_id=self.room_id,
            user_id='100001',
            user_name='用户A',
            content=special_content,
            msg_unique_key='special_key'
        )
        self.assertIsNotNone(msg_id)

    def test_none_values(self):
        """测试None值处理"""
        msg_id = self.db.insert_chat_message(
            room_id=self.room_id,
            user_id='100001',
            user_name=None,
            content=None,
            msg_unique_key='none_key'
        )
        # None值应该被转换为空字符串
        self.assertIsNotNone(msg_id)

    def test_unicode_content(self):
        """测试Unicode内容"""
        unicode_content = "中文测试 🇨🇳 🇺🇸 émojis"
        msg_id = self.db.insert_chat_message(
            room_id=self.room_id,
            user_id='100001',
            user_name='用户A',
            content=unicode_content,
            msg_unique_key='unicode_key'
        )
        self.assertIsNotNone(msg_id)


class TestMessageUniqueKey(unittest.TestCase):
    """测试消息唯一键生成"""

    def test_generate_unique_key_format(self):
        """测试唯一键格式"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'test.db')
            db = Database(db_path)
            room_id = db.insert_live_room(
                room_id='123456',
                live_id='261378947940',
                title='测试',
                anchor_name='主播',
                anchor_id='100001'
            )

            key1 = db._generate_message_unique_key(
                room_id, 'chat', '100001', 'content1'
            )
            key2 = db._generate_message_unique_key(
                room_id, 'chat', '100001', 'content1'
            )
            # 相同参数应生成相同key
            self.assertEqual(key1, key2)

            key3 = db._generate_message_unique_key(
                room_id, 'chat', '100001', 'content2'
            )
            # 不同内容应生成不同key
            self.assertNotEqual(key1, key3)


class TestThreadSafety(unittest.TestCase):
    """测试线程安全性"""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, 'test.db')
        self.db = Database(self.db_path)
        self.room_id = self.db.insert_live_room(
            room_id='123456',
            live_id='261378947940',
            title='测试直播间',
            anchor_name='主播A',
            anchor_id='100001'
        )

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_concurrent_inserts_no_data_loss(self):
        """测试并发插入不会丢失数据"""
        errors = []
        results = []
        success_count = [0]

        def insert_messages(start_idx):
            try:
                for i in range(start_idx, start_idx + 50):
                    msg_id = self.db.insert_chat_message(
                        room_id=self.room_id,
                        user_id=f'user_{i}',
                        user_name=f'用户{i}',
                        content=f'消息内容{i}',
                        msg_unique_key=f'concurrent_key_{i}'
                    )
                    results.append(msg_id)
                    if msg_id is not None:
                        success_count[0] += 1
            except Exception as e:
                errors.append(str(e))

        # 启动4个线程同时插入
        threads = [
            threading.Thread(target=insert_messages, args=(0,)),
            threading.Thread(target=insert_messages, args=(50,)),
            threading.Thread(target=insert_messages, args=(100,)),
            threading.Thread(target=insert_messages, args=(150,)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 不应该有错误
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")

        # 检查成功插入的数量
        self.assertEqual(success_count[0], 200, f"Only {success_count[0]} inserted")

        # 检查所有消息是否都插入成功 (默认limit=100，需要指定更大的limit)
        messages = self.db.get_chat_messages_by_room(self.room_id, limit=300)
        self.assertEqual(len(messages), 200)

    def test_concurrent_duplicate_handling(self):
        """测试并发重复键处理"""
        # 使用相同的key让多个线程同时插入
        duplicate_key = 'duplicate_test_key'
        insert_count = [0]
        lock = threading.Lock()

        def try_insert():
            msg_id = self.db.insert_chat_message(
                room_id=self.room_id,
                user_id='user_dup',
                user_name='重复用户',
                content='重复消息',
                msg_unique_key=duplicate_key
            )
            with lock:
                if msg_id is not None:
                    insert_count[0] += 1

        threads = [threading.Thread(target=try_insert) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 只有1条记录应该成功插入
        self.assertEqual(insert_count[0], 1)


class TestTOCTOUFix(unittest.TestCase):
    """测试TOCTOU漏洞修复"""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, 'test.db')
        self.db = Database(self.db_path)
        self.room_id = self.db.insert_live_room(
            room_id='123456',
            live_id='261378947940',
            title='测试直播间',
            anchor_name='主播A',
            anchor_id='100001'
        )

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_insert_uses_ignore_not_check(self):
        """测试使用INSERT OR IGNORE而非先检查后插入"""
        # 这个测试验证在高并发情况下不会因为TOCTOU导致重复插入
        results = []
        duplicate_key = 'toctou_test_key'

        def insert_task():
            msg_id = self.db.insert_chat_message(
                room_id=self.room_id,
                user_id='user_toctou',
                user_name='TOCTOU用户',
                content='测试TOCTOU',
                msg_unique_key=duplicate_key
            )
            results.append(msg_id)

        # 启动20个线程同时插入相同的key
        threads = [threading.Thread(target=insert_task) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 统计成功插入的数量
        success_count = sum(1 for r in results if r is not None)

        # 验证只有一条记录被插入
        messages = self.db.get_chat_messages_by_room(self.room_id)
        self.assertEqual(len(messages), 1)
        self.assertEqual(success_count, 1)


class TestRetryMechanism(unittest.TestCase):
    """测试重试机制"""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, 'test.db')
        self.db = Database(self.db_path)
        self.room_id = self.db.insert_live_room(
            room_id='123456',
            live_id='261378947940',
            title='测试直播间',
            anchor_name='主播A',
            anchor_id='100001'
        )

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_database_has_retry_decorator(self):
        """测试数据库有重试装饰器"""
        # 检查是否有重试机制的实现
        import inspect
        from database import Database

        # 检查_insert_message_record方法是否有重试逻辑
        source = inspect.getsource(Database._insert_message_record)
        # 应该包含重试相关的代码
        self.assertTrue(
            'retry' in source.lower() or 'attempt' in source.lower() or 'except' in source,
            "应该有重试机制相关代码"
        )

    def test_retry_decorator_exists(self):
        """测试retry_on_lock装饰器存在"""
        from database import retry_on_lock
        # 验证装饰器是一个可调用对象
        self.assertTrue(callable(retry_on_lock))
        # 验证可以调用装饰器
        decorator = retry_on_lock(max_retries=3)
        self.assertTrue(callable(decorator))

    def test_insert_methods_have_retry(self):
        """测试插入方法使用重试装饰器"""
        import inspect
        from database import Database

        # 检查主要插入方法是否有retry装饰器
        methods_to_check = [
            'insert_live_room',
            'insert_chat_message',
            'insert_gift_message',
            'insert_like_message',
            'insert_member_message',
            'insert_social_message',
            '_insert_message_record',
        ]

        for method_name in methods_to_check:
            method = getattr(Database, method_name)
            source = inspect.getsource(method)
            # 检查是否有retry相关代码
            self.assertTrue(
                'retry' in source.lower() or 'max_retries' in source.lower(),
                f"方法 {method_name} 应该有重试机制"
            )


if __name__ == '__main__':
    unittest.main()
