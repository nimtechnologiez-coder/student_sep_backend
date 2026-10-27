from .models import Notification

def mentor_context(request):
    try:
        path = getattr(request, 'path', '')
        if hasattr(request, 'is_mentor') and hasattr(request, 'is_admin'):
            is_mentor = request.is_mentor
            is_admin = request.is_admin
        elif path.startswith('/mentor'):
            is_mentor = True
            is_admin = False
        else:
            appuser_role = str(request.session.get('appuser_role', '')).strip().lower()
            session_role = str(request.session.get('role', '')).strip().lower()
            is_mentor = (appuser_role == 'mentor' or session_role == 'mentor')
            is_admin = False
            if not is_mentor:
                if (hasattr(request, 'user') and request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)) or \
                   appuser_role in ('admin', 'administrator') or \
                   session_role in ('admin', 'administrator'):
                    is_admin = True

        unread_count = 0
        if is_mentor or path.startswith('/mentor/'):
            from .views import get_current_mentor, get_mentor_unread_count
            trainer = get_current_mentor(request)
            unread_count = get_mentor_unread_count(trainer)
        else:
            from .views import get_admin_notifications_qs
            admin_unread_count = get_admin_notifications_qs().filter(is_read=False).count()
            unread_count = admin_unread_count

        return {
            'is_mentor': is_mentor,
            'is_admin': is_admin,
            'role': 'mentor' if is_mentor else ('admin' if is_admin else ''),
            'unread_notifications_count': unread_count
        }
    except Exception:
        return {
            'is_mentor': False,
            'is_admin': False,
            'role': '',
            'unread_notifications_count': 0
        }

