"""
Tests for desktop notification functionality when gift value exceeds threshold.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


class TestNotificationManager:
    """Test suite for NotificationManager class."""

    def test_notification_manager_can_be_instantiated(self):
        """NotificationManager should be instantiable with default threshold."""
        from notification import NotificationManager
        manager = NotificationManager()
        assert manager is not None

    def test_notification_manager_with_custom_threshold(self):
        """NotificationManager should accept custom threshold value."""
        from notification import NotificationManager
        manager = NotificationManager(threshold=200)
        assert manager.threshold == 200

    def test_default_threshold_is_100(self):
        """Default threshold should be 100 yuan (1000 diamonds)."""
        from notification import NotificationManager
        manager = NotificationManager()
        # 100 yuan = 1000 diamonds (1 yuan = 10 diamonds)
        assert manager.threshold == 1000

    def test_set_threshold_method(self):
        """NotificationManager should have a method to update threshold."""
        from notification import NotificationManager
        manager = NotificationManager()
        manager.set_threshold(500)
        assert manager.threshold == 500


class TestGiftValueCalculation:
    """Test suite for gift value calculation from GiftMessage."""

    def test_calculate_single_gift_value(self):
        """Should calculate single gift value correctly (diamond_count * quantity)."""
        from notification import NotificationManager

        # Mock GiftMessage
        mock_gift = Mock()
        mock_gift.diamond_count = 100  # 10 yuan per gift

        mock_message = Mock()
        mock_message.gift = mock_gift
        mock_message.combo_count = 2  # 2 gifts

        manager = NotificationManager()
        value = manager.calculate_gift_value(mock_message)

        # 100 diamonds * 2 = 200 diamonds = 20 yuan
        assert value == 200

    def test_calculate_gift_value_no_gift(self):
        """Should return 0 when gift is None."""
        from notification import NotificationManager

        mock_message = Mock()
        mock_message.gift = None
        mock_message.combo_count = 1

        manager = NotificationManager()
        value = manager.calculate_gift_value(mock_message)

        assert value == 0


class TestThresholdMonitoring:
    """Test suite for monitoring gift value against threshold."""

    def test_single_gift_exceeds_threshold(self):
        """Should detect when single gift value exceeds threshold."""
        from notification import NotificationManager

        mock_gift = Mock()
        mock_gift.diamond_count = 2000  # 200 yuan
        mock_gift.name = "豪华礼物"

        mock_message = Mock()
        mock_message.gift = mock_gift
        mock_message.combo_count = 1
        mock_message.user = Mock()
        mock_message.user.nick_name = "测试用户"

        manager = NotificationManager(threshold=1000)  # 100 yuan
        result = manager.check_threshold(mock_message)

        assert result is True

    def test_single_gift_below_threshold(self):
        """Should return False when gift value is below threshold."""
        from notification import NotificationManager

        mock_gift = Mock()
        mock_gift.diamond_count = 100  # 10 yuan

        mock_message = Mock()
        mock_message.gift = mock_gift
        mock_message.combo_count = 1

        manager = NotificationManager(threshold=1000)  # 100 yuan
        result = manager.check_threshold(mock_message)

        assert result is False

    def test_cumulative_value_exceeds_threshold(self):
        """Should track cumulative gift value and detect when threshold is exceeded."""
        from notification import NotificationManager

        manager = NotificationManager(threshold=1000)

        # First gift: 500 diamonds (50 yuan)
        mock_gift1 = Mock()
        mock_gift1.diamond_count = 500

        mock_message1 = Mock()
        mock_message1.gift = mock_gift1
        mock_message1.combo_count = 1

        result1 = manager.check_threshold(mock_message1)
        assert result1 is False
        assert manager.cumulative_value == 500

        # Second gift: 600 diamonds (60 yuan), total = 1100 (>100 yuan)
        mock_gift2 = Mock()
        mock_gift2.diamond_count = 600

        mock_message2 = Mock()
        mock_message2.gift = mock_gift2
        mock_message2.combo_count = 1

        result2 = manager.check_threshold(mock_message2)
        assert result2 is True

    def test_reset_cumulative_value(self):
        """Should be able to reset cumulative value."""
        from notification import NotificationManager

        manager = NotificationManager(threshold=1000)

        mock_gift = Mock()
        mock_gift.diamond_count = 500

        mock_message = Mock()
        mock_message.gift = mock_gift
        mock_message.combo_count = 1

        manager.check_threshold(mock_message)
        assert manager.cumulative_value == 500

        manager.reset()
        assert manager.cumulative_value == 0


class TestDesktopNotification:
    """Test suite for desktop notification sending."""

    @patch('notification.notification')
    def test_send_notification_single_gift(self, mock_notify):
        """Should send desktop notification when single gift exceeds threshold."""
        from notification import NotificationManager

        mock_gift = Mock()
        mock_gift.diamond_count = 2000
        mock_gift.name = "跑车"

        mock_message = Mock()
        mock_message.gift = mock_gift
        mock_message.combo_count = 1
        mock_message.user = Mock()
        mock_message.user.nick_name = "大户"
        mock_message.user.id = 12345

        manager = NotificationManager(threshold=1000)
        manager.send_notification(mock_message)

        mock_notify.notify.assert_called_once()
        call_args = mock_notify.notify.call_args
        assert 'title' in call_args.kwargs
        assert 'message' in call_args.kwargs

    @patch('notification.notification')
    def test_send_notification_cumulative(self, mock_notify):
        """Should send notification when cumulative value exceeds threshold."""
        from notification import NotificationManager

        manager = NotificationManager(threshold=1000)

        # First gift: 600 diamonds
        mock_gift1 = Mock()
        mock_gift1.diamond_count = 600
        mock_gift1.name = "鲜花"

        mock_message1 = Mock()
        mock_message1.gift = mock_gift1
        mock_message1.combo_count = 1
        mock_message1.user = Mock()
        mock_message1.user.nick_name = "用户A"

        manager.process_gift_message(mock_message1)

        # Second gift: 500 diamonds, total = 1100
        mock_gift2 = Mock()
        mock_gift2.diamond_count = 500
        mock_gift2.name = "棒棒糖"

        mock_message2 = Mock()
        mock_message2.gift = mock_gift2
        mock_message2.combo_count = 1
        mock_message2.user = Mock()
        mock_message2.user.nick_name = "用户B"

        manager.process_gift_message(mock_message2)

        # Should have sent notification
        assert mock_notify.notify.call_count >= 1

    @patch('notification.notification')
    def test_no_notification_below_threshold(self, mock_notify):
        """Should not send notification when value is below threshold."""
        from notification import NotificationManager

        mock_gift = Mock()
        mock_gift.diamond_count = 100  # 10 yuan

        mock_message = Mock()
        mock_message.gift = mock_gift
        mock_message.combo_count = 1

        manager = NotificationManager(threshold=1000)
        manager.process_gift_message(mock_message)

        mock_notify.notify.assert_not_called()


class TestProcessGiftMessage:
    """Test suite for processing gift messages end-to-end."""

    @patch('notification.notification')
    def test_process_gift_message_returns_correct_value(self, mock_notify):
        """process_gift_message should return the calculated gift value."""
        from notification import NotificationManager

        mock_gift = Mock()
        mock_gift.diamond_count = 500

        mock_message = Mock()
        mock_message.gift = mock_gift
        mock_message.combo_count = 2  # 2 gifts

        manager = NotificationManager(threshold=1000)
        value = manager.process_gift_message(mock_message)

        assert value == 1000  # 500 * 2

    def test_process_gift_message_without_gift(self):
        """process_gift_message should handle messages without gift data."""
        from notification import NotificationManager

        mock_message = Mock()
        mock_message.gift = None
        mock_message.combo_count = 0

        manager = NotificationManager(threshold=1000)
        value = manager.process_gift_message(mock_message)

        assert value == 0


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_zero_diamond_count(self):
        """Should handle zero diamond count correctly."""
        from notification import NotificationManager

        mock_gift = Mock()
        mock_gift.diamond_count = 0

        mock_message = Mock()
        mock_message.gift = mock_gift
        mock_message.combo_count = 5

        manager = NotificationManager(threshold=1000)
        value = manager.calculate_gift_value(mock_message)

        assert value == 0

    def test_zero_combo_count(self):
        """Should handle zero combo count correctly."""
        from notification import NotificationManager

        mock_gift = Mock()
        mock_gift.diamond_count = 100

        mock_message = Mock()
        mock_message.gift = mock_gift
        mock_message.combo_count = 0

        manager = NotificationManager(threshold=1000)
        value = manager.calculate_gift_value(mock_message)

        assert value == 0

    def test_negative_values_not_allowed(self):
        """Should handle negative values gracefully."""
        from notification import NotificationManager

        mock_gift = Mock()
        mock_gift.diamond_count = -100

        mock_message = Mock()
        mock_message.gift = mock_gift
        mock_message.combo_count = 1

        manager = NotificationManager(threshold=1000)
        value = manager.calculate_gift_value(mock_message)

        # Should treat negative as 0
        assert value >= 0
