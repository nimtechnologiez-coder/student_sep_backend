import os
import sys
import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class StudentsappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'studentsapp'

    def ready(self):
        # Avoid running the scheduler during management commands such as migrations, shell, etc.
        commands_to_skip = {'makemigrations', 'migrate', 'collectstatic', 'shell', 'dbshell', 'createsuperuser'}
        if any(cmd in sys.argv for cmd in commands_to_skip):
            return

        # When running with 'runserver', Django uses auto-reloader by default.
        # Ensure we only start the background worker thread in the reloaded main process.
        is_runserver = 'runserver' in sys.argv
        if is_runserver and os.environ.get('RUN_MAIN') != 'true':
            return

        try:
            from .views import start_fee_reminder_scheduler
            start_fee_reminder_scheduler(interval_seconds=300)
            logger.info("Fee reminder scheduler initialized in StudentsappConfig.ready()")
        except Exception as e:
            logger.error(f"Failed to start fee reminder scheduler: {e}")
