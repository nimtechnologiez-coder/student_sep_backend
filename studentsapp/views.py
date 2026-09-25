from django.core.paginator import Paginator
from django.shortcuts import render
from django.db.models import Sum, Q, Count
from django.utils import timezone
import random
import string
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Student, Batch, FeePayment, PlacementOffer, ClassSchedule, Trainer, Attendance, Activity, AcademicModule, Assessment, AssessmentResult, Notification, AppUser

# =============================================================================
# ADMIN PORTAL CONTROLLERS
# =============================================================================

def dashboard(request):
    role = request.GET.get('role', 'admin').lower()
    if role == 'mentor':
        return mentor_dashboard(request)
        
    role_meta = {
        'accountant': {
            'role': 'accountant',
            'role_title': 'Accountant Dashboard',
            'user_name': 'Manoj Nair',
            'user_role': 'Senior Accountant',
            'user_initials': 'MN',
            'focus_area': 'Tuition Receivables, Installment Ledger & Receipts'
        },
        'admin': {
            'role': 'admin',
            'role_title': 'Admin Dashboard',
            'user_name': 'Sneha N',
            'user_role': 'Administrator',
            'user_initials': 'SN',
            'focus_area': 'Institutional Operations, Batches & Academic Analytics'
        }
    }

    now = timezone.now()
    fee_year_param = request.GET.get('fee_year', 'this_year')
    target_year = now.year if fee_year_param == 'this_year' else now.year - 1
    current_fee_year_label = 'This Year' if fee_year_param == 'this_year' else 'Last Year'
    
    total_students = Student.objects.count()
    active_batches = Batch.objects.filter(status='Active').count()
    admissions_ytd = Student.objects.filter(join_date__year=now.year).count()
    
    fee_agg = FeePayment.objects.filter(payment_date__year=target_year).aggregate(total=Sum('amount'))
    fee_total = fee_agg['total'] or 0
    # Format fee e.g. 2850000 -> 28.5 L
    fee_collection_str = f"₹ {fee_total/100000:.1f} L" if fee_total >= 100000 else f"₹ {fee_total:,.0f}"
    
    placement_offers = PlacementOffer.objects.count()
    classes_today = ClassSchedule.objects.filter(date=now.date()).count()
    trainer_count = Trainer.objects.filter(status='Active').count()
    
    total_attendance = Attendance.objects.count()
    present_attendance = Attendance.objects.filter(status='Present').count()
    avg_attendance = int((present_attendance / total_attendance) * 100) if total_attendance > 0 else 0

    dashboard_metrics = {
        'total_students': total_students,
        'students_trend': '0%',
        'active_batches': active_batches,
        'batches_trend': '0%',
        'admissions': admissions_ytd,
        'admissions_trend': '0%',
        'fee_collection': fee_collection_str,
        'fee_trend': '0%',
        'placement_offers': placement_offers,
        'placement_trend': '0%',
        'classes_scheduled': classes_today,
        'trainer_count': trainer_count,
        'average_attendance': f"{avg_attendance}%",
        'attendance_trend': '0%'
    }

    # Recent lists
    recent_admissions = Student.objects.order_by('-join_date')[:5]
    todays_classes = ClassSchedule.objects.filter(date=now.date()).order_by('time')[:5]
    recent_activities = Activity.objects.order_by('-timestamp')[:5]
    
    
    # Chart data
    student_status_data = list(Student.objects.values('status').annotate(count=Count('status')))
    batch_students_data = list(Batch.objects.annotate(student_count=Count('students')).values('name', 'student_count')[:6])
    
    # Monthly fee collection
    from collections import defaultdict
    fees = FeePayment.objects.filter(payment_date__year=target_year)
    monthly_fees = defaultdict(int)
    for f in fees:
        monthly_fees[f.payment_date.month] += int(f.amount)
    
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    fee_collection_data = []
    total_acc = 0
    # For a cumulative chart, if that's what the line graph is (it says 28.5L in Sep, rising from Jan)
    for i in range(1, 10): # Let's say up to September
        total_acc += monthly_fees.get(i, 0)
        fee_collection_data.append({
            'month': month_names[i-1],
            'amount_lakhs': float(total_acc) / 100000.0 # Fallback realistic dummy logic if 0
        })

    context = {
        'active_page': 'dashboard',
        'metrics': dashboard_metrics,
        'recent_admissions': recent_admissions,
        'todays_classes': todays_classes,
        'recent_activities': recent_activities,
        'student_status_data': student_status_data,
        'current_fee_year_label': current_fee_year_label,
        'batch_students_data': batch_students_data,
        'fee_collection_data': fee_collection_data,
        **role_meta.get(role, role_meta['admin'])
    }

    return render(request, 'dashboard.html', context)

def students(request):
    students_list = Student.objects.all().order_by('-join_date')
    
    # Filtering logic
    q = request.GET.get('q', '').strip()
    batch_filter = request.GET.get('batch', '')
    program_filter = request.GET.get('program', '')
    status_filter = request.GET.get('status', '')
    
    if q:
        students_list = students_list.filter(
            Q(name__icontains=q) | 
            Q(email__icontains=q) | 
            Q(phone__icontains=q) | 
            Q(student_id__icontains=q)
        )
    if batch_filter:
        students_list = students_list.filter(batch__name=batch_filter)
    if program_filter:
        students_list = students_list.filter(course=program_filter)
    if status_filter:
        students_list = students_list.filter(status=status_filter)
        
    paginator = Paginator(students_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    batches = Batch.objects.values_list('name', flat=True).distinct()
    programs = Student.objects.values_list('course', flat=True).distinct()
    
    context = {
        'active_page': 'students', 
        'students': page_obj,
        'batches': batches,
        'programs': programs,
        'current_q': q,
        'current_batch': batch_filter,
        'current_program': program_filter,
        'current_status': status_filter,
        'kpi': {
            'total': Student.objects.count(),
            'active': Student.objects.filter(status='Active').count(),
            'pending': Student.objects.filter(status='Onboarding').count(),
            'completed': Student.objects.filter(status='Completed').count(),
            'rejected': Student.objects.filter(status='Dropped').count(),
        }
    }
    return render(request, 'students.html', context)

def batches(request):
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')

    batches_qs = Batch.objects.all().order_by('-start_date')

    if query:
        batches_qs = batches_qs.filter(Q(name__icontains=query) | Q(course__icontains=query) | Q(trainer__name__icontains=query))
    if status_filter:
        batches_qs = batches_qs.filter(status__iexact=status_filter)

    paginator = Paginator(batches_qs, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get mentors for the create/edit modal
    mentors = AppUser.objects.filter(role='Mentor')

    context = {
        'active_page': 'batches', 
        'batches': page_obj,
        'mentors': mentors,
        'kpi': {
            'total': Batch.objects.count(),
            'active': Batch.objects.filter(status='Active').count(),
            'completed': Batch.objects.filter(status='Completed').count(),
            'enrolled': Student.objects.filter(batch__isnull=False).count(),
            'upcoming': Batch.objects.filter(status='Upcoming').count(),
            'attendance': "85%"
        },
        'current_q': query,
        'current_status': status_filter
    }
    return render(request, 'batches.html', context)

def classes(request):
    classes_list = ClassSchedule.objects.all().order_by('-date', '-time')
    context = {
        'active_page': 'classes', 
        'classes': classes_list,
        'kpi': {
            'total': ClassSchedule.objects.count(),
            'online': ClassSchedule.objects.filter(mode='Online').count(),
            'offline': ClassSchedule.objects.filter(mode='Offline').count(),
            'trainers': Trainer.objects.count()
        }
    }
    return render(request, 'classes.html', context)

def academic(request):
    modules = AcademicModule.objects.all()
    context = {
        'active_page': 'academic', 
        'modules': modules,
        'kpi': {
            'total': AcademicModule.objects.count(),
            'topics': AcademicModule.objects.count() * 4,
            'progress': "65%",
            'assessments': Assessment.objects.count()
        }
    }
    return render(request, 'academic.html', context)

def assessments(request):
    assessments_list = Assessment.objects.all().order_by('-date')
    context = {
        'active_page': 'assessments', 
        'assessments': assessments_list,
        'kpi': {
            'total': Assessment.objects.count(),
            'avg_score': "75%",
            'pending': 0,
            'high': AssessmentResult.objects.filter(score__gte=90).count() if hasattr(AssessmentResult, 'score') else 0
        }
    }
    return render(request, 'assessments.html', context)

def fees(request):
    payments = FeePayment.objects.all().order_by('-payment_date')
    context = {
        'active_page': 'fees', 
        'payments': payments,
        'kpi': {
            'total': f"₹{sum(p.amount for p in FeePayment.objects.filter(status='Paid'))/100000:.1f}L",
            'pending': FeePayment.objects.filter(status='Pending').count(),
            'overdue': 0,
            'avg': "₹15,000"
        }
    }
    return render(request, 'fees.html', context)

def reports(request):
    activities = Activity.objects.all().order_by('-timestamp')
    context = {
        'active_page': 'reports', 
        'activities': activities,
        'kpi': {
            'total': Activity.objects.count(),
            'generated': Activity.objects.filter(timestamp__month=timezone.now().month).count(),
            'avg_score': "75%",
            'attendance': "85%"
        }
    }
    return render(request, 'reports.html', context)

def users_roles(request):
    query = request.GET.get('q', '')
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')

    users_qs = AppUser.objects.all().order_by('-id')

    if query:
        users_qs = users_qs.filter(Q(name__icontains=query) | Q(email__icontains=query) | Q(username__icontains=query))
    if role_filter and role_filter != 'all':
        users_qs = users_qs.filter(role__iexact=role_filter)
    if status_filter:
        users_qs = users_qs.filter(status__iexact=status_filter)

    paginator = Paginator(users_qs, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'active_page': 'users_roles', 
        'users': page_obj,
        'kpi': {
            'total': AppUser.objects.count(),
            'admins': AppUser.objects.filter(role='Admin').count(),
            'mentors': AppUser.objects.filter(role='Mentor').count(),
            'accountants': AppUser.objects.filter(role='Accountant').count(),
            'active': AppUser.objects.filter(status='Active').count(),
            'blocked': AppUser.objects.filter(status='Blocked').count(),
        },
        'current_q': query,
        'current_role': role_filter,
        'current_status': status_filter
    }
    return render(request, 'users_roles.html', context)

def notifications(request):
    notifs = Notification.objects.all().order_by('-timestamp')
    context = {'active_page': 'notifications', 'notifications': notifs}
    return render(request, 'notifications.html', context)


# =============================================================================
# MENTOR PORTAL CONTROLLERS
# =============================================================================

def mentor_dashboard(request):
    context = {
        'active_page': 'mentor_dashboard',
        'role': 'mentor',
        'is_mentor': True,
        'user_name': 'Dr. Rajiv Sen',
        'user_role': 'Senior Faculty Mentor',
        'user_initials': 'RS',
        # TODO: Fetch real data
        'students': [],
        'todays_classes': []
    }
    return render(request, 'mentor/dashboard.html', context)

def mentor_students(request):
    context = {
        'active_page': 'mentor_students',
        'role': 'mentor',
        'is_mentor': True,
        'user_name': 'Dr. Rajiv Sen',
        'user_role': 'Senior Faculty Mentor',
        'user_initials': 'RS',
        # TODO: Fetch real data
        'students': []
    }
    return render(request, 'mentor/students.html', context)

def mentor_student_detail(request, student_id):
    context = {
        'active_page': 'mentor_students',
        'role': 'mentor',
        'is_mentor': True,
        'user_name': 'Dr. Rajiv Sen',
        'user_role': 'Senior Faculty Mentor',
        'user_initials': 'RS',
        # TODO: Fetch real data
        'student': None,
        'evaluations': [],
        'attendance_records': []
    }
    return render(request, 'mentor/student_detail.html', context)

def mentor_classes(request):
    context = {
        'active_page': 'mentor_classes',
        'role': 'mentor',
        'is_mentor': True,
        'user_name': 'Dr. Rajiv Sen',
        'user_role': 'Senior Faculty Mentor',
        'user_initials': 'RS',
        # TODO: Fetch real data
        'classes': []
    }
    return render(request, 'mentor/classes.html', context)

def mentor_attendance(request, class_id=None):
    context = {
        'active_page': 'mentor_classes',
        'role': 'mentor',
        'is_mentor': True,
        'user_name': 'Dr. Rajiv Sen',
        'user_role': 'Senior Faculty Mentor',
        'user_initials': 'RS',
        # TODO: Fetch real data
        'students': []
    }
    return render(request, 'mentor/attendance.html', context)

def mentor_tasks(request):
    context = {
        'active_page': 'mentor_tasks',
        'role': 'mentor',
        'is_mentor': True,
        'user_name': 'Dr. Rajiv Sen',
        'user_role': 'Senior Faculty Mentor',
        'user_initials': 'RS',
        # TODO: Fetch real data
        'tasks': []
    }
    return render(request, 'mentor/tasks.html', context)

def mentor_evaluations(request, task_id=None):
    context = {
        'active_page': 'mentor_tasks',
        'role': 'mentor',
        'is_mentor': True,
        'user_name': 'Dr. Rajiv Sen',
        'user_role': 'Senior Faculty Mentor',
        'user_initials': 'RS',
        # TODO: Fetch real data
        'submissions': []
    }
    return render(request, 'mentor/evaluations.html', context)

def mentor_academic(request):
    context = {
        'active_page': 'mentor_academic',
        'role': 'mentor',
        'is_mentor': True,
        'user_name': 'Dr. Rajiv Sen',
        'user_role': 'Senior Faculty Mentor',
        'user_initials': 'RS',
        # TODO: Fetch real data
        'modules': []
    }
    return render(request, 'mentor/academic.html', context)

def mentor_assessments(request):
    context = {
        'active_page': 'mentor_assessments',
        'role': 'mentor',
        'is_mentor': True,
        'user_name': 'Dr. Rajiv Sen',
        'user_role': 'Senior Faculty Mentor',
        'user_initials': 'RS',
        # TODO: Fetch real data
        'assessments': []
    }
    return render(request, 'mentor/assessments.html', context)

def mentor_assessment_detail(request, assessment_id):
    context = {
        'active_page': 'mentor_assessments',
        'role': 'mentor',
        'is_mentor': True,
        'user_name': 'Dr. Rajiv Sen',
        'user_role': 'Senior Faculty Mentor',
        'user_initials': 'RS',
        # TODO: Fetch real data
        'assessment': None,
        'student_results': []
    }
    return render(request, 'mentor/assessment_detail.html', context)

def mentor_placement(request):
    context = {
        'active_page': 'mentor_placement',
        'role': 'mentor',
        'is_mentor': True,
        'user_name': 'Dr. Rajiv Sen',
        'user_role': 'Senior Faculty Mentor',
        'user_initials': 'RS',
        # TODO: Fetch real data
        'students': []
    }
    return render(request, 'mentor/placement.html', context)

def mentor_reports(request):
    context = {
        'active_page': 'mentor_reports',
        'role': 'mentor',
        'is_mentor': True,
        'user_name': 'Dr. Rajiv Sen',
        'user_role': 'Senior Faculty Mentor',
        'user_initials': 'RS',
        # TODO: Fetch real data
        'students': [],
        'attendance_trend': [],
        'subject_mastery': []
    }
    return render(request, 'mentor/reports.html', context)

def mentor_notifications(request):
    context = {
        'active_page': 'mentor_notifications',
        'role': 'mentor',
        'is_mentor': True,
        'user_name': 'Dr. Rajiv Sen',
        'user_role': 'Senior Faculty Mentor',
        'user_initials': 'RS',
        # TODO: Fetch real data
        'notifications': []
    }
    return render(request, 'mentor/notifications.html', context)

def login_view(request):
    return render(request, 'login.html')

def mentor_batches(request):
    context = {
        'active_page': 'mentor_batches',
        'role': 'mentor',
        'is_mentor': True,
        'user_name': 'Dr. Rajiv Sen',
        'user_role': 'Senior Faculty Mentor',
        'user_initials': 'RS',
        'batches': []
    }
    return render(request, 'mentor/batches.html', context)

def mentor_task_detail(request, task_id):
    context = {
        'active_page': 'mentor_tasks',
        'role': 'mentor',
        'is_mentor': True,
        'user_name': 'Dr. Rajiv Sen',
        'user_role': 'Senior Faculty Mentor',
        'user_initials': 'RS',
        'task': None,
        'submissions': []
    }
    return render(request, 'mentor/task_detail.html', context)


def placement(request):
    offers = PlacementOffer.objects.all().order_by('-offer_date')
    context = {
        'active_page': 'placement', 
        'offers': offers,
        'kpi': {
            'total': PlacementOffer.objects.filter(status='Accepted').count(),
            'extended': PlacementOffer.objects.count(),
            'interviews': PlacementOffer.objects.filter(status='Pending').count(),
            'avg_pkg': "₹6.5 LPA"
        }
    }
    return render(request, 'placement.html', context)

from django.http import JsonResponse

def api_fee_data(request):
    now = timezone.now()
    fee_year_param = request.GET.get('year', 'this_year')
    target_year = now.year if fee_year_param == 'this_year' else now.year - 1
    
    fee_agg = FeePayment.objects.filter(payment_date__year=target_year).aggregate(total=Sum('amount'))
    fee_total = fee_agg['total'] or 0
    fee_collection_str = f"₹ {fee_total/100000:.1f} L" if fee_total >= 100000 else f"₹ {fee_total:,.0f}"
    
    from collections import defaultdict
    fees = FeePayment.objects.filter(payment_date__year=target_year)
    monthly_fees = defaultdict(int)
    for f in fees:
        monthly_fees[f.payment_date.month] += int(f.amount)
    
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    fee_collection_data = []
    total_acc = 0
    for i in range(1, 10): 
        total_acc += monthly_fees.get(i, 0)
        fee_collection_data.append({
            'month': month_names[i-1],
            'amount_lakhs': float(total_acc) / 100000.0
        })
        
    return JsonResponse({
        'fee_collection_str': fee_collection_str,
        'fee_collection_data': fee_collection_data
    })

import string, random
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def api_approve_student(request, student_id):
    if request.method == 'POST':
        try:
            student = Student.objects.get(student_id=student_id)
            
            # Generate username: firstname + 3 numbers
            first_name = student.name.split()[0]
            nums_user = "".join(random.choices(string.digits, k=3))
            username = f"{first_name}{nums_user}"
            
            # Generate password: 2 upper, 2 lower, 3 digits, 1 special
            upper = random.choices(string.ascii_uppercase, k=2)
            lower = random.choices(string.ascii_lowercase, k=2)
            nums_pwd = random.choices(string.digits, k=3)
            special = random.choices("!@#$%^&*", k=1)
            pwd_list = upper + lower + nums_pwd + special
            random.shuffle(pwd_list)
            password = "".join(pwd_list)
            
            student.username = username
            student.portal_password = password
            student.approval_status = 'Approved'
            student.status = 'Active'
            student.save()
            
            return JsonResponse({
                'success': True,
                'username': username,
                'password': password
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False})

@csrf_exempt
def api_reject_student(request, student_id):
    if request.method == 'POST':
        try:
            student = Student.objects.get(student_id=student_id)
            student.approval_status = 'Rejected'
            student.status = 'Dropped'
            student.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False})

@csrf_exempt
def api_block_student(request, student_id):
    if request.method == 'POST':
        try:
            student = Student.objects.get(student_id=student_id)
            student.status = 'Dropped'
            student.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False})

@csrf_exempt
def api_edit_student(request, student_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            student = Student.objects.get(student_id=student_id)
            student.name = data.get('name', student.name)
            student.email = data.get('email', student.email)
            student.phone = data.get('phone', student.phone)
            student.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False})

@csrf_exempt
def api_add_user(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('name', '')
            email = data.get('email', '')
            role = data.get('role', '')
            
            # Generate username: name + 3 numbers
            first_name = name.split()[0] if name else 'User'
            nums_user = "".join(random.choices(string.digits, k=3))
            username = f"{first_name}{nums_user}"
            
            # Generate password: 2 capital, 3 small, 2 number, 1 special character
            upper = random.choices(string.ascii_uppercase, k=2)
            lower = random.choices(string.ascii_lowercase, k=3)
            nums_pwd = random.choices(string.digits, k=2)
            special = random.choices("!@#$%^&*", k=1)
            pwd_list = upper + lower + nums_pwd + special
            random.shuffle(pwd_list)
            password = "".join(pwd_list)
            
            AppUser.objects.create(
                name=name,
                email=email,
                role=role,
                username=username,
                portal_password=password
            )
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False})

@csrf_exempt
def api_edit_appuser(request, user_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            u = AppUser.objects.get(id=user_id)
            u.name = data.get('name', u.name)
            u.email = data.get('email', u.email)
            u.role = data.get('role', u.role)
            u.username = data.get('username', u.username)
            u.portal_password = data.get('portal_password', u.portal_password)
            u.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False})

@csrf_exempt
def api_block_appuser(request, user_id):
    if request.method == 'POST':
        try:
            u = AppUser.objects.get(id=user_id)
            u.status = 'Blocked'
            u.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False})

@csrf_exempt
def api_delete_appuser(request, user_id):
    if request.method == 'POST':
        try:
            AppUser.objects.get(id=user_id).delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False})

@csrf_exempt
def api_unblock_appuser(request, user_id):
    if request.method == 'POST':
        try:
            u = AppUser.objects.get(id=user_id)
            u.status = 'Active'
            u.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False})

@csrf_exempt
def api_add_batch(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            trainer_id = data.get('trainer_id')
            trainer = AppUser.objects.get(id=trainer_id) if trainer_id else None
            
            Batch.objects.create(
                name=data.get('name', ''),
                course=data.get('course', ''),
                trainer=trainer,
                capacity=data.get('capacity', 20),
                schedule_days=data.get('schedule_days', ''),
                schedule_time=data.get('schedule_time', ''),
                status=data.get('status', 'Upcoming'),
                start_date=data.get('start_date', timezone.now().date())
            )
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False})

@csrf_exempt
def api_edit_batch(request, batch_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            b = Batch.objects.get(id=batch_id)
            trainer_id = data.get('trainer_id')
            
            b.name = data.get('name', b.name)
            b.course = data.get('course', b.course)
            b.trainer = AppUser.objects.get(id=trainer_id) if trainer_id else b.trainer
            b.capacity = data.get('capacity', b.capacity)
            b.schedule_days = data.get('schedule_days', b.schedule_days)
            b.schedule_time = data.get('schedule_time', b.schedule_time)
            b.status = data.get('status', b.status)
            b.start_date = data.get('start_date', b.start_date)
            b.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False})

@csrf_exempt
def api_delete_batch(request, batch_id):
    if request.method == 'POST':
        try:
            Batch.objects.get(id=batch_id).delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False})
