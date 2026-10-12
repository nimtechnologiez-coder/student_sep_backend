import logging

logger = logging.getLogger(__name__)

def check_and_create_fee_reminders(student=None):
    """
    Disabled: Fee reminders are now displayed exclusively via the separate Fee Reminder modal at the top of the portal.
    Per user specification, no notifications or toast messages are generated.
    """
    return 0

def start_fee_reminder_scheduler(interval_seconds=300):
    """
    Disabled background scheduler to prevent automated notification messages.
    """
    pass
