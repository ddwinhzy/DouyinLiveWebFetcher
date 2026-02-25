"""
Desktop notification module for monitoring live stream gift values.

This module provides functionality to monitor gift messages and send
desktop notifications when gift value exceeds configured threshold.
"""

from plyer import notification


class NotificationManager:
    """
    Manages gift value monitoring and desktop notifications.

    Default threshold is 100 yuan (1000 diamonds, where 1 yuan = 10 diamonds).
    """

    # Default threshold in diamonds (100 yuan * 10)
    DEFAULT_THRESHOLD = 1000

    def __init__(self, threshold: int = None):
        """
        Initialize NotificationManager with optional custom threshold.

        Args:
            threshold: Custom threshold in diamonds. If None, uses DEFAULT_THRESHOLD.
        """
        self.threshold = threshold if threshold is not None else self.DEFAULT_THRESHOLD
        self.cumulative_value = 0

    def set_threshold(self, threshold: int) -> None:
        """
        Update the threshold value.

        Args:
            threshold: New threshold in diamonds.
        """
        self.threshold = threshold

    def calculate_gift_value(self, gift_message) -> int:
        """
        Calculate total gift value from a GiftMessage.

        Args:
            gift_message: A GiftMessage object with gift and combo_count.

        Returns:
            Total value in diamonds (diamond_count * combo_count).
        """
        if gift_message.gift is None:
            return 0

        diamond_count = gift_message.gift.diamond_count or 0
        combo_count = gift_message.combo_count or 0

        # Handle negative values
        if diamond_count < 0:
            diamond_count = 0
        if combo_count < 0:
            combo_count = 0

        return diamond_count * combo_count

    def check_threshold(self, gift_message) -> bool:
        """
        Check if gift value exceeds threshold (either single or cumulative).

        Args:
            gift_message: A GiftMessage object.

        Returns:
            True if threshold is exceeded, False otherwise.
        """
        gift_value = self.calculate_gift_value(gift_message)

        # Check single gift
        if gift_value >= self.threshold:
            return True

        # Check cumulative value
        self.cumulative_value += gift_value
        if self.cumulative_value >= self.threshold:
            return True

        return False

    def reset(self) -> None:
        """Reset cumulative value to zero."""
        self.cumulative_value = 0

    def send_notification(self, gift_message) -> None:
        """
        Send desktop notification for a gift message.

        Args:
            gift_message: A GiftMessage object with gift details and user info.
        """
        gift_value = self.calculate_gift_value(gift_message)
        gift_name = gift_message.gift.name if gift_message.gift else "未知礼物"
        user_name = gift_message.user.nick_name if gift_message.user else "未知用户"

        # Convert diamonds to yuan for display
        yuan_value = gift_value / 10

        title = "直播间礼物提醒"
        message = f"{user_name} 送出了 {gift_name}，价值 {yuan_value:.1f} 元"

        notification.notify(
            title=title,
            message=message,
            app_name="DouyinLive",
            timeout=5
        )

    def process_gift_message(self, gift_message) -> int:
        """
        Process a gift message: calculate value, check threshold, send notification.

        Args:
            gift_message: A GiftMessage object.

        Returns:
            The calculated gift value in diamonds.
        """
        gift_value = self.calculate_gift_value(gift_message)

        if gift_value >= self.threshold:
            self.send_notification(gift_message)
        else:
            # Track cumulative value
            self.cumulative_value += gift_value
            # Check if cumulative now exceeds threshold
            if self.cumulative_value >= self.threshold:
                self.send_notification(gift_message)
                # Reset after notification
                self.cumulative_value = 0

        return gift_value
