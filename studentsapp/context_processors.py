from .models import Notification

def mentor_context(request):
    try:
        appuser_role = str(request.session.get('appuser_role', '')).lower()
        is_mentor_path = request.path.startswith('/mentor/')

        if is_mentor_path or appuser_role == 'mentor':
            from .views import get_current_mentor, get_mentor_unread_count
            trainer = get_current_mentor(request)
            unread_count = get_mentor_unread_count(trainer)
            return {
                'unread_notifications_count': unread_count
            }
        else:
            admin_unread_count = Notification.objects.filter(is_read=False).count()
            return {
                'unread_notifications_count': admin_unread_count
            }
    except Exception:
        return {
            'unread_notifications_count': 0
        }
