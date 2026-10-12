from django.shortcuts import redirect
from django.http import JsonResponse

class DashboardAuthMiddleware:
    """
    Protects all dashboard pages and admin/mentor APIs from unauthorized access.
    Redirects unauthenticated users to /login/.
    Redirects already authenticated users on /login/ or / to their appropriate dashboard.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # Determine authentication state
        is_admin = False
        if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
            is_admin = True
        elif request.session.get('appuser_id') and str(request.session.get('appuser_role', '')).lower() in ('admin', 'administrator'):
            is_admin = True
        elif str(request.session.get('role', '')).lower() in ('admin', 'administrator'):
            is_admin = True

        is_mentor = False
        if request.session.get('appuser_id') and str(request.session.get('appuser_role', '')).lower() == 'mentor':
            is_mentor = True

        is_authenticated = is_admin or is_mentor

        # 1. If an already logged-in user visits login pages on GET, redirect to their dashboard
        if path in ('/', '/login', '/login/'):
            if request.method == 'GET' and is_authenticated:
                if is_mentor and not is_admin:
                    return redirect('mentor_dashboard')
                return redirect('dashboard')
            return self.get_response(request)

        # 2. Check protected dashboard pages
        protected_prefixes = [
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
            '/mentor',
        ]

        # /students/register/ is public student registration
        is_protected_page = False
        if path.startswith('/students/register'):
            is_protected_page = False
        else:
            for prefix in protected_prefixes:
                if path == prefix or path == f"{prefix}/" or path.startswith(f"{prefix}/"):
                    is_protected_page = True
                    break

        if is_protected_page:
            if not is_authenticated:
                return redirect('login_page')
            # If mentor attempts to access admin dashboard, redirect to mentor dashboard
            if is_mentor and not is_admin and not path.startswith('/mentor'):
                return redirect('mentor_dashboard')
            return self.get_response(request)

        # 3. Check protected Admin & Mentor APIs
        protected_api_prefixes = [
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
            '/api/mentor',
            '/api/curriculum/add-',
            '/api/curriculum/delete-',
            '/api/curriculum/edit-',
        ]

        is_protected_api = any(path.startswith(prefix) for prefix in protected_api_prefixes)
        if is_protected_api and not is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required. Please log in.'}, status=401)

        return self.get_response(request)
