from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.db.models import Sum, Q, Count
from django.utils import timezone
import random
import string
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, date, time, timedelta
from .models import Student, Batch, FeePayment, PlacementOffer, ClassSchedule, Trainer, Attendance, Activity, AcademicModule, Assessment, AssessmentResult, Notification, AppUser, StudentRequest, CurriculumMonth, CurriculumModule, CurriculumTopic, CourseModule, CourseTopic, Task, TaskSubmission

# =============================================================================
# ADMIN PORTAL CONTROLLERS
# =============================================================================

def dashboard(request):
    role = request.GET.get('role', 'admin').lower()
    if role == 'mentor':
        return mentor_dashboard(request)
        
    curr_user = request.user.get_full_name() if (request.user.is_authenticated and request.user.get_full_name()) else (request.user.username if request.user.is_authenticated else '')
    app_u = AppUser.objects.filter(role__iexact=role).first()
    user_name = curr_user or (app_u.name if app_u else '')
    user_initials = "".join([n[0] for n in user_name.split()[:2]]).upper() if user_name else ''

    role_meta = {
        'accountant': {
            'role': 'accountant',
            'role_title': 'Accountant Dashboard',
            'user_name': user_name,
            'user_role': 'Accountant',
            'user_initials': user_initials,
            'focus_area': 'Tuition Receivables, Installment Ledger & Receipts'
        },
        'admin': {
            'role': 'admin',
            'role_title': 'Admin Dashboard',
            'user_name': user_name,
            'user_role': 'Administrator',
            'user_initials': user_initials,
            'focus_area': 'Institutional Operations, Batches & Academic Analytics'
        }
    }

    now = timezone.now()
    fee_year_param = request.GET.get('fee_year', 'this_year')
    target_year = now.year if fee_year_param == 'this_year' else now.year - 1
    current_fee_year_label = 'This Year' if fee_year_param == 'this_year' else 'Last Year'
    
    total_students = Student.objects.count()
    active_batches = Batch.objects.count()
    admissions_ytd = Student.objects.filter(join_date__year=now.year).count()
    
    fee_agg = FeePayment.objects.filter(payment_date__year=target_year).aggregate(total=Sum('amount'))
    fee_total = fee_agg['total'] or 0
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

    recent_admissions = Student.objects.order_by('-join_date')[:5]
    todays_classes = ClassSchedule.objects.filter(date=now.date()).order_by('-id')[:3]
    recent_activities = Activity.objects.order_by('-timestamp')[:5]
    
    student_status_data = list(Student.objects.values('status').annotate(count=Count('status')))
    batch_students_data = list(Batch.objects.annotate(student_count=Count('students', filter=Q(students__approval_status='Approved') & ~Q(students__status='Dropped'))).values('name', 'student_count')[:6])
    
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
    # Auto-fix existing students with missing credentials (username, portal_password, parent_username, parent_password)
    for s in Student.objects.all():
        updated = False
        first_name = s.name.split()[0] if s.name else "Student"
        
        if not s.username or s.username == '-':
            nums_user = "".join(random.choices(string.digits, k=3))
            s.username = f"STU_{first_name}{nums_user}"
            updated = True
            
        if not s.portal_password or s.portal_password == '-':
            upper = random.choices(string.ascii_uppercase, k=2)
            lower = random.choices(string.ascii_lowercase, k=2)
            nums_pwd = random.choices(string.digits, k=3)
            special = random.choices("!@#$%^&*", k=1)
            pwd_list = upper + lower + nums_pwd + special
            random.shuffle(pwd_list)
            s.portal_password = "".join(pwd_list)
            updated = True

        if not s.parent_username or s.parent_username == '-':
            nums_parent = "".join(random.choices(string.digits, k=3))
            s.parent_username = f"P_{first_name}{nums_parent}"
            updated = True

        if not s.parent_password or s.parent_password == '-':
            p_upper = random.choices(string.ascii_uppercase, k=2)
            p_lower = random.choices(string.ascii_lowercase, k=2)
            p_nums = random.choices(string.digits, k=3)
            p_special = random.choices("!@#$%^&*", k=1)
            p_pwd_list = p_upper + p_lower + p_nums + p_special
            random.shuffle(p_pwd_list)
            s.parent_password = "".join(p_pwd_list)
            updated = True

        if not s.course or s.course == '-' or 'Full Stack' in s.course:
            s.course = "Generative AI & LLMs"
            updated = True

        if updated:
            s.save()

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
            'pending': Student.objects.filter(approval_status='Pending').count(),
            'completed': Student.objects.filter(status='Completed').count(),
            'rejected': Student.objects.filter(approval_status='Rejected').count(),
        }
    }
    return render(request, 'students.html', context)

def batches(request):
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    course_filter = request.GET.get('course', '')
    trainer_filter = request.GET.get('trainer', '')

    batches_qs = Batch.objects.all().order_by('-start_date')

    if query:
        batches_qs = batches_qs.filter(Q(name__icontains=query) | Q(course__icontains=query) | Q(trainer__name__icontains=query))
    if status_filter:
        batches_qs = batches_qs.filter(status__iexact=status_filter)
    if course_filter:
        batches_qs = batches_qs.filter(course__iexact=course_filter)
    if trainer_filter:
        batches_qs = batches_qs.filter(trainer__id=trainer_filter)

    paginator = Paginator(batches_qs, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    mentors = AppUser.objects.filter(role='Mentor')
    unassigned_students = Student.objects.filter(batch__isnull=True).exclude(status='Dropped')
    all_batches = Batch.objects.filter(status='Active')

    tot_att = Attendance.objects.count()
    pres_att = Attendance.objects.filter(status='Present').count()
    att_pct_str = f"{int((pres_att / tot_att) * 100)}%" if tot_att > 0 else "0%"

    context = {
        'all_batches': all_batches,
        'unassigned_students': unassigned_students,
        'active_page': 'batches', 
        'batches': page_obj,
        'mentors': mentors,
        'kpi': {
            'total': Batch.objects.count(),
            'active': Batch.objects.filter(status='Active').count(),
            'completed': Batch.objects.filter(status='Completed').count(),
            'enrolled': Student.objects.filter(batch__isnull=False).count(),
            'upcoming': Batch.objects.filter(status='Upcoming').count(),
            'attendance': att_pct_str
        },
        'current_q': query,
        'current_status': status_filter,
        'current_course': course_filter,
        'current_trainer': trainer_filter
    }
    return render(request, 'batches.html', context)

def classes(request):
    classes_raw = list(ClassSchedule.objects.all().select_related('batch', 'trainer').prefetch_related('attendances', 'batch__students'))
    today = timezone.localdate()
    now_time = timezone.localtime().time()

    live_count = 0
    upcoming_count = 0
    past_count = 0
    todays_count = 0

    for c in classes_raw:
        if c.date == today:
            todays_count += 1

        # Real DB attendance calculations
        atts = list(c.attendances.all())
        if atts:
            c.has_attendance = True
            c.present_count = sum(1 for a in atts if a.status == 'Present')
            c.absent_count = sum(1 for a in atts if a.status == 'Absent')
            c.leave_count = sum(1 for a in atts if a.status == 'Leave')
            tot_students = c.batch.students.exclude(status='Dropped').count() if c.batch else len(atts)
            if tot_students == 0:
                tot_students = len(atts)
            c.attendance_pct = int((c.present_count / tot_students) * 100) if tot_students > 0 else 0
        else:
            c.has_attendance = False
            c.present_count = 0
            c.absent_count = 0
            c.leave_count = 0
            c.attendance_pct = 0

        # Slot calculation (Morning, Afternoon, Evening)
        start_t = c.time
        if start_t:
            if start_t.hour < 12:
                c.time_slot = 'Morning'
            elif start_t.hour < 17:
                c.time_slot = 'Afternoon'
            else:
                c.time_slot = 'Evening'
        else:
            c.time_slot = 'Morning'

        # Full Date + Start Time + End Time comparison
        if c.date > today:
            c.session_status = 'Upcoming'
            upcoming_count += 1
        elif c.date < today:
            c.session_status = 'Past'
            past_count += 1
        else: # c.date == today
            end_t = c.end_time

            if start_t and now_time < start_t:
                c.session_status = 'Upcoming'
                upcoming_count += 1
            elif end_t and now_time > end_t:
                c.session_status = 'Past'
                past_count += 1
            elif start_t and end_t and start_t <= now_time <= end_t:
                c.session_status = 'Live Now'
                live_count += 1
            elif start_t and not end_t:
                start_dt = datetime.combine(today, start_t)
                end_dt = start_dt + timedelta(minutes=90)
                if start_t <= now_time <= end_dt.time():
                    c.session_status = 'Live Now'
                    live_count += 1
                elif now_time > end_dt.time():
                    c.session_status = 'Past'
                    past_count += 1
                else:
                    c.session_status = 'Upcoming'
                    upcoming_count += 1
            else:
                c.session_status = 'Upcoming'
                upcoming_count += 1

    # Sorting Hierarchy:
    # 0: Today's classes (sorted by Start Time ascending)
    # 1: Upcoming classes (sorted by Date ascending -> Start Time ascending)
    # 2: Past classes (sorted by Date descending -> Start Time ascending)
    def get_sort_key(c):
        default_time = time(0, 0)
        t = c.time if c.time else default_time
        if c.date == today:
            return (0, c.date, t)
        elif c.date > today:
            return (1, c.date, t)
        else:
            days_ago = (today - c.date).days
            return (2, days_ago, t)

    classes_list = sorted(classes_raw, key=get_sort_key)
    batches = Batch.objects.filter(status='Active').order_by('name')
    
    # Collect all mentors/trainers from both AppUser (role=mentor) and Trainer model
    mentor_users = AppUser.objects.filter(role__icontains='mentor').order_by('name')
    trainer_models = Trainer.objects.all().order_by('name')

    all_mentors_set = {}
    for mu in mentor_users:
        if mu.name and mu.name.strip():
            all_mentors_set[mu.name.strip()] = {'id': mu.name.strip().lower(), 'name': mu.name.strip()}
    for tm in trainer_models:
        if tm.name and tm.name.strip():
            all_mentors_set[tm.name.strip()] = {'id': tm.name.strip().lower(), 'name': tm.name.strip()}

    trainers_list = sorted(list(all_mentors_set.values()), key=lambda x: x['name'])

    context = {
        'active_page': 'classes', 
        'classes': classes_list,
        'batches': batches,
        'trainers_list': trainers_list,
        'kpi': {
            'total': len(classes_list),
            'todays': todays_count,
            'live': live_count,
            'upcoming': upcoming_count,
            'past': past_count,
            'online': ClassSchedule.objects.filter(mode='Online').count(),
            'offline': ClassSchedule.objects.filter(mode='Offline').count(),
            'trainers': len(trainers_list)
        }
    }
    return render(request, 'classes.html', context)

def academic(request):
    phases = CurriculumMonth.objects.prefetch_related('course_modules__topics').all().order_by('number', 'id')
    phases_list = []
    total_modules = 0
    total_topics = 0

    for p in phases:
        mods_list = []
        for m in p.course_modules.all().order_by('order', 'id'):
            total_modules += 1
            tops_list = []
            for t in m.topics.all().order_by('order', 'id'):
                total_topics += 1
                tops_list.append({
                    'id': t.id,
                    'order': t.order,
                    'name': t.name,
                    'description': t.description,
                    'duration': t.duration,
                    'class_type': t.class_type,
                    'status': t.status,
                })
            mods_list.append({
                'id': m.id,
                'phase_id': p.id,
                'order': m.order,
                'name': m.name,
                'description': m.description,
                'topics': tops_list
            })
        phases_list.append({
            'id': p.id,
            'number': p.number,
            'title': p.title,
            'description': p.description,
            'status': p.status,
            'modules': mods_list
        })
    
    first_cm = CourseModule.objects.values_list('course_name', flat=True).first()
    course_title = first_cm or Batch.objects.values_list('course', flat=True).first() or Student.objects.exclude(course__isnull=True).values_list('course', flat=True).first() or "Generative AI & LLMs"

    context = {
        'active_page': 'curriculum',
        'course_title': course_title,
        'phases': phases,
        'phases_json': json.dumps(phases_list),
        'kpi': {
            'total_phases': phases.count(),
            'total_modules': total_modules,
            'total_topics': total_topics,
            'course': course_title,
            'delivery_type': 'Online Class'
        }
    }
    return render(request, 'academic.html', context)

def assessments(request):
    assessments_list = Assessment.objects.all().order_by('-date')
    from django.db.models import Avg
    avg_val = AssessmentResult.objects.aggregate(avg=Avg('marks_obtained'))['avg']
    if avg_val is None:
        avg_val = TaskSubmission.objects.filter(status='Evaluated').aggregate(avg=Avg('marks_obtained'))['avg']
    avg_score_str = f"{int(avg_val)}%" if avg_val is not None else "0%"
    pending_submissions = TaskSubmission.objects.filter(status='Submitted').count()

    context = {
        'active_page': 'assessments', 
        'assessments': assessments_list,
        'kpi': {
            'total': Assessment.objects.count(),
            'avg_score': avg_score_str,
            'pending': pending_submissions,
            'high': AssessmentResult.objects.filter(score__gte=90).count() if hasattr(AssessmentResult, 'score') else 0
        }
    }
    return render(request, 'assessments.html', context)

def fees(request):
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    payments_qs = FeePayment.objects.all().order_by('-payment_date')
    
    if query:
        payments_qs = payments_qs.filter(Q(student__name__icontains=query) | Q(student__student_id__icontains=query) | Q(student__batch__name__icontains=query))
    if status_filter:
        payments_qs = payments_qs.filter(status__iexact=status_filter)
    if start_date:
        payments_qs = payments_qs.filter(payment_date__gte=start_date)
    if end_date:
        payments_qs = payments_qs.filter(payment_date__lte=end_date)
        
    paginator = Paginator(payments_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    paid_qs = payments_qs.filter(status='Paid')
    pending_qs = payments_qs.filter(status='Pending')
    
    total_paid_sum = paid_qs.aggregate(total=Sum('amount'))['total'] or 0
    total_pending_sum = pending_qs.aggregate(total=Sum('amount'))['total'] or 0
    
    kpi = {
        'total_paid_sum': f"₹{total_paid_sum:,.2f}",
        'total_pending_sum': f"₹{total_pending_sum:,.2f}",
        'paid_count': paid_qs.count(),
        'pending_count': pending_qs.count(),
        'total_count': payments_qs.count(),
        'active_batches_count': Batch.objects.count()
    }

    context = {
        'active_page': 'fees',
        'payments': page_obj,
        'kpi': kpi,
        'current_q': query,
        'current_status': status_filter,
        'current_start_date': start_date,
        'current_end_date': end_date
    }
    return render(request, 'fees.html', context)

def reports(request):
    query = request.GET.get('q', '')
    
    students_qs = Student.objects.all().order_by('-join_date')
    if query:
        students_qs = students_qs.filter(Q(name__icontains=query) | Q(student_id__icontains=query) | Q(batch__name__icontains=query))
        
    paginator = Paginator(students_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate some KPIs for the report
    total_students = Student.objects.count()
    active_students = Student.objects.filter(status='Active').count()
    
    context = {
        'active_page': 'reports',
        'students': page_obj,
        'current_q': query,
        'kpi': {
            'total_students': total_students,
            'active_students': active_students
        }
    }
    return render(request, 'reports.html', context)

def users_roles(request):
    query = request.GET.get('q', '')
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')

    from django.db.models import Sum
    users_qs = AppUser.objects.annotate(
        student_count=Count('mentees', filter=Q(mentees__approval_status='Approved') & ~Q(mentees__status='Dropped')),
        total_capacity=Sum('batch__capacity', filter=Q(batch__status='Active'))
    ).order_by('-id')
    
    for u in users_qs:
        if u.total_capacity is None:
            u.total_capacity = 0

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
    if request.method == 'POST':
        action_type = request.POST.get('action_type', 'broadcast')
        if action_type == 'broadcast':
            notif_id = request.POST.get('notif_id')
            title = request.POST.get('title')
            message = request.POST.get('message')
            category = request.POST.get('category', 'System')
            target_group = request.POST.get('target_group', 'All Students')
            
            if notif_id:
                try:
                    notif = Notification.objects.get(id=notif_id)
                    notif.title = title
                    notif.message = message
                    notif.category = category
                    notif.target_group = target_group
                    notif.save()
                except Notification.DoesNotExist:
                    pass
            else:
                Notification.objects.create(
                    title=title,
                    message=message,
                    category=category,
                    target_group=target_group
                )
        elif action_type == 'reply':
            request_id = request.POST.get('request_id')
            reply_msg = request.POST.get('reply_message')
            status = request.POST.get('status')
            try:
                sreq = StudentRequest.objects.get(id=request_id)
                sreq.admin_reply = reply_msg
                sreq.status = status
                sreq.save()
                # Create a notification for the student
                Notification.objects.create(
                    title=f"Reply to your request: {sreq.subject}",
                    message=reply_msg,
                    category='Support Reply',
                    target_group='Specific Student',
                    target_student=sreq.student
                )
            except StudentRequest.DoesNotExist:
                pass
        return redirect('notifications')
    query = request.GET.get('q', '')
    category_filter = request.GET.get('category', '')
    target_filter = request.GET.get('target', '')
    status_filter = request.GET.get('status', '')

    notifs_qs = Notification.objects.all().order_by('-timestamp')

    if query:
        notifs_qs = notifs_qs.filter(Q(title__icontains=query) | Q(message__icontains=query))
    if category_filter:
        notifs_qs = notifs_qs.filter(category__iexact=category_filter)
    if target_filter:
        notifs_qs = notifs_qs.filter(target_group__iexact=target_filter)
    if status_filter == 'read':
        notifs_qs = notifs_qs.filter(is_read=True)
    elif status_filter == 'unread':
        notifs_qs = notifs_qs.filter(is_read=False)

    paginator = Paginator(notifs_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    student_requests = StudentRequest.objects.all().order_by('-created_at')

    kpi = {
        'total': notifs_qs.count(),
        'unread': notifs_qs.filter(is_read=False).count(),
        'fee_alerts': notifs_qs.filter(category='Fee Alert').count(),
        'assessments': notifs_qs.filter(category='Assessments').count(),
        'system': notifs_qs.filter(category='System').count(),
    }

    context = {
        'active_page': 'notifications',
        'notifications': page_obj,
        'student_requests': student_requests,
        'kpi': kpi,
        'current_q': query,
        'current_category': category_filter,
        'current_target': target_filter,
        'current_status': status_filter
    }
    return render(request, 'notifications.html', context)


# =============================================================================
# MENTOR PORTAL CONTROLLERS
# =============================================================================

def parse_time_str(time_str):
    if not time_str:
        return None
    time_str = str(time_str).strip()
    for fmt in ('%I:%M %p', '%I:%M%p', '%H:%M:%S', '%H:%M'):
        try:
            return datetime.strptime(time_str, fmt).time()
        except ValueError:
            pass
    return None

def parse_date_str(date_str):
    if not date_str:
        return None
    if isinstance(date_str, date):
        return date_str
    date_str = str(date_str).strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            pass
    return None

def get_current_mentor(request):
    mentor_id = request.session.get('appuser_id')
    trainer = AppUser.objects.filter(id=mentor_id, role__iexact='mentor').first() if mentor_id else None
    if not trainer:
        user_name_sess = request.session.get('appuser_name')
        if user_name_sess:
            trainer = AppUser.objects.filter(name__iexact=user_name_sess, role__iexact='mentor').first()
    if not trainer:
        trainer = AppUser.objects.filter(role__iexact='mentor').first()
    return trainer

def mentor_dashboard(request):
    trainer = get_current_mentor(request)
    user_name = trainer.name if trainer else request.session.get('appuser_name', '')
    initials = "".join([n[0] for n in user_name.split()[:2]]).upper() if user_name else ''

    mentor_batches_qs = Batch.objects.filter(trainer=trainer) if trainer else Batch.objects.none()

    batches_list = []
    for b in mentor_batches_qs:
        st_count = Student.objects.filter(batch=b).exclude(status='Dropped').count()
        cap = getattr(b, 'capacity', 0) or 0
        percent = min(100, int((st_count / cap) * 100)) if cap > 0 else 0
        b.students_count = st_count
        b.capacity = cap
        b.capacity_percent = percent
        b.timing_lower = (b.timing or '').lower()
        b.program = getattr(b, 'course', None) or ''
        batches_list.append(b)

    students_count = Student.objects.filter(
        batch__in=mentor_batches_qs
    ).exclude(batch__isnull=True).exclude(status='Dropped').distinct().count()

    today = timezone.localdate()
    todays_classes_qs = ClassSchedule.objects.filter(
        Q(trainer=trainer) | Q(batch__in=mentor_batches_qs),
        date=today
    ).select_related('batch', 'trainer').order_by('time')[:3]

    todays_classes = []
    for c in todays_classes_qs:
        c.display_name = c.subject or (c.batch.name if c.batch else '')
        c.time_str = c.time.strftime('%I:%M %p') if c.time else ''
        todays_classes.append(c)

    unread_notifications_count = Notification.objects.filter(
        Q(target_group__in=['All Users', 'Mentor']) | Q(target_group__iexact='all'),
        is_read=False
    ).count()

    pending_eval_qs = TaskSubmission.objects.filter(task__batch__in=mentor_batches_qs, status='Submitted') if mentor_batches_qs.exists() else TaskSubmission.objects.none()

    context = {
        'active_page': 'mentor_dashboard',
        'role': 'mentor',
        'is_mentor': True,
        'user_name': user_name,
        'user_role': 'Mentor',
        'user_initials': initials,
        'date_str': today.strftime('%a, %d %b %Y'),
        'my_students_count': students_count,
        'pending_evaluations_count': pending_eval_qs.count(),
        'pending_evaluations': list(pending_eval_qs[:5]),
        'todays_classes_count': len(todays_classes),
        'todays_classes': todays_classes,
        'my_batches_count': len(batches_list),
        'mentor_batches': batches_list,
        'unread_notifications_count': unread_notifications_count,
    }
    return render(request, 'mentor/dashboard.html', context)

def mentor_students(request):
    trainer = get_current_mentor(request)
    user_name = trainer.name if trainer else request.session.get('appuser_name', 'Mentor')
    initials = "".join([n[0] for n in user_name.split()[:2]]).upper() if user_name else 'M'

    mentor_batches = Batch.objects.filter(trainer=trainer) if trainer else Batch.objects.none()
    students_qs = Student.objects.filter(
        batch__in=mentor_batches
    ).exclude(batch__isnull=True).exclude(status='Dropped').distinct().select_related('batch')

    # KPI Data Calculations
    total_students_count = students_qs.count()
    active_students_count = students_qs.filter(status='Active').count()
    
    total_attendance_pct = 0
    needs_attention_count = 0

    students = []
    for s in students_qs:
        # Calculate attendance based on classes created for the batch
        batch_total_classes = s.batch.classes.count() if s.batch else 0
        attendances = s.attendances.all()
        present = attendances.filter(status='Present').count()
        leave = attendances.filter(status='Leave').count()
        
        # Absent is the difference between total created classes and present/leave records
        # Fallback to explicit absent records if no batch or weird data
        explicit_absent = attendances.filter(status='Absent').count()
        
        total_classes = batch_total_classes if batch_total_classes > 0 else (present + leave + explicit_absent)
        absent = total_classes - present - leave
        if absent < 0:
            absent = explicit_absent
            total_classes = present + leave + absent
        
        rate = 0
        if total_classes > 0:
            rate = round((present / total_classes) * 100)
            
        s.attendance_rate = rate
        s.classes_summary = f"{present} / {leave} / {absent}"
        students.append(s)
        
        total_attendance_pct += rate
        if rate < 75 and total_classes > 0:
            needs_attention_count += 1
            
    avg_attendance = int(total_attendance_pct / total_students_count) if total_students_count > 0 else 0

    # Batches Data
    batches_data = []
    for b in mentor_batches:
        b_count = sum(1 for s in students if s.batch == b)
        batches_data.append({
            'name': b.name,
            'student_count': b_count,
            'timing': b.timing
        })

    context = {
        'active_page': 'mentor_students',
        'role': 'mentor',
        'is_mentor': True,
        'user_name': user_name,
        'user_role': 'Mentor',
        'user_initials': initials,
        'students': students,
        'batches': mentor_batches,
        'total_students_count': total_students_count,
        'active_students_count': active_students_count,
        'avg_attendance': avg_attendance,
        'needs_attention_count': needs_attention_count,
        'batches_data': batches_data,
    }
    return render(request, 'mentor/students.html', context)

def mentor_student_detail(request, student_id):
    trainer = get_current_mentor(request)
    user_name = trainer.name if trainer else request.session.get('appuser_name', '')
    initials = "".join([n[0] for n in user_name.split()[:2]]).upper() if user_name else ''
    student = Student.objects.filter(student_id=student_id).first()
    evaluations = list(TaskSubmission.objects.filter(student=student).order_by('-submitted_at')) if student else []
    attendance_records = list(Attendance.objects.filter(student=student).order_by('-date')) if student else []

    context = {
        'active_page': 'mentor_students',
        'role': 'mentor',
        'is_mentor': True,
        'user_name': user_name,
        'user_role': 'Mentor',
        'user_initials': initials,
        'student': student,
        'evaluations': evaluations,
        'attendance_records': attendance_records,
    }
    return render(request, 'mentor/student_detail.html', context)

def mentor_curriculum(request):
    trainer = get_current_mentor(request)
    user_name = trainer.name if trainer else request.session.get('appuser_name', '')
    initials = "".join([n[0] for n in user_name.split()[:2]]).upper() if user_name else ''
    
    modules = CourseModule.objects.prefetch_related('topics').all().order_by('order', 'id')
    modules_list = []
    total_topics = 0
    for m in modules:
        topics_list = []
        for t in m.topics.all().order_by('order', 'id'):
            topics_list.append({
                'id': t.id,
                'order': t.order,
                'name': t.name,
                'description': t.description,
                'duration': t.duration,
                'class_type': t.class_type,
                'status': t.status,
            })
            total_topics += 1
        modules_list.append({
            'id': m.id,
            'order': m.order,
            'name': m.name,
            'description': m.description,
            'topics': topics_list
        })

    first_cm = CourseModule.objects.values_list('course_name', flat=True).first()
    course_title = first_cm or Batch.objects.values_list('course', flat=True).first() or ""

    context = {
        'active_page': 'mentor_curriculum',
        'role': 'mentor',
        'is_mentor': True,
        'user_name': user_name,
        'user_role': 'Mentor',
        'user_initials': initials,
        'course_title': course_title,
        'modules': modules,
        'modules_json': json.dumps(modules_list),
        'kpi': {
            'total_modules': modules.count(),
            'total_topics': total_topics,
            'course': course_title,
            'delivery_type': 'Online Class'
        }
    }
    return render(request, 'mentor/curriculum.html', context)

def mentor_classes(request):
    trainer = get_current_mentor(request)
    user_name = trainer.name if trainer else request.session.get('appuser_name', 'Mentor')
    initials = "".join([n[0] for n in user_name.split()[:2]]).upper() if user_name else 'M'

    mentor_batches = Batch.objects.filter(trainer=trainer) if trainer else Batch.objects.none()

    # ONLY students belonging to batches where Batch.trainer = logged-in mentor
    students_qs = Student.objects.filter(
        batch__in=mentor_batches
    ).exclude(batch__isnull=True).exclude(status='Dropped').distinct()
    students_count = students_qs.count()

    # Query ClassSchedule
    all_classes_qs = ClassSchedule.objects.filter(
        Q(trainer=trainer) | Q(batch__in=mentor_batches)
    ).select_related('batch', 'trainer').distinct().order_by('date', 'time')

    today = timezone.localdate()
    now_dt = timezone.localtime()
    now_time = now_dt.time()

    today_classes = []
    upcoming_classes = []
    past_classes = []

    for c in all_classes_qs:
        # Properties session and session_lower are dynamically calculated by the ClassSchedule model
        c.duration = '90 Mins'

        if c.date == today:
            today_classes.append(c)
        elif c.date > today:
            upcoming_classes.append(c)
        else:
            past_classes.append(c)

    past_this_month = [c for c in past_classes if c.date and c.date.year == today.year and c.date.month == today.month]

    kpi = {
        'today': len(today_classes),
        'upcoming': len(upcoming_classes),
        'past': len(past_this_month),
        'completed': len(past_this_month),
        'students': students_count,
    }

    # Admin course modules for Schedule New Class dropdown
    course_modules = CourseModule.objects.prefetch_related('topics').all().order_by('order', 'id')
    modules_data = []
    for m in course_modules:
        topics_list = []
        for t in m.topics.all().order_by('order', 'id'):
            topics_list.append({
                'id': t.id,
                'name': t.name,
                'duration': t.duration,
                'description': t.description or '',
                'moduleId': m.id,
            })
        modules_data.append({
            'id': m.id,
            'order': m.order,
            'name': m.name,
            'topics': topics_list,
        })
    modules_json = json.dumps(modules_data)

    # Injected dynamic calendar classes
    calendar_classes = []
    for c in all_classes_qs:
        calendar_classes.append({
            'id': c.id,
            'date': c.date.strftime('%Y-%m-%d') if c.date else '',
            'subject': c.subject,
            'batch_name': c.batch.name if c.batch else 'General Batch',
            'time': c.time.strftime('%I:%M %p') if c.time else '',
            'end_time': c.end_time.strftime('%I:%M %p') if c.end_time else '',
            'mode': c.mode,
        })
    calendar_classes_json = json.dumps(calendar_classes)

    batches_list = list(mentor_batches) if mentor_batches.exists() else list(Batch.objects.filter(status='Active'))

    context = {
        'active_page': 'mentor_classes',
        'role': 'mentor',
        'is_mentor': True,
        'user_name': user_name,
        'user_role': 'Mentor',
        'user_initials': initials,
        'today': today,
        'today_classes': today_classes,
        'upcoming_classes': upcoming_classes,
        'past_classes': past_this_month,
        'kpi': kpi,
        'batches': batches_list,
        'course_modules': course_modules,
        'modules_json': modules_json,
        'calendar_classes_json': calendar_classes_json,
    }
    return render(request, 'mentor/classes.html', context)


def mentor_attendance(request, class_id=None):
    return redirect('mentor_students')

def mentor_tasks(request):
    trainer = get_current_mentor(request)
    user_name = trainer.name if trainer else request.session.get('appuser_name', 'Mentor')
    initials = "".join([n[0] for n in user_name.split()[:2]]).upper() if user_name else 'M'
    
    my_batches = Batch.objects.filter(trainer=trainer, status='Active') if trainer else Batch.objects.filter(status='Active')
    tasks = Task.objects.filter(batch__in=my_batches).order_by('-created_at')
    
    # Calculate stats
    total_tasks = tasks.count()
    awaiting_grading = TaskSubmission.objects.filter(task__in=tasks, status='Submitted').count()
    evaluated = TaskSubmission.objects.filter(task__in=tasks, status='Evaluated').count()
    
    context = {
        'active_page': 'mentor_tasks',
        'role': 'mentor',
        'is_mentor': True,
        'user_name': user_name,
        'user_role': 'Faculty Mentor',
        'user_initials': initials,
        'tasks': tasks,
        'my_batches': my_batches,
        'kpi': {
            'total': total_tasks,
            'awaiting': awaiting_grading,
            'evaluated': evaluated,
            'overdue': 0
        }
    }
    return render(request, 'mentor/tasks.html', context)

def mentor_evaluations(request, task_id=None):
    trainer = get_current_mentor(request)
    user_name = trainer.name if trainer else request.session.get('appuser_name', '')
    initials = "".join([n[0] for n in user_name.split()[:2]]).upper() if user_name else ''
    user_role = trainer.role if (trainer and hasattr(trainer, 'role') and trainer.role) else 'Mentor'
    
    submissions_qs = TaskSubmission.objects.all().order_by('-submitted_at')
    if task_id:
        submissions_qs = submissions_qs.filter(task_id=task_id)
    elif trainer:
        submissions_qs = submissions_qs.filter(task__batch__trainer=trainer)

    context = {
        'active_page': 'mentor_tasks',
        'role': 'mentor',
        'is_mentor': True,
        'user_name': user_name,
        'user_role': user_role,
        'user_initials': initials,
        'submissions': list(submissions_qs)
    }
    return render(request, 'mentor/evaluations.html', context)

def mentor_academic(request):
    return redirect('mentor_students')

def mentor_assessments(request):
    trainer = get_current_mentor(request)
    user_name = trainer.name if trainer else request.session.get('appuser_name', '')
    initials = "".join([n[0] for n in user_name.split()[:2]]).upper() if user_name else ''
    user_role = trainer.role if (trainer and hasattr(trainer, 'role') and trainer.role) else 'Mentor'
    
    assessments_qs = Assessment.objects.all().order_by('-date')

    context = {
        'active_page': 'mentor_assessments',
        'role': 'mentor',
        'is_mentor': True,
        'user_name': user_name,
        'user_role': user_role,
        'user_initials': initials,
        'assessments': list(assessments_qs)
    }
    return render(request, 'mentor/assessments.html', context)

def mentor_assessment_detail(request, assessment_id):
    trainer = get_current_mentor(request)
    user_name = trainer.name if trainer else request.session.get('appuser_name', '')
    initials = "".join([n[0] for n in user_name.split()[:2]]).upper() if user_name else ''
    user_role = trainer.role if (trainer and hasattr(trainer, 'role') and trainer.role) else 'Mentor'
    
    asm = Assessment.objects.filter(id=assessment_id).first()
    results = list(AssessmentResult.objects.filter(assessment=asm)) if asm else []

    context = {
        'active_page': 'mentor_assessments',
        'role': 'mentor',
        'is_mentor': True,
        'user_name': user_name,
        'user_role': user_role,
        'user_initials': initials,
        'assessment': asm,
        'student_results': results
    }
    return render(request, 'mentor/assessment_detail.html', context)

def mentor_placement(request):
    trainer = get_current_mentor(request)
    user_name = trainer.name if trainer else request.session.get('appuser_name', '')
    initials = "".join([n[0] for n in user_name.split()[:2]]).upper() if user_name else ''
    user_role = trainer.role if (trainer and hasattr(trainer, 'role') and trainer.role) else 'Mentor'
    
    my_batches = Batch.objects.filter(trainer=trainer) if trainer else Batch.objects.none()
    students_qs = Student.objects.filter(batch__in=my_batches).exclude(status='Dropped') if trainer else Student.objects.none()

    context = {
        'active_page': 'mentor_placement',
        'role': 'mentor',
        'is_mentor': True,
        'user_name': user_name,
        'user_role': user_role,
        'user_initials': initials,
        'students': list(students_qs)
    }
    return render(request, 'mentor/placement.html', context)

def mentor_reports(request):
    trainer = get_current_mentor(request)
    user_name = trainer.name if trainer else request.session.get('appuser_name', '')
    initials = "".join([n[0] for n in user_name.split()[:2]]).upper() if user_name else ''
    user_role = trainer.role if (trainer and hasattr(trainer, 'role') and trainer.role) else 'Mentor'
    
    my_batches = Batch.objects.filter(trainer=trainer) if trainer else Batch.objects.none()
    students_qs = Student.objects.filter(batch__in=my_batches).exclude(status='Dropped') if trainer else Student.objects.none()

    context = {
        'active_page': 'mentor_reports',
        'role': 'mentor',
        'is_mentor': True,
        'user_name': user_name,
        'user_role': user_role,
        'user_initials': initials,
        'students': list(students_qs),
        'attendance_trend': [],
        'subject_mastery': []
    }
    return render(request, 'mentor/reports.html', context)

def mentor_notifications(request):
    trainer = get_current_mentor(request)
    user_name = trainer.name if trainer else request.session.get('appuser_name', 'Mentor')
    initials = "".join([n[0] for n in user_name.split()[:2]]).upper() if user_name else 'M'
    
    my_batches = Batch.objects.filter(trainer=trainer, status='Active') if trainer else Batch.objects.filter(status='Active')
    my_batch_ids = list(my_batches.values_list('id', flat=True))
    my_students = Student.objects.filter(batch__in=my_batches).exclude(status='Dropped').order_by('name').select_related('batch')
    my_student_ids = list(my_students.values_list('id', flat=True))
    
    notifications = Notification.objects.filter(
        Q(direction='question', sender_student__batch__id__in=my_batch_ids) |
        Q(direction='sent', sender_mentor=trainer) |
        Q(sender_mentor__isnull=True, sender_student__isnull=True) |
        Q(sender_mentor__isnull=True, target_group__in=['All Users', 'All Students', 'Mentor', 'All Mentors']) |
        Q(sender_mentor__isnull=True, target_student__id__in=my_student_ids)
    ).select_related('sender_student', 'sender_student__batch', 'target_student', 'target_student__batch', 'sender_mentor').order_by('-timestamp').distinct()[:100]
    
    context = {
        'active_page': 'mentor_notifications',
        'role': 'mentor',
        'is_mentor': True,
        'user_name': user_name,
        'user_initials': initials,
        'my_batches': my_batches,
        'my_students': my_students,
        'notifications': notifications,
    }
    return render(request, 'mentor/notifications.html', context)

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        print(f"DEBUG LOGIN: username='{username}', password='{password}'")
        role = request.POST.get('role', 'admin') # if they selected a role in the UI
        
        # 1. Check Django Superuser
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_superuser:
                login(request, user)
                return redirect('dashboard')
            else:
                return render(request, 'login.html', {'error': 'Only administrators can access the admin control center.'})
        
        # 2. Check Parent (Student model)
        if role == 'parent':
            try:
                student = Student.objects.get(parent_username=username, parent_password=password)
                request.session['parent_student_id'] = student.student_id
                request.session['role'] = 'Parent'
                # Redirect to a generic place or parent portal
                return redirect('students') # Temporary redirect for parent
            except Student.DoesNotExist:
                return render(request, 'login.html', {'error': 'Invalid username or password.'})

        # 3. Check AppUser (Mentor/Accountant)
        try:
            appuser = AppUser.objects.get(username=username, portal_password=password)
            if appuser.status.lower() == 'blocked':
                return render(request, 'login.html', {'error': 'This account has been blocked.'})
            
            # Set custom session variables
            request.session['appuser_id'] = appuser.id
            request.session['appuser_role'] = appuser.role
            request.session['appuser_name'] = appuser.name
            
            if appuser.role.lower() == 'mentor':
                return redirect('mentor_dashboard')
            else:
                return render(request, 'login.html', {'error': f'Dashboard for {appuser.role} is not available yet.'})
                
        except AppUser.DoesNotExist:
            return render(request, 'login.html', {'error': 'Invalid username or password.'})

    return render(request, 'login.html')

def mentor_batches(request):
    return redirect('mentor_students')

def mentor_task_detail(request, task_id):
    trainer = get_current_mentor(request)
    user_name = trainer.name if trainer else request.session.get('appuser_name', 'Mentor')
    initials = "".join([n[0] for n in user_name.split()[:2]]).upper() if user_name else 'M'
    
    try:
        task = Task.objects.get(id=task_id)
        submissions = task.submissions.all().order_by('-submitted_at')
    except Task.DoesNotExist:
        return redirect('mentor_tasks')
        
    context = {
        'active_page': 'mentor_tasks',
        'role': 'mentor',
        'is_mentor': True,
        'user_name': user_name,
        'user_role': 'Faculty Mentor',
        'user_initials': initials,
        'task': task,
        'submissions': submissions
    }
    return render(request, 'mentor/task_detail.html', context)


def placement(request):
    offers = PlacementOffer.objects.all().order_by('-offer_date')
    from django.db.models import Avg
    avg_val = PlacementOffer.objects.aggregate(avg=Avg('package'))['avg']
    avg_pkg_str = f"₹{avg_val:.1f} LPA" if avg_val is not None else "₹0 LPA"
    context = {
        'active_page': 'placement', 
        'offers': offers,
        'kpi': {
            'total': PlacementOffer.objects.filter(status='Accepted').count(),
            'extended': PlacementOffer.objects.count(),
            'interviews': PlacementOffer.objects.filter(status='Pending').count(),
            'avg_pkg': avg_pkg_str
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
            
            first_name = student.name.split()[0] if student.name else "Student"
            if not student.username or student.username == '-':
                # Generate username: STU_firstname + 3 numbers
                nums_user = "".join(random.choices(string.digits, k=3))
                student.username = f"STU_{first_name}{nums_user}"
                
            if not student.portal_password or student.portal_password == '-':
                # Generate password: 2 upper, 2 lower, 3 digits, 1 special
                upper = random.choices(string.ascii_uppercase, k=2)
                lower = random.choices(string.ascii_lowercase, k=2)
                nums_pwd = random.choices(string.digits, k=3)
                special = random.choices("!@#$%^&*", k=1)
                pwd_list = upper + lower + nums_pwd + special
                random.shuffle(pwd_list)
                student.portal_password = "".join(pwd_list)
            
            if not student.parent_username or student.parent_username == '-':
                # Auto-generate Parent credentials: P_firstname + 3 numbers
                nums_parent = "".join(random.choices(string.digits, k=3))
                student.parent_username = f"P_{first_name}{nums_parent}"
                
            if not student.parent_password or student.parent_password == '-':
                p_upper = random.choices(string.ascii_uppercase, k=2)
                p_lower = random.choices(string.ascii_lowercase, k=2)
                p_nums = random.choices(string.digits, k=3)
                p_special = random.choices("!@#$%^&*", k=1)
                p_pwd_list = p_upper + p_lower + p_nums + p_special
                random.shuffle(p_pwd_list)
                student.parent_password = "".join(p_pwd_list)

            student.approval_status = 'Approved'
            student.status = 'Active'
            
            # Batch Assignment Logic (Based on Timing and Capacity)
            target_timing = student.timing_preference or 'Morning'
            matching_batches = Batch.objects.filter(status='Active', timing=target_timing)
            assigned_batch = None
            
            for b in matching_batches:
                enrolled_count = b.students.filter(approval_status='Approved').exclude(status='Dropped').count()
                if enrolled_count < b.capacity:
                    assigned_batch = b
                    break
                    
            if not assigned_batch:
                assigned_batch = Batch.objects.filter(timing=target_timing).first() or Batch.objects.first()
                
            student.batch = assigned_batch
            if assigned_batch and assigned_batch.trainer:
                student.mentor = assigned_batch.trainer
                
            student.save()
            
            return JsonResponse({
                'success': True,
                'username': student.username,
                'password': student.portal_password,
                'parent_username': student.parent_username,
                'parent_password': student.parent_password,
                'batch': student.batch.name if student.batch else '-'
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
            student.status = 'Blocked'
            student.approval_status = 'Blocked'
            student.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False})


@csrf_exempt
def api_unblock_student(request, student_id):
    if request.method == 'POST':
        try:
            student = Student.objects.get(student_id=student_id)
            student.status = 'Active'
            student.approval_status = 'Approved'
            student.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False})

@csrf_exempt
def api_add_student(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            student_id = data.get('student_id') or f"NIM-{timezone.now().year}-{random.randint(10000, 99999)}"
            name = data.get('name', '')
            first_name = name.split()[0] if name else "Student"
            
            username = data.get('username') or f"STU_{first_name}{''.join(random.choices(string.digits, k=3))}"
            
            if data.get('password'):
                portal_password = data.get('password')
            else:
                upper = random.choices(string.ascii_uppercase, k=2)
                lower = random.choices(string.ascii_lowercase, k=2)
                nums_pwd = random.choices(string.digits, k=3)
                special = random.choices("!@#$%^&*", k=1)
                pwd_list = upper + lower + nums_pwd + special
                random.shuffle(pwd_list)
                portal_password = "".join(pwd_list)
                
            parent_username = data.get('parent_username') or f"P_{first_name}{''.join(random.choices(string.digits, k=3))}"
            
            if data.get('parent_password'):
                parent_password = data.get('parent_password')
            else:
                p_upper = random.choices(string.ascii_uppercase, k=2)
                p_lower = random.choices(string.ascii_lowercase, k=2)
                p_nums = random.choices(string.digits, k=3)
                p_special = random.choices("!@#$%^&*", k=1)
                p_pwd_list = p_upper + p_lower + p_nums + p_special
                random.shuffle(p_pwd_list)
                parent_password = "".join(p_pwd_list)

            student = Student.objects.create(
                student_id=student_id,
                name=name,
                email=data.get('email', ''),
                phone=data.get('phone', ''),
                username=username,
                portal_password=portal_password,
                parent_username=parent_username,
                parent_password=parent_password,
                course=data.get('course') or data.get('program') or 'Generative AI & LLMs',
                approval_status='Approved',
                status='Active',
                join_date=timezone.now().date()
            )
            return JsonResponse({'success': True, 'student_id': student.student_id})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False})

@csrf_exempt
def api_register_student(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            student_id = data.get('student_id') or data.get('registrationId') or f"NIM-{timezone.now().year}-{random.randint(10000, 99999)}"
            name = data.get('name') or data.get('fullName', '')
            email = data.get('email', '')
            phone = data.get('phone', '')
            dob = data.get('dob', '')
            guardian_name = data.get('guardian_name') or data.get('guardianName', '')
            guardian_phone = data.get('guardian_phone') or data.get('guardianPhone', '')
            address = data.get('address', '')
            timing_pref = data.get('timing_preference') or data.get('batchTiming') or ''
            plan = data.get('plan') or ''
            amount = data.get('amount') or 0.0
            payment_method = data.get('payment_method') or data.get('paymentMethod') or 'UPI'
            transaction_id = data.get('transaction_id') or data.get('transactionId') or f"TXN-{random.randint(10000000, 99999999)}"
            course = data.get('course') or data.get('program') or 'Generative AI & LLMs'

            student = Student.objects.create(
                student_id=student_id,
                name=name,
                email=email,
                phone=phone,
                timing_preference=timing_pref,
                username=None,
                portal_password=None,
                parent_username=None,
                parent_password=None,
                course=course,
                batch=None,
                approval_status='Pending',
                status='Onboarding',
                join_date=timezone.now().date()
            )

            try:
                amount_num = float(amount)
            except (TypeError, ValueError):
                amount_num = 0.0

            balance_due = max(0.0, float(data.get('balance_due', 0.0)))

            FeePayment.objects.create(
                student=student,
                amount=amount_num,
                balance_due=balance_due,
                payment_method=payment_method,
                transaction_id=transaction_id,
                status='Paid',
                payment_date=timezone.now().date()
            )

            return JsonResponse({
                'success': True,
                'message': 'Registration submitted successfully! Awaiting admin approval.',
                'student_id': student.student_id,
                'approval_status': 'Pending',
                'transaction_id': transaction_id
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

@csrf_exempt
def api_auth_login(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = (data.get('username') or data.get('emailOrPhone') or '').strip()
            password = (data.get('password') or '').strip()
            role = (data.get('role') or 'student').lower()

            if not username or not password:
                return JsonResponse({'success': False, 'error': 'Please enter username/email and password.'}, status=400)

            if role == 'parent':
                # Check Student model for Parent credentials
                try:
                    student = Student.objects.get(
                        Q(parent_username__iexact=username) | Q(email__iexact=username) | Q(phone__exact=username),
                        parent_password=password
                    )
                    if student.approval_status != 'Approved':
                        return JsonResponse({'success': False, 'error': 'Student registration is pending Admin approval. Login will be enabled after approval.'}, status=403)
                    
                    return JsonResponse({
                        'success': True,
                        'role': 'parent',
                        'student_id': student.student_id,
                        'student_name': student.name,
                        'parent_username': student.parent_username
                    })
                except Student.DoesNotExist:
                    return JsonResponse({'success': False, 'error': 'Invalid Parent Username or Password.'}, status=401)

            else:
                # Student role
                try:
                    student = Student.objects.get(
                        Q(username__iexact=username) | Q(email__iexact=username) | Q(phone__exact=username) | Q(student_id__iexact=username),
                        portal_password=password
                    )
                    if student.approval_status != 'Approved':
                        return JsonResponse({'success': False, 'error': 'Your registration is pending Admin approval. Login credentials will be activated once approved.'}, status=403)
                    
                    if student.status == 'Blocked':
                        return JsonResponse({'success': False, 'error': 'Your student account has been blocked by Admin.'}, status=403)

                    return JsonResponse({
                        'success': True,
                        'role': 'student',
                        'student_id': student.student_id,
                        'name': student.name,
                        'email': student.email,
                        'username': student.username,
                        'course': student.course,
                        'batch': student.batch.name if student.batch else ''
                    })
                except Student.DoesNotExist:
                    return JsonResponse({'success': False, 'error': 'Invalid Student Username or Password.'}, status=401)

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

@csrf_exempt
def api_student_dashboard_data(request, student_id=None):
    if not student_id:
        student_id = request.GET.get('student_id') or request.GET.get('username')
        
    student = None
    if student_id:
        student = Student.objects.filter(
            Q(student_id__iexact=student_id) | Q(username__iexact=student_id) | Q(email__iexact=student_id)
        ).first()

    if not student:
        student = Student.objects.filter(approval_status='Approved').first() or Student.objects.first()

    if not student:
        return JsonResponse({'success': False, 'error': 'No student records found'}, status=404)

    # 1. Student Info
    batch_name = student.batch.name if student.batch else (student.timing_preference or '')
    timing = student.timing_preference or (student.batch.timing if student.batch else '')
    
    # 2. Attendance stats
    tot_att = Attendance.objects.filter(student=student).count()
    pres_att = Attendance.objects.filter(student=student, status='Present').count()
    att_percent = round((pres_att / tot_att * 100), 1) if tot_att > 0 else 0.0

    # 3. Upcoming Classes
    classes_qs = ClassSchedule.objects.all().order_by('date', 'time')[:3]
    classes_data = []
    for c in classes_qs:
        classes_data.append({
            'id': c.id,
            'subject': c.subject,
            'batch_name': c.batch.name if c.batch else batch_name,
            'date': c.date.strftime("%d %b %Y") if c.date else "",
            'time': c.time.strftime("%I:%M %p") if c.time else "",
            'duration': c.duration or "",
            'meeting_link': c.meeting_link or "",
            'mode': c.mode
        })

    # 4. Fee Details
    latest_fee = FeePayment.objects.filter(student=student).order_by('-payment_date').first()
    fee_data = {
        'amount': float(latest_fee.amount) if latest_fee else 0.0,
        'balance_due': float(latest_fee.balance_due) if latest_fee else 0.0,
        'status': latest_fee.status if latest_fee else '',
        'transaction_id': latest_fee.transaction_id if latest_fee else ''
    }

    # 5. Tasks/Assignments
    tasks_qs = Task.objects.all().order_by('-created_at')[:4]
    tasks_data = []
    for t in tasks_qs:
        sub = TaskSubmission.objects.filter(task=t, student=student).first()
        tasks_data.append({
            'id': t.id,
            'title': t.title,
            'subject': t.subject,
            'due_date': t.due_date.strftime("%d %b %Y") if t.due_date else "",
            'status': sub.status if sub else 'Pending',
            'grade': sub.marks if sub else None
        })

    return JsonResponse({
        'success': True,
        'student': {
            'student_id': student.student_id,
            'name': student.name,
            'email': student.email,
            'phone': student.phone,
            'username': student.username,
            'course': student.course or "",
            'batch': batch_name,
            'timing': timing,
            'status': student.status,
            'approval_status': student.approval_status,
            'join_date': student.join_date.strftime("%d %b %Y") if student.join_date else "",
            'attendance_percent': att_percent,
        },
        'classes': classes_data,
        'fee': fee_data,
        'tasks': tasks_data,
    })

def get_student_obj(student_id):
    if not student_id:
        return Student.objects.filter(approval_status='Approved').first() or Student.objects.first()
    st = Student.objects.filter(
        Q(student_id__iexact=student_id) | Q(username__iexact=student_id) | Q(email__iexact=student_id)
    ).first()
    if not st:
        st = Student.objects.filter(approval_status='Approved').first() or Student.objects.first()
    return st

@csrf_exempt
def api_student_profile(request, student_id=None):
    student = get_student_obj(student_id)
    if not student:
        return JsonResponse({'success': False, 'error': 'Student not found'}, status=404)

    return JsonResponse({
        'success': True,
        'student': {
            'student_id': student.student_id,
            'name': student.name,
            'email': student.email,
            'phone': student.phone,
            'username': student.username or "",
            'parent_username': student.parent_username or "",
            'parent_name': getattr(student, 'parent_name', '') or getattr(student, 'guardian_name', '') or "",
            'course': student.course or "",
            'batch': student.batch.name if student.batch else (student.timing_preference or ""),
            'timing': student.timing_preference or "",
            'status': student.status,
            'approval_status': student.approval_status,
            'join_date': student.join_date.strftime("%d %b %Y") if student.join_date else "",
            'mentor': student.mentor.name if student.mentor else ""
        }
    })

@csrf_exempt
def api_student_curriculum(request, student_id=None):
    student = get_student_obj(student_id)
    months_qs = CurriculumMonth.objects.all().order_by('number')
    months_data = []
    
    for m in months_qs:
        modules_data = []
        for mod in m.modules.all():
            topics_data = []
            for top in mod.topics.all():
                topics_data.append({
                    'id': top.id,
                    'title': top.title,
                    'description': top.description,
                    'type': top.type,
                    'duration': top.duration,
                    'status': top.status
                })
            modules_data.append({
                'id': mod.id,
                'code': mod.code,
                'title': mod.title,
                'week_range': mod.week_range,
                'status': mod.status,
                'learning_objectives': mod.learning_objectives,
                'topics': topics_data
            })
        months_data.append({
            'id': m.id,
            'number': m.number,
            'title': m.title,
            'description': m.description,
            'status': m.status,
            'modules': modules_data
        })
        
    return JsonResponse({
        'success': True,
        'course': student.course if student else "",
        'months': months_data
    })

@csrf_exempt
def api_student_classes_list(request, student_id=None):
    student = get_student_obj(student_id)
    classes_qs = ClassSchedule.objects.all().order_by('-date', 'time')
    if student and student.batch:
        classes_qs = classes_qs.filter(Q(batch=student.batch) | Q(batch__isnull=True))
        
    classes_data = []
    for c in classes_qs:
        classes_data.append({
            'id': c.id,
            'subject': c.subject,
            'batch': c.batch.name if c.batch else "",
            'date': c.date.strftime("%Y-%m-%d") if c.date else "",
            'date_formatted': c.date.strftime("%d %b %Y") if c.date else "",
            'time': c.time.strftime("%I:%M %p") if c.time else "",
            'end_time': c.get_end_time().strftime("%I:%M %p") if c.get_end_time() else "",
            'duration': c.duration or "",
            'description': c.description,
            'mode': c.mode,
            'meeting_link': c.meeting_link or "",
            'status': c.get_status(),
            'trainer': c.trainer.name if c.trainer else ""
        })
        
    return JsonResponse({
        'success': True,
        'classes': classes_data
    })

@csrf_exempt
def api_student_tasks_list(request, student_id=None):
    student = get_student_obj(student_id)
    tasks_qs = Task.objects.all().order_by('-due_date')
    if student and student.batch:
        tasks_qs = tasks_qs.filter(Q(batch=student.batch) | Q(batch__isnull=True))

    tasks_data = []
    for t in tasks_qs:
        sub = TaskSubmission.objects.filter(task=t, student=student).first() if student else None
        tasks_data.append({
            'id': t.id,
            'title': t.title,
            'subject': getattr(t, 'subject', t.module_code),
            'category': t.category,
            'module_code': t.module_code,
            'description': t.description,
            'max_marks': t.max_marks,
            'due_date': t.due_date.strftime("%d %b %Y") if t.due_date else "",
            'submission_status': sub.status if sub else 'Pending',
            'submitted_at': sub.submitted_at.strftime("%d %b %Y %I:%M %p") if (sub and sub.submitted_at) else None,
            'marks_obtained': sub.marks_obtained if sub else None,
            'feedback': sub.mentor_feedback if sub else None
        })
        
    return JsonResponse({
        'success': True,
        'tasks': tasks_data
    })

@csrf_exempt
def api_student_attendance_list(request, student_id=None):
    student = get_student_obj(student_id)
    if not student:
        return JsonResponse({'success': False, 'records': [], 'stats': {}}, status=404)
        
    att_qs = Attendance.objects.filter(student=student).order_by('-date')
    records = []
    present_count = 0
    absent_count = 0
    late_count = 0
    
    for a in att_qs:
        if a.status == 'Present':
            present_count += 1
        elif a.status == 'Absent':
            absent_count += 1
        elif a.status == 'Late':
            late_count += 1
            
        records.append({
            'id': a.id,
            'date': a.date.strftime("%d %b %Y"),
            'status': a.status,
            'subject': a.class_schedule.subject if a.class_schedule else "",
            'batch': a.batch.name if a.batch else (student.batch.name if student.batch else "")
        })
        
    total = len(records)
    rate = round((present_count / total * 100), 1) if total > 0 else 0.0
    
    return JsonResponse({
        'success': True,
        'records': records,
        'stats': {
            'total_sessions': total,
            'present_count': present_count,
            'absent_count': absent_count,
            'late_count': late_count,
            'attendance_rate': rate
        }
    })

@csrf_exempt
def api_student_career(request, student_id=None):
    student = get_student_obj(student_id)
    offers_qs = PlacementOffer.objects.filter(student=student).order_by('-offer_date') if student else []
    offers_data = []
    for o in offers_qs:
        offers_data.append({
            'id': o.id,
            'company': o.company,
            'offer_date': o.offer_date.strftime("%d %b %Y")
        })

    att_tot = Attendance.objects.filter(student=student).count() if student else 0
    att_pres = Attendance.objects.filter(student=student, status='Present').count() if student else 0
    readiness = int((att_pres / att_tot) * 100) if att_tot > 0 else 0
        
    return JsonResponse({
        'success': True,
        'student_id': student.student_id if student else "",
        'student_name': student.name if student else "",
        'course': student.course if student else "",
        'offers': offers_data,
        'portfolio_status': 'Complete' if (student and student.approval_status == 'Approved') else 'In Progress',
        'readiness_score': readiness
    })

@csrf_exempt
def api_student_fees_list(request, student_id=None):
    student = get_student_obj(student_id)
    if not student:
        return JsonResponse({'success': False, 'payments': []}, status=404)
        
    payments_qs = FeePayment.objects.filter(student=student).order_by('-payment_date')
    payments_data = []
    total_paid = 0.0
    balance_due = 0.0
    
    for p in payments_qs:
        total_paid += float(p.amount)
        balance_due = float(p.balance_due)
        payments_data.append({
            'id': p.id,
            'amount': float(p.amount),
            'balance_due': float(p.balance_due),
            'payment_method': p.payment_method,
            'transaction_id': p.transaction_id or "-",
            'payment_date': p.payment_date.strftime("%d %b %Y"),
            'status': p.status
        })
        
    return JsonResponse({
        'success': True,
        'total_paid': total_paid,
        'balance_due': balance_due,
        'payments': payments_data
    })

@csrf_exempt
def api_student_notifications_list(request, student_id=None):
    student = get_student_obj(student_id)
    notifs_qs = Notification.objects.filter(
        Q(target_student=student) | Q(target_group='All Users') | Q(target_group='Students')
    ).order_by('-timestamp') if student else Notification.objects.all().order_by('-timestamp')[:10]
    
    notifs_data = []
    for n in notifs_qs:
        notifs_data.append({
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'category': n.category,
            'is_read': n.is_read,
            'timestamp': n.timestamp.strftime("%d %b %Y %I:%M %p")
        })
        
    return JsonResponse({
        'success': True,
        'notifications': notifs_data
    })

@csrf_exempt
def api_edit_student(request, student_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            student = Student.objects.get(student_id=student_id)
            student.name = data.get('name', student.name)
            student.email = data.get('email', student.email)
            student.phone = data.get('phone', student.phone)
            student.username = data.get('username', student.username)
            student.portal_password = data.get('password', student.portal_password)
            student.parent_username = data.get('parent_username', student.parent_username)
            student.parent_password = data.get('parent_password', student.parent_password)
            student.course = data.get('program', student.course)
            student.status = data.get('status', student.status)
            
            # Batch mapping by name
            batch_name = data.get('batch')
            if batch_name and batch_name != '-':
                try:
                    student.batch = Batch.objects.get(name=batch_name)
                except Batch.DoesNotExist:
                    pass
            elif batch_name == '-' or batch_name == '':
                student.batch = None
                
            student.save()
            
            # Calculate updated batch name to return
            b_name = student.batch.name if student.batch else '-'
            return JsonResponse({'success': True, 'batch': b_name})
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
            
            # Generate auto name
            auto_name = data.get('name') or f"Batch - {random.randint(1000, 9999)}"
            
            b = Batch.objects.create(
                name=auto_name,
                course=data.get('course', ''),
                trainer=trainer,
                capacity=data.get('capacity', 0),
                schedule_days=data.get('schedule_days', ''),
                schedule_time=data.get('schedule_time', ''),
                status='Active',
                start_date=timezone.now().date(),
                timing=data.get('timing', '')
            )
            return JsonResponse({'success': True, 'batch_id': b.id})
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
            
            old_trainer = b.trainer
            new_trainer = AppUser.objects.get(id=trainer_id) if trainer_id else b.trainer
            
            b.name = data.get('name', b.name)
            b.course = data.get('course', b.course)
            b.trainer = new_trainer
            b.capacity = data.get('capacity', b.capacity)
            b.schedule_days = data.get('schedule_days', b.schedule_days)
            b.schedule_time = data.get('schedule_time', b.schedule_time)
            b.status = data.get('status', b.status)
            b.timing = data.get('timing', b.timing)
            b.save()
            
            # Sync mentor for all students in this batch if trainer changed
            if old_trainer != new_trainer:
                students = b.students.exclude(status='Dropped')
                for s in students:
                    s.mentor = new_trainer
                    s.save()
                    
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False})

@csrf_exempt
def api_assign_students_batch(request, batch_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            student_ids = data.get('student_ids', [])
            batch = Batch.objects.get(id=batch_id)
            
            # Fetch students
            students = Student.objects.filter(student_id__in=student_ids)
            for s in students:
                s.batch = batch
                if batch.trainer:
                    s.mentor = batch.trainer
                s.save()
            
            return JsonResponse({'success': True, 'new_count': batch.current_students_count})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False})

from django.db import transaction

@csrf_exempt
def api_delete_batch(request, batch_id):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                batch = Batch.objects.select_for_update().get(id=batch_id)
                data = json.loads(request.body) if request.body else {}
                
                # Active students in the old batch
                students = batch.students.exclude(status='Dropped')
                students_count = students.count()
                old_timing = batch.timing  # authoritative source — never trust frontend alone
                
                if not request.body and students_count > 0:
                    return JsonResponse({
                        'success': False, 
                        'error': 'This batch contains active students and cannot be deleted directly. Please migrate them first.'
                    })
                
                migration_type = data.get('migration_type', 'unassigned')
                target_batch_id = data.get('target_batch_id')
                
                VALID_TIMINGS = ('Morning', 'Afternoon', 'Evening')
                
                if migration_type == 'migrate' and target_batch_id:
                    target_batch = Batch.objects.select_for_update().get(id=target_batch_id)
                    
                    # Strict timing validation
                    if target_batch.timing != old_timing:
                        return JsonResponse({
                            'success': False,
                            'error': f'Timing mismatch: "{batch.name}" is a {old_timing} batch. You can only move students to another {old_timing} batch. The selected batch "{target_batch.name}" is {target_batch.timing}.'
                        })
                    
                    if target_batch.current_students_count + students_count > target_batch.capacity:
                        return JsonResponse({
                            'success': False, 
                            'error': f'Insufficient capacity. Target batch "{target_batch.name}" can only take {target_batch.capacity - target_batch.current_students_count} more students, but needs {students_count}.'
                        })
                        
                    for s in students:
                        s.batch = target_batch
                        if target_batch.trainer:
                            s.mentor = target_batch.trainer
                        s.save()

                elif migration_type == 'create_and_migrate':
                    new_batch_data = data.get('new_batch_data', {})
                    new_capacity = int(new_batch_data.get('capacity', 20))
                    new_timing = new_batch_data.get('timing', old_timing)
                    
                    # Strict timing validation — new batch must match old batch timing
                    if new_timing not in VALID_TIMINGS:
                        return JsonResponse({
                            'success': False,
                            'error': f'Invalid timing "{new_timing}". Must be one of: Morning, Afternoon, Evening.'
                        })
                    if new_timing != old_timing:
                        return JsonResponse({
                            'success': False,
                            'error': f'Timing mismatch: The old batch is {old_timing}. The new batch must also be {old_timing}.'
                        })
                    
                    if new_capacity < students_count:
                        return JsonResponse({
                            'success': False, 
                            'error': f'Insufficient capacity. The old batch has {students_count} active students, but the new batch capacity is only {new_capacity}.'
                        })
                        
                    trainer_id = new_batch_data.get('trainer_id')
                    trainer = AppUser.objects.get(id=trainer_id) if trainer_id else None
                    auto_name = new_batch_data.get('name') or f"Batch - {random.randint(1000, 9999)}"
                    
                    target_batch = Batch.objects.create(
                        name=auto_name,
                        course=new_batch_data.get('course', ''),
                        trainer=trainer,
                        capacity=new_capacity,
                        schedule_days=new_batch_data.get('schedule_days', ''),
                        schedule_time=new_batch_data.get('schedule_time', ''),
                        status='Active',
                        start_date=timezone.now().date(),
                        timing=new_timing  # locked to old batch timing
                    )
                    
                    for s in students:
                        s.batch = target_batch
                        if target_batch.trainer:
                            s.mentor = target_batch.trainer
                        s.save()

                elif migration_type == 'unassigned':
                    for s in students:
                        s.batch = None
                        s.save()
                
                # Delete old batch ONLY after successful migration
                batch.delete()
                
                target_new_count = None
                if migration_type == 'migrate' and target_batch_id:
                    target_new_count = target_batch.current_students_count
                
            return JsonResponse({'success': True, 'target_new_count': target_new_count})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False})


import csv
from django.http import HttpResponse

def api_export_fees(request):
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    payments_qs = FeePayment.objects.all().order_by('-payment_date')
    
    if query:
        payments_qs = payments_qs.filter(Q(student__name__icontains=query) | Q(student__student_id__icontains=query) | Q(student__batch__name__icontains=query))
    if status_filter:
        payments_qs = payments_qs.filter(status__iexact=status_filter)
    if start_date:
        payments_qs = payments_qs.filter(payment_date__gte=start_date)
    if end_date:
        payments_qs = payments_qs.filter(payment_date__lte=end_date)
        
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="financial_ledger.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Student Name', 'Student ID', 'Batch', 'Amount', 'Balance Due', 'Payment Method', 'Transaction ID', 'Payment Date', 'Due Date', 'Status'])
    
    for payment in payments_qs:
        writer.writerow([
            payment.student.name,
            payment.student.student_id,
            payment.student.batch.name if payment.student.batch else 'Unassigned',
            payment.amount,
            payment.balance_due,
            payment.payment_method,
            payment.transaction_id,
            payment.payment_date,
            payment.due_date,
            payment.status
        ])
        
    return response

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def api_student_requests(request, student_id):
    try:
        student = Student.objects.get(student_id=student_id)
    except Student.DoesNotExist:
        return JsonResponse({'error': 'Student not found'}, status=404)

    if request.method == 'GET':
        reqs = StudentRequest.objects.filter(student=student).order_by('-created_at')
        data = [{
            'id': r.id,
            'category': r.category,
            'subject': r.subject,
            'description': r.description,
            'priority': r.priority,
            'status': r.status,
            'admin_reply': r.admin_reply,
            'created_at': r.created_at.strftime("%Y-%m-%d %H:%M")
        } for r in reqs]
        return JsonResponse({'requests': data})

    elif request.method == 'POST':
        try:
            body = json.loads(request.body)
            sreq = StudentRequest.objects.create(
                student=student,
                category=body.get('category', 'General'),
                subject=body.get('subject', ''),
                description=body.get('description', ''),
                priority=body.get('priority', 'Normal')
            )
            return JsonResponse({'success': True, 'id': sreq.id})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def api_student_notifications(request, student_id):
    try:
        student = Student.objects.get(student_id=student_id)
    except Student.DoesNotExist:
        return JsonResponse({'error': 'Student not found'}, status=404)
        
    if request.method == 'GET':
        # Get general broadcasts that match the student's batch or "All Students"
        # and also personal notifications
        notifs = Notification.objects.filter(
            Q(target_group='All Students') | 
            Q(target_group=student.batch.name if student.batch else 'None') |
            Q(target_student=student)
        ).order_by('-timestamp')
        
        data = [{
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'category': n.category,
            'timestamp': n.timestamp.strftime("%Y-%m-%d %H:%M"),
            'is_read': n.is_read
        } for n in notifs]
        return JsonResponse({'notifications': data})

def logout_view(request):
    logout(request)
    request.session.flush()
    return redirect('login_page')

def parse_date_helper(val):
    if not val:
        return None
    if isinstance(val, (date, datetime)):
        return val.date() if isinstance(val, datetime) else val
    s = str(val).strip()
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%Y/%m/%d', '%d/%m/%Y'):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass
    return None

def parse_time_helper(val):
    if not val:
        return None
    if isinstance(val, time):
        return val
    s = str(val).strip()
    for fmt in ('%H:%M', '%H:%M:%S', '%I:%M %p', '%I:%M%p', '%I:%M:%S %p', '%H.%M'):
        try:
            return datetime.strptime(s, fmt).time()
        except ValueError:
            pass
    return None

def validate_class_schedule(batch, c_date, start_t, end_t, edit_class_id=None):
    if not c_date:
        return False, 'Please select a valid class date.'
    if not start_t:
        return False, 'Please select a valid Start Time.'
    if not end_t:
        return False, 'Please select a valid End Time.'

    today = timezone.localdate()
    now_time = timezone.localtime().time()

    # Requirement 1: Past date NOT allowed
    if c_date < today:
        return False, 'Cannot schedule a class for a past date.'

    # Requirement 2: Today's date is allowed, but Start Time must NOT be earlier than current time
    if c_date == today and start_t < now_time:
        return False, "Start Time cannot be in the past for today's classes."

    # Requirement 3: Start Time must be less than End Time
    if start_t >= end_t:
        return False, 'Start Time must be before End Time.'

    # Requirement 6 & 7: Same Batch + same Date + overlapping Time Range -> NOT allowed
    # (Different Batch + same Date + same Time -> ALLOWED)
    if batch:
        overlapping_qs = ClassSchedule.objects.filter(
            batch=batch,
            date=c_date,
            time__lt=end_t,
            end_time__gt=start_t
        )
        if edit_class_id:
            overlapping_qs = overlapping_qs.exclude(id=edit_class_id)
        
        overlapping = overlapping_qs.first()
        if overlapping:
            ex_start = overlapping.time.strftime('%I:%M %p') if overlapping.time else ''
            ex_end = overlapping.end_time.strftime('%I:%M %p') if overlapping.end_time else ''
            b_name = batch.name
            d_str = c_date.strftime('%d %b %Y')
            return False, f"Time conflict! Batch '{b_name}' already has a class scheduled on {d_str} between {ex_start} and {ex_end}."

    return True, None


@csrf_exempt
def api_add_class(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            date_str = data.get('date')
            start_time_str = data.get('start_time')
            end_time_str = data.get('end_time')

            c_date = parse_date_helper(date_str)
            start_t = parse_time_helper(start_time_str)
            end_t = parse_time_helper(end_time_str)

            batch_id = data.get('batch_id')
            batch = Batch.objects.filter(id=batch_id).first() if batch_id else None
            trainer = get_current_mentor(request)

            is_valid, err_msg = validate_class_schedule(batch, c_date, start_t, end_t)
            if not is_valid:
                return JsonResponse({'success': False, 'error': err_msg}, status=400)

            # Auto-calculate duration if not provided
            duration = data.get('duration')
            if not duration or 'Invalid' in str(duration) or duration == 'Auto-calculated':
                start_dt = datetime.datetime.combine(c_date, start_t)
                end_dt = datetime.datetime.combine(c_date, end_t)
                duration_mins = int((end_dt - start_dt).total_seconds() / 60)
                duration = f"{duration_mins} Mins"

            subject = data.get('subject')
            topic_id = data.get('topic_id')
            if not subject and topic_id:
                top = CourseTopic.objects.filter(id=topic_id).first()
                if top:
                    subject = top.name

            cls = ClassSchedule.objects.create(
                subject=subject or 'Online Class',
                batch=batch,
                trainer=trainer,
                date=c_date,
                time=start_t,
                end_time=end_t,
                duration=duration,
                description=data.get('description', ''),
                mode=data.get('mode', 'Online'),
                meeting_link=data.get('meeting_link')
            )
            return JsonResponse({'success': True, 'id': cls.id})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)


@csrf_exempt
def api_mentor_classes(request):
    trainer = get_current_mentor(request)
    mentor_batches = Batch.objects.filter(trainer=trainer) if trainer else Batch.objects.none()
    classes = ClassSchedule.objects.filter(
        Q(trainer=trainer) | Q(batch__in=mentor_batches)
    ).select_related('batch', 'trainer').distinct().order_by('date', 'time')

    classes_data = []
    for c in classes:
        classes_data.append({
            'id': c.id,
            'subject': c.subject,
            'batch_id': c.batch.id if c.batch else None,
            'batch_name': c.batch.name if c.batch else 'General Batch',
            'trainer_id': c.trainer.id if c.trainer else None,
            'trainer_name': c.trainer.name if c.trainer else 'Mentor',
            'date': c.date.strftime('%Y-%m-%d') if c.date else '',
            'time': c.time.strftime('%I:%M %p') if c.time else '',
            'end_time': c.end_time.strftime('%I:%M %p') if c.end_time else '',
            'start_time_24': c.time.strftime('%H:%M') if c.time else '10:00',
            'end_time_24': c.end_time.strftime('%H:%M') if c.end_time else '11:30',
            'mode': c.mode,
            'meeting_link': c.meeting_link or '',
        })
    return JsonResponse({'classes': classes_data, 'success': True})


@csrf_exempt
def api_mentor_edit_class(request, class_id):
    try:
        cls = ClassSchedule.objects.get(id=class_id)
    except ClassSchedule.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Class not found'}, status=404)

    if request.method == 'GET':
        topic = CourseTopic.objects.filter(name__iexact=cls.subject).first()
        module_id = topic.module_id if topic else None
        topic_id = topic.id if topic else None

        return JsonResponse({
            'success': True,
            'class': {
                'id': cls.id,
                'subject': cls.subject,
                'batch_id': cls.batch_id,
                'batch_name': cls.batch.name if cls.batch else '',
                'module_id': module_id,
                'topic_id': topic_id,
                'date': cls.date.strftime('%Y-%m-%d') if cls.date else '',
                'start_time': cls.time.strftime('%I:%M %p') if cls.time else '',
                'end_time': cls.end_time.strftime('%I:%M %p') if cls.end_time else '',
                'start_time_24': cls.time.strftime('%H:%M') if cls.time else '10:00',
                'end_time_24': cls.end_time.strftime('%H:%M') if cls.end_time else '11:30',
                'time_range': f"{cls.time.strftime('%I:%M %p') if cls.time else ''} – {cls.end_time.strftime('%I:%M %p') if cls.end_time else ''}".strip(' –'),
                'duration': cls.duration or '90 Mins',
                'description': cls.description or cls.subject,
                'mode': cls.mode,
                'meeting_link': cls.meeting_link or '',
            }
        })
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            date_str = data.get('date')
            start_time_str = data.get('start_time')
            end_time_str = data.get('end_time')

            c_date = parse_date_helper(date_str) if date_str else cls.date
            start_t = parse_time_helper(start_time_str) if start_time_str else cls.time
            end_t = parse_time_helper(end_time_str) if end_time_str else cls.end_time

            batch_id = data.get('batch_id')
            batch = Batch.objects.filter(id=batch_id).first() if batch_id else cls.batch

            is_valid, err_msg = validate_class_schedule(batch, c_date, start_t, end_t, edit_class_id=cls.id)
            if not is_valid:
                return JsonResponse({'success': False, 'error': err_msg}, status=400)

            # Auto-calculate duration
            duration = data.get('duration')
            if not duration or 'Invalid' in str(duration) or duration == 'Auto-calculated':
                start_dt = datetime.datetime.combine(c_date, start_t)
                end_dt = datetime.datetime.combine(c_date, end_t)
                duration_mins = int((end_dt - start_dt).total_seconds() / 60)
                duration = f"{duration_mins} Mins"

            if 'subject' in data and data['subject']:
                cls.subject = data['subject']
            elif 'topic_id' in data and data['topic_id']:
                top = CourseTopic.objects.filter(id=data['topic_id']).first()
                if top:
                    cls.subject = top.name

            cls.batch = batch
            cls.date = c_date
            cls.time = start_t
            cls.end_time = end_t
            cls.duration = duration
            if 'description' in data:
                cls.description = data['description']
            if 'mode' in data:
                cls.mode = data['mode']
            if 'meeting_link' in data:
                cls.meeting_link = data['meeting_link']
            cls.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)

@csrf_exempt
def api_mentor_delete_class(request, class_id):
    if request.method == 'POST':
        try:
            cls = ClassSchedule.objects.get(id=class_id)
            cls.delete()
            return JsonResponse({'status': 'success', 'success': True})
        except ClassSchedule.DoesNotExist:
            return JsonResponse({'status': 'error', 'error': 'Class not found'}, status=404)
    return JsonResponse({'status': 'error', 'error': 'Invalid method'}, status=405)


@csrf_exempt
def api_add_task(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            batch = Batch.objects.get(id=data.get('batch_id'))
            mentor_id = request.session.get('appuser_id')
            trainer = AppUser.objects.get(id=mentor_id) if mentor_id else None
            
            Task.objects.create(
                title=data.get('title'),
                description=data.get('description'),
                batch=batch,
                trainer=trainer,
                due_date=data.get('due_date'),
                category=data.get('category', 'Laboratory'),
                module_code=data.get('module_code', 'AI-101'),
                max_marks=data.get('max_marks', 100)
            )
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid method'})

@csrf_exempt
def api_mentor_edit_task(request, task_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            task = Task.objects.get(id=task_id)
            
            task.title = data.get('title', task.title)
            task.description = data.get('description', task.description)
            task.due_date = data.get('due_date', task.due_date)
            task.category = data.get('category', task.category)
            task.module_code = data.get('module_code', task.module_code)
            task.max_marks = data.get('max_marks', task.max_marks)
            if 'batch_id' in data and data['batch_id']:
                task.batch = Batch.objects.get(id=data['batch_id'])
            
            task.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid method'})

@csrf_exempt
def api_mentor_delete_task(request, task_id):
    if request.method == 'POST':
        try:
            task = Task.objects.get(id=task_id)
            task.delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid method'})

@csrf_exempt
def api_evaluate_submission(request, submission_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            submission = TaskSubmission.objects.get(id=submission_id)
            
            submission.marks_obtained = data.get('marks_obtained', submission.marks_obtained)
            submission.mentor_feedback = data.get('mentor_feedback', submission.mentor_feedback)
            submission.status = 'Evaluated'
            
            submission.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid method'})

@csrf_exempt
def api_mentor_send_batch_notification(request):
    """Send message from mentor to a batch or individual student."""
    if request.method == 'POST':
        try:
            trainer = get_current_mentor(request)
            if not trainer:
                return JsonResponse({'success': False, 'error': 'Mentor not found in session.'})
            
            data = json.loads(request.body)
            title = (data.get('title') or '').strip()
            message = (data.get('message') or '').strip()
            send_type = data.get('send_type', 'batch')  # 'batch' or 'student'
            
            if not title or not message:
                return JsonResponse({'success': False, 'error': 'Title and message are required.'})
            
            my_batches = Batch.objects.filter(trainer=trainer, status='Active')
            
            if send_type == 'student':
                student_id = data.get('student_id')
                if not student_id:
                    return JsonResponse({'success': False, 'error': 'Please select a student.'})
                student = Student.objects.get(id=student_id)
                # Security: student must belong to one of the mentor's batches
                if student.batch_id not in my_batches.values_list('id', flat=True):
                    return JsonResponse({'success': False, 'error': 'You can only message students in your assigned batches.'})
                Notification.objects.create(
                    title=title,
                    message=message,
                    category='message',
                    direction='sent',
                    sender_mentor=trainer,
                    target_student=student,
                    target_group=f"Student: {student.name}"
                )
                return JsonResponse({'success': True, 'count': 1})
            else:
                batch_id = data.get('batch_id')
                if not batch_id:
                    return JsonResponse({'success': False, 'error': 'Please select a batch.'})
                batch = Batch.objects.get(id=batch_id)
                # Security: batch must belong to this mentor
                if batch.id not in my_batches.values_list('id', flat=True):
                    return JsonResponse({'success': False, 'error': 'You can only message your own batches.'})
                students = batch.students.exclude(status='Dropped')
                count = 0
                for s in students:
                    Notification.objects.create(
                        title=title,
                        message=message,
                        category='message',
                        direction='sent',
                        sender_mentor=trainer,
                        target_student=s,
                        target_group=f"Batch: {batch.name}"
                    )
                    count += 1
                return JsonResponse({'success': True, 'count': count})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid method'})


@csrf_exempt
def api_mentor_mark_notification_read(request, notif_id):
    """Mark a single notification as read."""
    if request.method == 'POST':
        try:
            notif = Notification.objects.get(id=notif_id)
            notif.is_read = True
            notif.save()
            return JsonResponse({'success': True})
        except Notification.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Notification not found.'})
    return JsonResponse({'success': False, 'error': 'Invalid method'})


@csrf_exempt
def api_mentor_delete_notification(request, notif_id):
    """Delete a single notification."""
    if request.method == 'POST':
        try:
            notif = Notification.objects.get(id=notif_id)
            notif.delete()
            return JsonResponse({'success': True})
        except Notification.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Notification not found.'})
    return JsonResponse({'success': False, 'error': 'Invalid method'})



@csrf_exempt
def api_mentor_batch_students(request):
    """Return students for a given batch (for dynamic dropdown)."""
    if request.method == 'GET':
        batch_id = request.GET.get('batch_id')
        trainer = get_current_mentor(request)
        if not batch_id or not trainer:
            return JsonResponse({'students': []})
        my_batches = Batch.objects.filter(trainer=trainer, status='Active')
        try:
            batch = my_batches.get(id=batch_id)
        except Batch.DoesNotExist:
            return JsonResponse({'students': []})
        students = batch.students.exclude(status='Dropped').order_by('name')
        return JsonResponse({'students': [{'id': s.id, 'name': s.name} for s in students]})
    return JsonResponse({'students': []})

@csrf_exempt
def api_student_classes(request, student_id):
    try:
        student = Student.objects.get(student_id=student_id)
        if not student.batch:
            return JsonResponse({'classes': []})
        
        classes = ClassSchedule.objects.filter(batch=student.batch).order_by('-date', '-time')
        classes_data = []
        for c in classes:
            classes_data.append({
                'id': f"cls-{c.id}",
                'topic': c.subject,
                'moduleCode': 'MOD',
                'moduleTitle': c.subject,
                'date': c.date.strftime('%Y-%m-%d') if c.date else '',
                'dayNumber': c.date.day if c.date else 0,
                'monthName': c.date.strftime('%b').upper() if c.date else '',
                'time': f"{c.time.strftime('%I:%M %p') if c.time else ''} - {c.end_time.strftime('%I:%M %p') if c.end_time else ''}",
                'trainer': c.trainer.name if c.trainer else 'Unknown',
                'trainerRole': 'Mentor',
                'mode': c.mode,
                'status': 'Scheduled', # Simple hardcode or derive from date
                'isToday': c.date == timezone.now().date() if c.date else False,
                'description': c.subject,
                'link': c.meeting_link or '#',
                'agenda': []
            })
        return JsonResponse({'classes': classes_data})
    except Student.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Student not found'}, status=404)

@csrf_exempt
def api_student_tasks(request, student_id):
    try:
        student = Student.objects.get(student_id=student_id)
        if not student.batch:
            return JsonResponse({'tasks': []})
            
        tasks = Task.objects.filter(batch=student.batch).order_by('-due_date')
        tasks_data = []
        for t in tasks:
            tasks_data.append({
                'id': t.id,
                'title': t.title,
                'description': t.description,
                'due_date': t.due_date.strftime('%Y-%m-%d %I:%M %p') if t.due_date else '',
                'status': 'Pending'
            })
        return JsonResponse({'tasks': tasks_data})
    except Student.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Student not found'}, status=404)

@csrf_exempt
def api_curriculum_get(request):
    phases = CurriculumMonth.objects.prefetch_related('course_modules__topics').all().order_by('number', 'id')
    data = []
    course_name = CourseModule.objects.values_list('course_name', flat=True).first() or 'Generative AI & LLMs'
    
    for p in phases:
        mods_data = []
        for mod in p.course_modules.all().order_by('order', 'id'):
            topics_data = []
            for t in mod.topics.all().order_by('order', 'id'):
                topics_data.append({
                    'id': f"topic-{t.id}",
                    'title': t.name,
                    'description': t.description or '',
                    'type': t.class_type or 'Online Class',
                    'duration': t.duration or '90 Mins',
                    'status': 'Completed' if t.status == 'Completed' else ('In Progress' if t.status == 'Active' else 'Upcoming')
                })
            mods_data.append({
                'id': f"mod-{mod.id}",
                'code': f"MOD-{mod.order}",
                'title': mod.name,
                'weekRange': f"Week {((mod.order - 1) * 4) + 1} - {mod.order * 4}",
                'status': 'In Progress' if mod.order == 1 else 'Upcoming',
                'learningObjectives': [mod.description] if mod.description else [],
                'topics': topics_data
            })
        
        data.append({
            'monthNumber': p.number,
            'title': p.title,
            'shortTopic': p.title[:30],
            'code': f"PHASE-{p.number}",
            'duration': f"{max(len(mods_data), 1) * 2} Weeks",
            'status': p.status or 'Upcoming',
            'description': p.description,
            'modules': mods_data
        })
        
    return JsonResponse({
        'curriculum': data,
        'course_name': course_name
    })

@csrf_exempt
def api_curriculum_add_month(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        CurriculumMonth.objects.create(
            number=data.get('number'),
            title=data.get('title'),
            description=data.get('description'),
            status=data.get('status', 'Upcoming')
        )
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})

@csrf_exempt
def api_curriculum_add_module(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        month = CurriculumMonth.objects.get(number=data.get('month_number'))
        CurriculumModule.objects.create(
            month=month,
            code=data.get('code'),
            title=data.get('title'),
            week_range=data.get('week_range'),
            status=data.get('status', 'Not Started'),
            learning_objectives=data.get('learning_objectives', [])
        )
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})

@csrf_exempt
def api_curriculum_add_topic(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        # mod_id expects format "mod-1"
        mod_id = str(data.get('module_id')).replace("mod-", "")
        module = CurriculumModule.objects.get(id=mod_id)
        CurriculumTopic.objects.create(
            module=module,
            title=data.get('title'),
            description=data.get('description'),
            type=data.get('type'),
            duration=data.get('duration'),
            status=data.get('status', 'Not Started')
        )
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})


# =============================================================================
# ADMIN CURRICULUM CRUD APIS (CourseModule & CourseTopic)
# =============================================================================

def api_admin_curriculum_data(request):
    phases = CurriculumMonth.objects.prefetch_related('course_modules__topics').all().order_by('number', 'id')
    phases_list = []
    for p in phases:
        mods_list = []
        for m in p.course_modules.all().order_by('order', 'id'):
            tops_list = []
            for t in m.topics.all().order_by('order', 'id'):
                tops_list.append({
                    'id': t.id,
                    'order': t.order,
                    'name': t.name,
                    'description': t.description,
                    'duration': t.duration,
                    'class_type': t.class_type,
                    'status': t.status,
                })
            mods_list.append({
                'id': m.id,
                'phase_id': p.id,
                'order': m.order,
                'name': m.name,
                'description': m.description,
                'topics': tops_list
            })
        phases_list.append({
            'id': p.id,
            'number': p.number,
            'title': p.title,
            'description': p.description,
            'status': p.status,
            'modules': mods_list
        })
    return JsonResponse({'status': 'success', 'phases': phases_list})

@csrf_exempt
def api_admin_add_phase(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            number = int(data.get('number', CurriculumMonth.objects.count() + 1))
            title = data.get('title', '').strip()
            description = data.get('description', '').strip()
            status = data.get('status', 'Upcoming').strip()
            if not title:
                return JsonResponse({'status': 'error', 'message': 'Phase / Month title is required'}, status=400)
            phase = CurriculumMonth.objects.create(
                number=number,
                title=title,
                description=description,
                status=status
            )
            return JsonResponse({'status': 'success', 'phase': {
                'id': phase.id,
                'number': phase.number,
                'title': phase.title,
                'description': phase.description,
                'status': phase.status,
                'modules': []
            }})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

@csrf_exempt
def api_admin_edit_phase(request, phase_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            phase = CurriculumMonth.objects.get(id=phase_id)
            phase.number = int(data.get('number', phase.number))
            phase.title = data.get('title', phase.title).strip()
            phase.description = data.get('description', phase.description).strip()
            phase.status = data.get('status', phase.status).strip()
            phase.save()
            return JsonResponse({'status': 'success', 'phase': {
                'id': phase.id,
                'number': phase.number,
                'title': phase.title,
                'description': phase.description,
                'status': phase.status
            }})
        except CurriculumMonth.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Phase / Month not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error'}, status=405)

@csrf_exempt
def api_admin_delete_phase(request, phase_id):
    if request.method == 'POST':
        try:
            phase = CurriculumMonth.objects.get(id=phase_id)
            phase.delete()
            return JsonResponse({'status': 'success'})
        except CurriculumMonth.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Phase / Month not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error'}, status=405)

@csrf_exempt
def api_admin_add_module(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            phase_id = data.get('phase_id')
            phase = None
            if phase_id:
                phase = CurriculumMonth.objects.filter(id=phase_id).first()
            if not phase:
                phase = CurriculumMonth.objects.first()
            if not phase:
                phase = CurriculumMonth.objects.create(number=1, title='Phase 1: Foundations', status='Current')

            order = int(data.get('order', phase.course_modules.count() + 1))
            name = data.get('name', '').strip()
            description = data.get('description', '').strip()
            if not name:
                return JsonResponse({'status': 'error', 'message': 'Module name is required'}, status=400)
            course_name = data.get('course_name') or 'Generative AI & LLMs'
            mod = CourseModule.objects.create(
                phase=phase,
                course_name=course_name,
                order=order,
                name=name,
                description=description
            )
            return JsonResponse({'status': 'success', 'module': {
                'id': mod.id,
                'phase_id': phase.id,
                'order': mod.order,
                'name': mod.name,
                'description': mod.description,
                'topics': []
            }})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

@csrf_exempt
def api_admin_edit_module(request, module_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            mod = CourseModule.objects.get(id=module_id)
            if 'phase_id' in data and data['phase_id']:
                target_phase = CurriculumMonth.objects.filter(id=data['phase_id']).first()
                if target_phase:
                    mod.phase = target_phase
            mod.order = int(data.get('order', mod.order))
            mod.name = data.get('name', mod.name).strip()
            mod.description = data.get('description', mod.description).strip()
            mod.save()
            return JsonResponse({'status': 'success', 'module': {
                'id': mod.id,
                'phase_id': mod.phase.id if mod.phase else None,
                'order': mod.order,
                'name': mod.name,
                'description': mod.description
            }})
        except CourseModule.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Module not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error'}, status=405)

@csrf_exempt
def api_admin_delete_module(request, module_id):
    if request.method == 'POST':
        try:
            mod = CourseModule.objects.get(id=module_id)
            mod.delete()
            return JsonResponse({'status': 'success'})
        except CourseModule.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Module not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error'}, status=405)

@csrf_exempt
def api_admin_add_topic(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            module_id = data.get('module_id')
            mod = CourseModule.objects.get(id=module_id)
            order = int(data.get('order', mod.topics.count() + 1))
            name = data.get('name', '').strip()
            description = data.get('description', '').strip()
            duration = data.get('duration', '90 Mins')
            status = data.get('status', 'Active')
            if not name:
                return JsonResponse({'status': 'error', 'message': 'Topic name is required'}, status=400)
            top = CourseTopic.objects.create(
                module=mod,
                order=order,
                name=name,
                description=description,
                duration=duration,
                class_type='Online Class',
                status=status
            )
            return JsonResponse({'status': 'success', 'topic': {
                'id': top.id,
                'order': top.order,
                'name': top.name,
                'description': top.description,
                'duration': top.duration,
                'class_type': top.class_type,
                'status': top.status
            }})
        except CourseModule.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Module not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error'}, status=405)

@csrf_exempt
def api_admin_edit_topic(request, topic_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            top = CourseTopic.objects.get(id=topic_id)
            top.order = int(data.get('order', top.order))
            top.name = data.get('name', top.name).strip()
            top.description = data.get('description', top.description).strip()
            top.duration = data.get('duration', top.duration)
            top.status = data.get('status', top.status)
            top.save()
            return JsonResponse({'status': 'success', 'topic': {
                'id': top.id,
                'order': top.order,
                'name': top.name,
                'description': top.description,
                'duration': top.duration,
                'class_type': top.class_type,
                'status': top.status
            }})
        except CourseTopic.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Topic not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error'}, status=405)

@csrf_exempt
def api_admin_delete_topic(request, topic_id):
    if request.method == 'POST':
        try:
            top = CourseTopic.objects.get(id=topic_id)
            top.delete()
            return JsonResponse({'status': 'success'})
        except CourseTopic.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Topic not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error'}, status=405)

def api_student_attendance(request, student_id):
    student = Student.objects.filter(student_id=student_id).first()
    if not student:
        return JsonResponse({'status': 'error', 'message': 'Student not found'})
    
    batch_total_classes = student.batch.classes.count() if student.batch else 0
    attendances = student.attendances.all().select_related('class_schedule', 'class_schedule__module', 'class_schedule__topic').order_by('-date')
    
    history = []
    present_count = 0
    leave_count = 0
    explicit_absent_count = 0
    
    for a in attendances:
        if a.status == 'Present':
            present_count += 1
        elif a.status == 'Leave':
            leave_count += 1
        elif a.status == 'Absent':
            explicit_absent_count += 1
            
        topic_name = a.class_schedule.subject if a.class_schedule else 'General Class'
        module_name = 'General'
        if a.class_schedule and a.class_schedule.module:
            module_name = a.class_schedule.module.course_name
            
        history.append({
            'date': a.date.strftime('%d %b %Y'),
            'topic': topic_name,
            'module': module_name,
            'status': a.status
        })
        
    total_classes = batch_total_classes if batch_total_classes > 0 else (present_count + leave_count + explicit_absent_count)
    absent_count = total_classes - present_count - leave_count
    if absent_count < 0:
        absent_count = explicit_absent_count
        total_classes = present_count + leave_count + absent_count
        
    overall_percentage = round((present_count / total_classes) * 100) if total_classes > 0 else 0
    
    return JsonResponse({
        'status': 'success',
        'name': student.name,
        'batch': student.batch.name if student.batch else '',
        'course': student.course or 'Gen AI',
        'overall_percentage': overall_percentage,
        'total_classes': total_classes,
        'present_count': present_count,
        'leave_count': leave_count,
        'absent_count': absent_count,
        'history': history
    })

@csrf_exempt
def api_mentor_batch_classes(request, batch_id):
    try:
        batch = Batch.objects.get(id=batch_id)
        classes = ClassSchedule.objects.filter(batch=batch).order_by('-date', '-time')
        classes_data = []
        for c in classes:
            classes_data.append({
                'id': c.id,
                'date_str': c.date.strftime('%d %b %Y') if c.date else '',
                'subject': c.subject,
                'time_str': f"{c.time.strftime('%I:%M %p') if c.time else ''}"
            })
        return JsonResponse({'status': 'success', 'classes': classes_data})
    except Batch.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Batch not found'}, status=404)

@csrf_exempt
def api_mentor_class_attendance(request, class_id):
    try:
        cls = ClassSchedule.objects.get(id=class_id)
        if not cls.batch:
            return JsonResponse({'status': 'error', 'message': 'Class has no batch assigned'}, status=400)
            
        students = cls.batch.students.exclude(status='Dropped').order_by('name')
        
        # Existing attendance records for this class schedule
        existing_att = {
            att.student.student_id: att.status 
            for att in Attendance.objects.filter(class_schedule=cls).select_related('student')
        }
        
        students_data = []
        for s in students:
            status = existing_att.get(s.student_id, 'Present')
            students_data.append({
                'student_id': s.student_id,
                'db_id': s.id,
                'name': s.name,
                'initials': s.initials,
                'avatar_color': s.avatar_color,
                'status': status
            })
            
        class_info = {
            'id': cls.id,
            'subject': cls.subject,
            'date_str': cls.date.strftime('%d %b %Y') if cls.date else '',
            'batch_name': cls.batch.name if cls.batch else ''
        }
        return JsonResponse({'status': 'success', 'class': class_info, 'students': students_data})
    except ClassSchedule.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Class not found'}, status=404)

@csrf_exempt
def api_mentor_save_class_attendance(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)
        
    try:
        data = json.loads(request.body)
        class_id = data.get('class_id')
        records = data.get('records', {})
        
        if not class_id:
            return JsonResponse({'status': 'error', 'message': 'Class ID is required'}, status=400)
            
        cls = ClassSchedule.objects.get(id=class_id)
        
        for student_identifier, status in records.items():
            # Match student by student_id or pk
            student = Student.objects.filter(
                Q(student_id=student_identifier) | Q(id=student_identifier) if str(student_identifier).isdigit() else Q(student_id=student_identifier)
            ).first()
            
            if student:
                Attendance.objects.update_or_create(
                    student=student,
                    class_schedule=cls,
                    defaults={
                        'batch': cls.batch,
                        'status': status,
                        'date': cls.date
                    }
                )
                
        return JsonResponse({'status': 'success', 'message': 'Class attendance saved successfully!'})
    except ClassSchedule.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Class not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# =============================================================================
# STUDENT PORTAL API VIEWS
# =============================================================================

def get_student_by_id_or_default(student_id=None):
    if student_id:
        st = Student.objects.filter(
            Q(student_id=student_id) | Q(username=student_id) | Q(email=student_id) |
            (Q(id=int(student_id)) if str(student_id).isdigit() else Q(pk=-1))
        ).first()
        if st:
            return st
    return Student.objects.filter(approval_status='Approved').first() or Student.objects.first()

def get_student_curriculum_roadmap_data(student):
    if not student:
        return {
            'roadmap': [],
            'completed_topics': 0,
            'total_topics': 0,
            'course_progress_pct': 0
        }
        
    phases = CurriculumMonth.objects.prefetch_related('course_modules__topics').all().order_by('number', 'id')
    if phases.exists():
        roadmap = []
        total_topics_count = 0
        completed_topics_count = 0
        for p in phases:
            mods_data = []
            for mod in p.course_modules.all().order_by('order', 'id'):
                topics_data = []
                for top in mod.topics.all().order_by('order', 'id'):
                    total_topics_count += 1
                    if top.status == 'Completed':
                        completed_topics_count += 1
                    topics_data.append({
                        'id': f"t_{p.number}_{mod.id}_{top.id}",
                        'title': top.name,
                        'type': top.class_type or 'Online Class',
                        'duration': top.duration or '90 Mins',
                        'status': 'Completed' if top.status == 'Completed' else ('In Progress' if top.status == 'Active' else 'Upcoming')
                    })
                mods_data.append({
                    'id': f"m_{mod.id}",
                    'code': f"MOD-{mod.order}",
                    'title': mod.name,
                    'week_range': f"Week {((mod.order - 1) * 4) + 1} - {mod.order * 4}",
                    'status': 'In Progress' if mod.order == 1 else 'Upcoming',
                    'topics': topics_data
                })
            roadmap.append({
                'number': p.number,
                'title': p.title,
                'description': p.description,
                'status': p.status or 'Upcoming',
                'modules': mods_data
            })
        course_progress_pct = round((completed_topics_count / total_topics_count * 100)) if total_topics_count > 0 else 0
        return {
            'roadmap': roadmap,
            'completed_topics': completed_topics_count,
            'total_topics': total_topics_count,
            'course_progress_pct': course_progress_pct
        }

    months_qs = CurriculumMonth.objects.prefetch_related('modules__topics').all().order_by('number')
    
    roadmap = []
    total_topics_count = 0
    completed_topics_count = 0
    
    if months_qs.exists():
        for m in months_qs:
            mods_data = []
            for mod in m.modules.all():
                topics_data = []
                for top in mod.topics.all():
                    total_topics_count += 1
                    if top.status == 'Completed':
                        completed_topics_count += 1
                    topics_data.append({
                        'id': f"t_{m.number}_{mod.code}_{top.id}",
                        'title': top.title,
                        'type': top.type or '',
                        'duration': top.duration or '',
                        'status': top.status or 'Not Started'
                    })
                mods_data.append({
                    'id': f"m_{mod.code}",
                    'code': mod.code,
                    'title': mod.title,
                    'week_range': mod.week_range,
                    'status': mod.status or 'Not Started',
                    'topics': topics_data
                })
            roadmap.append({
                'number': m.number,
                'title': m.title,
                'description': m.description,
                'status': m.status or 'Not Started',
                'modules': mods_data
            })
    
    course_progress_pct = round((completed_topics_count / total_topics_count * 100)) if total_topics_count > 0 else 0
    
    return {
        'roadmap': roadmap,
        'completed_topics': completed_topics_count,
        'total_topics': total_topics_count,
        'course_progress_pct': course_progress_pct
    }


def api_student_dashboard_data(request, student_id=None):
    student = get_student_by_id_or_default(student_id)
    if not student:
        return JsonResponse({'status': 'error', 'message': 'No student found'}, status=404)
        
    batch = student.batch
    mentor_name = student.mentor.name if student.mentor else (batch.trainer.name if batch and batch.trainer else '')
    
    # Calculate attendance stats
    attendances = Attendance.objects.filter(student=student)
    total_classes = attendances.count()
    present_classes = attendances.filter(status='Present').count()
    attendance_pct = round((present_classes / total_classes * 100)) if total_classes > 0 else 0
    sessions_summary = f"{present_classes} of {total_classes} sessions" if total_classes > 0 else "0 sessions completed"
    
    # Calculate task stats
    tasks = Task.objects.filter(batch=batch) if batch else Task.objects.none()
    total_tasks = tasks.count()
    submissions = TaskSubmission.objects.filter(student=student)
    submitted_task_ids = set(submissions.values_list('task_id', flat=True))
    pending_tasks_qs = tasks.exclude(id__in=submitted_task_ids)
    pending_count = pending_tasks_qs.count()
    first_pending_task = pending_tasks_qs.first()
    pending_task_name = first_pending_task.title if first_pending_task else ""
    
    now_dt = timezone.now()
    overdue_count = pending_tasks_qs.filter(due_date__lt=now_dt).count()
    
    # Calculate fee stats
    payments = FeePayment.objects.filter(student=student)
    total_paid = sum([p.amount for p in payments if p.status == 'Paid'])
    total_due = sum([p.balance_due for p in payments if p.status == 'Pending'])
    total_fee = float(total_paid + total_due)
    paid_pct = round((float(total_paid) / total_fee * 100)) if total_fee > 0 else 0
    
    next_due_pay = payments.filter(status='Pending', due_date__isnull=False).order_by('due_date').first()
    next_due_date = next_due_pay.due_date.strftime('%d %b %Y') if next_due_pay else "N/A"
    
    # Live / Upcoming Class
    today = timezone.localdate()
    live_class = None
    if batch:
        cls = ClassSchedule.objects.filter(batch=batch, date__gte=today).order_by('date', 'time').first()
        if cls:
            live_class = {
                'id': cls.id,
                'subject': cls.subject,
                'date': cls.date.strftime('%d %b %Y'),
                'time': cls.time.strftime('%I:%M %p') if cls.time else '',
                'end_time': cls.end_time.strftime('%I:%M %p') if cls.end_time else '',
                'duration': cls.duration or '',
                'mode': cls.mode,
                'meeting_link': cls.meeting_link or '',
                'is_live': cls.get_status() == 'Live Now',
                'status': cls.get_status(),
                'trainer': cls.trainer.name if cls.trainer else (batch.trainer.name if batch.trainer else ''),
                'description': cls.description or ''
            }
            
    # Curriculum months & progress via dynamic helper function
    curriculum_info = get_student_curriculum_roadmap_data(student)
    roadmap = curriculum_info['roadmap']
    completed_topics_count = curriculum_info['completed_topics']
    total_topics_count = curriculum_info['total_topics']
    course_progress_pct = curriculum_info['course_progress_pct']
    
    # Recent Results
    recent_results = []
    eval_submissions = submissions.filter(status='Evaluated').order_by('-submitted_at')[:3]
    for sub in eval_submissions:
        recent_results.append({
            'title': sub.task.title,
            'category': sub.task.category,
            'score': f"{sub.marks_obtained}%" if sub.marks_obtained is not None else "Evaluated",
            'status': 'Passed'
        })
        
    # Announcements (Top 3 latest items dynamically: new added, old automatically removed)
    notifs_qs = Notification.objects.filter(
        Q(target_student=student) | Q(target_group__in=['All Users', 'All Students'])
    ).order_by('-timestamp')[:3]
    
    announcements = [{
        'id': n.id,
        'title': n.title,
        'message': n.message,
        'category': n.category,
        'date': n.timestamp.strftime('%d %b • %I:%M %p') if n.timestamp else ''
    } for n in notifs_qs]

    return JsonResponse({
        'status': 'success',
        'success': True,
        'student': {
            'student_id': student.student_id,
            'name': student.name,
            'email': student.email,
            'phone': student.phone,
            'course': student.course or (batch.course if batch else ''),
            'batch': batch.name if batch else '',
            'status': student.status or '',
            'timing_preference': student.timing_preference or '',
            'initials': student.initials or '',
            'avatar_color': student.avatar_color or '',
            'mentor_name': mentor_name,
            'join_date': student.join_date.strftime('%d %b %Y') if student.join_date else ''
        },
        'kpi': {
            'attendance_pct': attendance_pct,
            'sessions_summary': sessions_summary,
            'course_progress_pct': course_progress_pct,
            'completed_topics': completed_topics_count,
            'total_topics': total_topics_count,
            'pending_assignments': pending_count,
            'pending_task_name': pending_task_name,
            'overdue_assignments': overdue_count,
            'total_fee': total_fee,
            'total_paid': float(total_paid),
            'total_due': float(total_due),
            'paid_pct': paid_pct,
            'next_due_date': next_due_date
        },
        'live_class': live_class,
        'roadmap': roadmap,
        'recent_results': recent_results,
        'announcements': announcements
    })

def api_student_profile(request, student_id=None):
    student = get_student_by_id_or_default(student_id)
    if not student:
        return JsonResponse({'status': 'error', 'message': 'No student found'}, status=404)
        
    batch = student.batch
    mentor = student.mentor or (batch.trainer if batch else None)
    
    return JsonResponse({
        'status': 'success',
        'profile': {
            'student_id': student.student_id,
            'name': student.name,
            'email': student.email,
            'phone': student.phone,
            'course': student.course or (batch.course if batch else ''),
            'batch': batch.name if batch else '',
            'status': student.status,
            'timing_preference': student.timing_preference,
            'join_date': student.join_date.strftime('%Y-%m-%d') if student.join_date else '',
            'username': student.username or '',
            'portal_password': student.portal_password or '',
            'parent_username': student.parent_username or '',
            'parent_password': student.parent_password or '',
            'parent_name': getattr(student, 'parent_name', '') or getattr(student, 'guardian_name', '') or '',
            'term_credits': getattr(student, 'term_credits', '') or '',
            'topics_count': getattr(student, 'topics_count', 0) or 0,
            'hands_on_labs': getattr(student, 'hands_on_labs', 0) or 0,
            'compute_env': getattr(student, 'compute_env', '') or '',
            'initials': student.initials,
            'avatar_color': student.avatar_color,
            'mentor': {
                'name': mentor.name if mentor else '',
                'email': mentor.email if mentor else '',
                'role': mentor.role if mentor else ''
            } if mentor else None
        }
    })

def api_student_curriculum(request, student_id=None):
    student = get_student_by_id_or_default(student_id)
    curriculum_info = get_student_curriculum_roadmap_data(student)
    months_data = curriculum_info['roadmap']
    total_topics = curriculum_info['total_topics']
    completed_topics = curriculum_info['completed_topics']
    total_modules = sum([len(m.get('modules', [])) for m in months_data])
        
    return JsonResponse({
        'status': 'success',
        'student_id': student.student_id if student else '',
        'kpi': {
            'total_modules': total_modules,
            'total_topics': total_topics,
            'completed_topics': completed_topics
        },
        'months': months_data
    })

def api_student_classes_list(request, student_id=None):
    student = get_student_by_id_or_default(student_id)
    if not student or not student.batch:
        return JsonResponse({'status': 'success', 'classes': [], 'kpi': {'total': 0, 'upcoming': 0, 'completed': 0, 'live': 0}})
        
    classes_qs = ClassSchedule.objects.filter(batch=student.batch).order_by('date', 'time')
    classes_list = []
    upcoming_cnt = 0
    completed_cnt = 0
    live_cnt = 0
    
    for c in classes_qs:
        st = c.get_status()
        if st == 'Upcoming':
            upcoming_cnt += 1
        elif st == 'Past':
            completed_cnt += 1
        elif st == 'Live Now':
            live_cnt += 1
            
        classes_list.append({
            'id': c.id,
            'subject': c.subject,
            'batch_name': c.batch.name if c.batch else '',
            'trainer_name': c.trainer.name if c.trainer else (c.batch.trainer.name if c.batch and c.batch.trainer else 'Mentor'),
            'date': c.date.strftime('%Y-%m-%d') if c.date else '',
            'date_str': c.date.strftime('%d %b %Y') if c.date else '',
            'time': c.time.strftime('%I:%M %p') if c.time else '',
            'end_time': c.end_time.strftime('%I:%M %p') if c.end_time else '',
            'duration': c.duration or '90 Mins',
            'mode': c.mode,
            'meeting_link': c.meeting_link or '',
            'status': st,
            'description': c.description or ''
        })
        
    return JsonResponse({
        'status': 'success',
        'student_id': student.student_id,
        'batch_name': student.batch.name,
        'kpi': {
            'total': len(classes_list),
            'upcoming': upcoming_cnt,
            'completed': completed_cnt,
            'live': live_cnt
        },
        'classes': classes_list
    })

def api_student_tasks_list(request, student_id=None):
    student = get_student_by_id_or_default(student_id)
    if not student or not student.batch:
        return JsonResponse({'status': 'success', 'tasks': [], 'kpi': {'total': 0, 'submitted': 0, 'evaluated': 0, 'pending': 0}})
        
    tasks_qs = Task.objects.filter(batch=student.batch).order_by('-due_date')
    submissions = {sub.task_id: sub for sub in TaskSubmission.objects.filter(student=student)}
    
    tasks_list = []
    submitted_cnt = 0
    evaluated_cnt = 0
    pending_cnt = 0
    
    for t in tasks_qs:
        sub = submissions.get(t.id)
        sub_data = None
        if sub:
            submitted_cnt += 1
            if sub.status == 'Evaluated':
                evaluated_cnt += 1
            sub_data = {
                'id': sub.id,
                'status': sub.status,
                'submission_url': sub.submission_url or '',
                'submission_text': sub.submission_text or '',
                'submitted_at': sub.submitted_at.strftime('%d %b %Y %I:%M %p') if sub.submitted_at else '',
                'marks_obtained': sub.marks_obtained,
                'mentor_feedback': sub.mentor_feedback or ''
            }
        else:
            pending_cnt += 1
            
        tasks_list.append({
            'id': t.id,
            'title': t.title,
            'category': t.category,
            'module_code': t.module_code,
            'max_marks': t.max_marks,
            'description': t.description or '',
            'due_date': t.due_date.strftime('%d %b %Y %I:%M %p') if t.due_date else '',
            'status': t.status,
            'submission': sub_data
        })
        
    return JsonResponse({
        'status': 'success',
        'student_id': student.student_id,
        'kpi': {
            'total': len(tasks_list),
            'submitted': submitted_cnt,
            'evaluated': evaluated_cnt,
            'pending': pending_cnt
        },
        'tasks': tasks_list
    })

def api_student_attendance_list(request, student_id=None):
    return api_student_attendance(request, student_id if student_id else (get_student_by_id_or_default().student_id if get_student_by_id_or_default() else ''))

def api_student_career(request, student_id=None):
    student = get_student_by_id_or_default(student_id)
    if not student:
        return JsonResponse({'status': 'error', 'message': 'Student not found'}, status=404)
        
    offers_qs = PlacementOffer.objects.filter(student=student).order_by('-offer_date')
    offers_list = [{
        'id': o.id,
        'company': o.company,
        'offer_date': o.offer_date.strftime('%d %b %Y') if o.offer_date else ''
    } for o in offers_qs]
    
    return JsonResponse({
        'status': 'success',
        'student_id': student.student_id,
        'offers': offers_list,
        'profile': {
            'name': student.name,
            'course': student.course or (student.batch.course if student.batch else 'Gen AI'),
            'status': student.status
        }
    })

def api_student_fees_list(request, student_id=None):
    student = get_student_by_id_or_default(student_id)
    if not student:
        return JsonResponse({'status': 'error', 'message': 'Student not found'}, status=404)
        
    payments_qs = FeePayment.objects.filter(student=student).order_by('-payment_date')
    payments_list = []
    total_paid = 0
    total_due = 0
    next_due_date = ''
    
    for p in payments_qs:
        if p.status == 'Paid':
            total_paid += p.amount
        elif p.status == 'Pending':
            total_due += p.balance_due
            if p.due_date and not next_due_date:
                next_due_date = p.due_date.strftime('%d %b %Y')
                
        payments_list.append({
            'id': p.id,
            'amount': float(p.amount),
            'balance_due': float(p.balance_due),
            'payment_method': p.payment_method,
            'transaction_id': p.transaction_id or '',
            'due_date': p.due_date.strftime('%d %b %Y') if p.due_date else '',
            'payment_date': p.payment_date.strftime('%d %b %Y') if p.payment_date else '',
            'status': p.status
        })
        
    return JsonResponse({
        'status': 'success',
        'student_id': student.student_id,
        'kpi': {
            'total_paid': float(total_paid),
            'total_due': float(total_due),
            'next_due_date': next_due_date or 'N/A'
        },
        'payments': payments_list
    })

def api_student_notifications_list(request, student_id=None):
    student = get_student_by_id_or_default(student_id)
    if not student:
        return JsonResponse({'status': 'error', 'message': 'Student not found'}, status=404)
        
    notifs_qs = Notification.objects.filter(
        Q(target_student=student) | Q(target_group__in=['All Users', 'All Students'])
    ).order_by('-timestamp')
    
    requests_qs = StudentRequest.objects.filter(student=student).order_by('-created_at')
    
    notifs_list = [{
        'id': n.id,
        'title': n.title,
        'message': n.message,
        'category': n.category,
        'is_read': n.is_read,
        'timestamp': n.timestamp.strftime('%d %b %Y %I:%M %p') if n.timestamp else ''
    } for n in notifs_qs]
    
    requests_list = [{
        'id': r.id,
        'category': r.category,
        'subject': r.subject,
        'description': r.description,
        'priority': r.priority,
        'status': r.status,
        'admin_reply': r.admin_reply or '',
        'created_at': r.created_at.strftime('%d %b %Y %I:%M %p') if r.created_at else ''
    } for r in requests_qs]
    
    unread_cnt = notifs_qs.filter(is_read=False).count()
    
    return JsonResponse({
        'status': 'success',
        'student_id': student.student_id,
        'kpi': {
            'total': len(notifs_list),
            'unread': unread_cnt,
            'requests_count': len(requests_list)
        },
        'notifications': notifs_list,
        'requests': requests_list
    })

@csrf_exempt
def api_student_requests(request, student_id=None):
    student = get_student_by_id_or_default(student_id)
    if not student:
        return JsonResponse({'status': 'error', 'message': 'Student not found'}, status=404)
        
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            StudentRequest.objects.create(
                student=student,
                category=data.get('category', 'General'),
                subject=data.get('subject', ''),
                description=data.get('description', ''),
                priority=data.get('priority', 'Normal')
            )
            return JsonResponse({'status': 'success', 'message': 'Request submitted successfully!'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
            
    requests_qs = StudentRequest.objects.filter(student=student).order_by('-created_at')
    requests_list = [{
        'id': r.id,
        'category': r.category,
        'subject': r.subject,
        'description': r.description,
        'priority': r.priority,
        'status': r.status,
        'admin_reply': r.admin_reply or '',
        'created_at': r.created_at.strftime('%d %b %Y %I:%M %p') if r.created_at else ''
    } for r in requests_qs]
    
    return JsonResponse({'status': 'success', 'requests': requests_list})

@csrf_exempt
def api_student_classes(request, student_id=None):
    return api_student_classes_list(request, student_id)

@csrf_exempt
def api_student_tasks(request, student_id=None):
    return api_student_tasks_list(request, student_id)

@csrf_exempt
def api_student_notifications(request, student_id=None):
    return api_student_notifications_list(request, student_id)


# =============================================================================
# MENTOR CLASS CRUD API VIEWS
# =============================================================================

@csrf_exempt
def api_add_class(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            subject = data.get('subject', '').strip()
            batch_id = data.get('batch_id')
            class_date_str = data.get('date')
            start_time_str = data.get('start_time')
            end_time_str = data.get('end_time')
            duration = data.get('duration', '90 Mins')
            description = data.get('description', '')
            mode = data.get('mode', 'Online')
            meeting_link = data.get('meeting_link', '')
            module_id = data.get('module_id')
            topic_id = data.get('topic_id')

            if not subject:
                return JsonResponse({'status': 'error', 'success': False, 'error': 'Subject/Topic name is required'}, status=400)
            if not batch_id:
                return JsonResponse({'status': 'error', 'success': False, 'error': 'Batch is required'}, status=400)
            if not class_date_str or not start_time_str:
                return JsonResponse({'status': 'error', 'success': False, 'error': 'Date and Start Time are required'}, status=400)

            batch = Batch.objects.get(id=batch_id)
            class_date = parse_date_str(class_date_str)
            start_time = parse_time_str(start_time_str)
            end_time = parse_time_str(end_time_str) if end_time_str else None

            module = CourseModule.objects.filter(id=module_id).first() if module_id else None
            topic = CourseTopic.objects.filter(id=topic_id).first() if topic_id else None

            cls = ClassSchedule.objects.create(
                subject=subject,
                batch=batch,
                trainer=batch.trainer,
                date=class_date,
                time=start_time,
                end_time=end_time,
                duration=duration,
                description=description,
                mode=mode,
                meeting_link=meeting_link,
                module=module,
                topic=topic
            )
            return JsonResponse({'status': 'success', 'success': True, 'message': 'Class scheduled successfully!', 'class_id': cls.id})
        except Batch.DoesNotExist:
            return JsonResponse({'status': 'error', 'success': False, 'error': 'Batch not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'success': False, 'error': 'Invalid request method'}, status=405)

@csrf_exempt
def api_mentor_edit_class(request, class_id):
    try:
        cls = ClassSchedule.objects.get(id=class_id)
        if request.method == 'GET':
            return JsonResponse({
                'status': 'success',
                'success': True,
                'class': {
                    'id': cls.id,
                    'subject': cls.subject,
                    'batch_id': cls.batch_id,
                    'module_id': cls.module_id,
                    'topic_id': cls.topic_id,
                    'date': cls.date.strftime('%Y-%m-%d') if cls.date else '',
                    'start_time': cls.time.strftime('%H:%M') if cls.time else '',
                    'end_time': cls.end_time.strftime('%H:%M') if cls.end_time else '',
                    'duration': cls.duration or '90 Mins',
                    'description': cls.description or '',
                    'mode': cls.mode,
                    'meeting_link': cls.meeting_link or ''
                }
            })
        elif request.method == 'POST':
            data = json.loads(request.body)
            if 'subject' in data:
                cls.subject = data['subject'].strip()
            if 'batch_id' in data and data['batch_id']:
                cls.batch = Batch.objects.get(id=data['batch_id'])
            if 'date' in data and data['date']:
                cls.date = parse_date_str(data['date'])
            if 'start_time' in data and data['start_time']:
                cls.time = parse_time_str(data['start_time'])
            if 'end_time' in data and data['end_time']:
                cls.end_time = parse_time_str(data['end_time'])
            if 'duration' in data:
                cls.duration = data['duration']
            if 'description' in data:
                cls.description = data['description']
            if 'mode' in data:
                cls.mode = data['mode']
            if 'meeting_link' in data:
                cls.meeting_link = data['meeting_link']
            if 'module_id' in data and data['module_id']:
                cls.module = CourseModule.objects.filter(id=data['module_id']).first()
            if 'topic_id' in data and data['topic_id']:
                cls.topic = CourseTopic.objects.filter(id=data['topic_id']).first()

            cls.save()
            return JsonResponse({'status': 'success', 'success': True, 'message': 'Class updated successfully!'})
    except ClassSchedule.DoesNotExist:
        return JsonResponse({'status': 'error', 'success': False, 'error': 'Class not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'success': False, 'error': 'Invalid request method'}, status=405)

@csrf_exempt
def api_mentor_delete_class(request, class_id):
    if request.method == 'POST':
        try:
            cls = ClassSchedule.objects.get(id=class_id)
            cls.delete()
            return JsonResponse({'status': 'success', 'success': True, 'message': 'Class deleted successfully!'})
        except ClassSchedule.DoesNotExist:
            return JsonResponse({'status': 'error', 'success': False, 'error': 'Class not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'success': False, 'error': 'Invalid request method'}, status=405)

def api_mentor_classes(request):
    classes = ClassSchedule.objects.all().select_related('batch', 'trainer').order_by('-date', '-time')
    classes_data = []
    for c in classes:
        classes_data.append({
            'id': c.id,
            'subject': c.subject,
            'batch_name': c.batch.name if c.batch else '',
            'date': c.date.strftime('%Y-%m-%d') if c.date else '',
            'date_str': c.date.strftime('%d %b %Y') if c.date else '',
            'time': c.time.strftime('%I:%M %p') if c.time else '',
            'end_time': c.end_time.strftime('%I:%M %p') if c.end_time else '',
            'duration': c.duration or '90 Mins',
            'mode': c.mode,
            'meeting_link': c.meeting_link or '',
            'status': c.get_status()
        })
    return JsonResponse({'status': 'success', 'success': True, 'classes': classes_data})



