from django.shortcuts import redirect
from django.http import JsonResponse

class DashboardAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # Ignore public student registration
        if path.startswith('/students/register'):
            return self.get_response(request)

        # 1. Retrieve session-stored auth namespaces
        session = getattr(request, 'session', {})
        admin_auth = session.get('admin_auth')
        mentor_auth = session.get('mentor_auth')
        tab_sessions = session.get('tab_sessions', {})

        # Legacy session fallback migration if namespaces are not yet populated
        if not admin_auth and not mentor_auth:
            legacy_appuser_role = str(session.get('appuser_role', '')).strip().lower()
            legacy_role = str(session.get('role', '')).strip().lower()
            if legacy_appuser_role == 'mentor' or legacy_role == 'mentor':
                mentor_auth = {
                    'appuser_id': session.get('appuser_id'),
                    'role': 'Mentor',
                    'appuser_role': 'Mentor',
                    'appuser_name': session.get('appuser_name', 'Mentor'),
                    'is_authenticated': True
                }
                session['mentor_auth'] = mentor_auth
            elif (hasattr(request, 'user') and request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)) or \
                 legacy_appuser_role in ('admin', 'administrator') or legacy_role in ('admin', 'administrator'):
                admin_auth = {
                    'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') and request.user.is_authenticated else None,
                    'appuser_id': session.get('appuser_id'),
                    'role': 'Admin',
                    'appuser_role': 'Admin',
                    'appuser_name': session.get('appuser_name', 'Admin'),
                    'is_authenticated': True
                }
                session['admin_auth'] = admin_auth

        # 2. Extract tab_id token if provided
        tab_id = request.headers.get('X-Tab-ID') or request.GET.get('tab_id') or request.POST.get('tab_id')
        tab_auth = tab_sessions.get(tab_id) if tab_id and isinstance(tab_sessions, dict) else None
        request.tab_id = tab_id

        # Route definitions
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
        is_admin_page = any(path == p or path == f"{p}/" or path.startswith(f"{p}/") for p in admin_page_prefixes)
        is_mentor_page = path == '/mentor' or path == '/mentor/' or path.startswith('/mentor/')
        is_mentor_api = path.startswith('/api/mentor')

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
        is_admin_api = any(path.startswith(p) for p in admin_api_prefixes)

        # 3. Determine active role context for this request
        target_role = None
        if tab_auth:
            t_role = str(tab_auth.get('role', '')).strip().lower()
            if t_role == 'mentor':
                target_role = 'mentor'
            elif t_role in ('admin', 'administrator'):
                target_role = 'admin'

        if not target_role:
            if is_mentor_page or is_mentor_api:
                target_role = 'mentor'
            elif is_admin_page or is_admin_api:
                target_role = 'admin'
            else:
                # Login or root path without tab context - do not assume a role
                target_role = None

        # 4. Hydrate in-memory request.session and request properties for downstream views & templates
        if target_role == 'mentor' and mentor_auth:
            session['appuser_role'] = 'Mentor'
            session['role'] = 'Mentor'
            session['appuser_id'] = mentor_auth.get('appuser_id')
            session['appuser_name'] = mentor_auth.get('appuser_name', 'Mentor')
            request.is_mentor = True
            request.is_admin = False
        elif target_role == 'admin' and admin_auth:
            session['appuser_role'] = 'Admin'
            session['role'] = 'Admin'
            session['appuser_name'] = admin_auth.get('appuser_name', 'Admin')
            if admin_auth.get('appuser_id'):
                session['appuser_id'] = admin_auth.get('appuser_id')
            else:
                session.pop('appuser_id', None)
            request.is_mentor = False
            request.is_admin = True
        else:
            request.is_mentor = False
            request.is_admin = False

        # 5. Handle Login page & Root routing
        if path in ('/', '/login', '/login/'):
            if request.method == 'GET':
                # If this specific tab has an authenticated session and didn't force login
                if tab_auth and not request.GET.get('force'):
                    if tab_auth.get('role', '').lower() == 'mentor' and mentor_auth:
                        return redirect('mentor_dashboard')
                    elif tab_auth.get('role', '').lower() in ('admin', 'administrator') and admin_auth:
                        return redirect('dashboard')

            return self.get_response(request)

        # 6. Protected Page Authentication and Cross-Role Routing Guards
        if is_admin_page:
            # If tab_id was provided, verify this specific tab has an active admin tab session
            if tab_id:
                if not tab_auth or str(tab_auth.get('role', '')).lower() not in ('admin', 'administrator'):
                    return redirect('login_page')
            elif not admin_auth:
                return redirect('login_page')

            # Cross-role guard
            if tab_auth and tab_auth.get('role', '').lower() == 'mentor' and not tab_auth.get('allow_admin'):
                return redirect('mentor_dashboard')

        if is_mentor_page:
            # If tab_id was provided, verify this specific tab has an active mentor tab session
            if tab_id:
                if not tab_auth or str(tab_auth.get('role', '')).lower() != 'mentor':
                    return redirect('login_page')
            elif not mentor_auth:
                return redirect('login_page')

            # Cross-role guard
            if tab_auth and tab_auth.get('role', '').lower() in ('admin', 'administrator') and not tab_auth.get('allow_mentor'):
                return redirect('dashboard')

        # 7. Check protected APIs
        if is_admin_api:
            if tab_id:
                if not tab_auth or str(tab_auth.get('role', '')).lower() not in ('admin', 'administrator'):
                    return JsonResponse({'success': False, 'error': 'Session expired or invalid tab.'}, status=401)
            elif not admin_auth and not mentor_auth:
                return JsonResponse({'success': False, 'error': 'Authentication required. Please log in.'}, status=401)
            if not admin_auth and not (tab_auth and str(tab_auth.get('role', '')).lower() in ('admin', 'administrator')):
                return JsonResponse({'success': False, 'error': 'Permission denied. Administrator access required.'}, status=403)

        if is_mentor_api:
            if tab_id:
                if not tab_auth or str(tab_auth.get('role', '')).lower() != 'mentor':
                    return JsonResponse({'success': False, 'error': 'Session expired or invalid tab.'}, status=401)
            elif not mentor_auth and not admin_auth:
                return JsonResponse({'success': False, 'error': 'Authentication required. Please log in.'}, status=401)
            if not mentor_auth and not (tab_auth and str(tab_auth.get('role', '')).lower() == 'mentor'):
                return JsonResponse({'success': False, 'error': 'Permission denied. Mentor access required.'}, status=403)

        return self.get_response(request)
