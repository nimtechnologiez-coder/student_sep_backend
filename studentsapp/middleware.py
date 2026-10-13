from django.shortcuts import redirect
from django.http import JsonResponse

class DashboardAuthMiddleware:
    """
    Protects all dashboard pages and admin/mentor APIs from unauthorized access.
    Enforces strict role-based routing between Admin and Mentor portals:
    - Admin users are restricted to Admin routes (e.g. /dashboard/, /students/, /users/)
    - Mentor users are restricted to Mentor routes (e.g. /mentor/dashboard/, /mentor/students/)
    - Prevents session bleed or cross-role URL navigation.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # Determine user role strictly
        appuser_role = str(request.session.get('appuser_role', '')).strip().lower()
        session_role = str(request.session.get('role', '')).strip().lower()

        is_mentor = False
        is_admin = False

        if appuser_role == 'mentor' or session_role == 'mentor':
            is_mentor = True
            is_admin = False
        elif (hasattr(request, 'user') and request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)) or \
             appuser_role in ('admin', 'administrator') or \
             session_role in ('admin', 'administrator'):
            is_admin = True
            is_mentor = False

        is_authenticated = is_admin or is_mentor

        # 1. Login page routing
        if path in ('/', '/login', '/login/'):
            if request.method == 'GET' and is_authenticated:
                if is_mentor:
                    return redirect('mentor_dashboard')
                if is_admin:
                    return redirect('dashboard')
            return self.get_response(request)

        # 2. Check protected page access
        admin_page_prefixes = [
            '/dashboard',
            '/students',
            '/batches',
            '/classes',
            '/academic',
            '/assessments',
            '/fees',
            '/placement',
            '/reports',
            '/users',
            '/notifications',
        ]

        # Ignore public student registration
        if path.startswith('/students/register'):
            return self.get_response(request)

        is_admin_page = any(path == p or path == f"{p}/" or path.startswith(f"{p}/") for p in admin_page_prefixes)
        is_mentor_page = path == '/mentor' or path == '/mentor/' or path.startswith('/mentor/')

        # A. Unauthenticated access check
        if (is_admin_page or is_mentor_page) and not is_authenticated:
            return redirect('login_page')

        # B. Mentor accessing Admin pages -> redirect to corresponding Mentor page or Mentor Dashboard
        if is_admin_page and is_mentor:
            if path.startswith('/students'):
                return redirect('mentor_students')
            elif path.startswith('/classes') or path.startswith('/batches'):
                return redirect('mentor_classes')
            elif path.startswith('/academic'):
                return redirect('mentor_curriculum')
            elif path.startswith('/assessments'):
                return redirect('mentor_assessments')
            elif path.startswith('/placement'):
                return redirect('mentor_placement')
            elif path.startswith('/reports'):
                return redirect('mentor_reports')
            elif path.startswith('/notifications'):
                return redirect('mentor_notifications')
            else:
                # /users/, /fees/, /dashboard/, etc.
                return redirect('mentor_dashboard')

        # C. Admin accessing Mentor pages -> redirect to corresponding Admin page or Admin Dashboard
        if is_mentor_page and is_admin:
            if path.startswith('/mentor/students'):
                return redirect('students')
            elif path.startswith('/mentor/classes') or path.startswith('/mentor/attendance'):
                return redirect('classes')
            elif path.startswith('/mentor/batches'):
                return redirect('batches')
            elif path.startswith('/mentor/curriculum') or path.startswith('/mentor/academic'):
                return redirect('academic')
            elif path.startswith('/mentor/assessments'):
                return redirect('assessments')
            elif path.startswith('/mentor/placement'):
                return redirect('placement')
            elif path.startswith('/mentor/reports'):
                return redirect('reports')
            elif path.startswith('/mentor/notifications'):
                return redirect('notifications')
            else:
                return redirect('dashboard')

        # 3. Check protected Admin & Mentor APIs
        admin_api_prefixes = [
            '/api/approve-student',
            '/api/reject-student',
            '/api/block-student',
            '/api/unblock-student',
            '/api/add-student',
            '/api/edit-student',
            '/api/add-user',
            '/api/edit-appuser',
            '/api/block-appuser',
            '/api/unblock-appuser',
            '/api/delete-appuser',
            '/api/add-batch',
            '/api/edit-batch',
            '/api/delete-batch',
            '/api/assign-students-batch',
            '/api/export-students',
            '/api/export-fees',
            '/api/fees/',
            '/api/fee-data',
            '/api/admin',
            '/api/curriculum/add-',
            '/api/curriculum/delete-',
            '/api/curriculum/edit-',
        ]
        mentor_api_prefixes = [
            '/api/mentor',
        ]

        if any(path.startswith(p) for p in admin_api_prefixes):
            if not is_authenticated:
                return JsonResponse({'success': False, 'error': 'Authentication required. Please log in.'}, status=401)
            if not is_admin:
                return JsonResponse({'success': False, 'error': 'Permission denied. Administrator access required.'}, status=403)

        if any(path.startswith(p) for p in mentor_api_prefixes):
            if not is_authenticated:
                return JsonResponse({'success': False, 'error': 'Authentication required. Please log in.'}, status=401)
            if not is_mentor and not is_admin:
                return JsonResponse({'success': False, 'error': 'Permission denied. Mentor access required.'}, status=403)

        return self.get_response(request)
