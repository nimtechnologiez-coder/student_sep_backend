from django.db import models
from django.utils import timezone

class Trainer(models.Model):
    name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=[('Active', 'Active'), ('Inactive', 'Inactive')], default='Active')
    

    @property
    def initials(self):
        parts = self.name.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        elif parts:
            return parts[0][:2].upper()
        return "??"
    
    @property
    def avatar_color(self):
        colors = ['#2563eb', '#16a34a', '#d97706', '#9333ea', '#e11d48', '#0891b2', '#be123c']
        # Use length or simple hash to keep it consistent
        return colors[len(self.name) % len(colors)]

    def __str__(self):
        return self.name

class Batch(models.Model):
    name = models.CharField(max_length=50)
    course = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=[('Active', 'Active'), ('Upcoming', 'Upcoming'), ('Completed', 'Completed')], default='Active')
    start_date = models.DateField(default=timezone.now)
    trainer = models.ForeignKey('AppUser', on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'role': 'Mentor'})
    capacity = models.IntegerField(default=10)
    timing = models.CharField(max_length=20, choices=[('Morning', 'Morning'), ('Afternoon', 'Afternoon'), ('Evening', 'Evening')], default='Morning')
    schedule_days = models.CharField(max_length=50, default='Mon-Fri')
    schedule_time = models.CharField(max_length=50, default='9:00 AM - 1:00 PM')
    
    @property
    def current_students_count(self):
        return self.students.filter(approval_status='Approved').exclude(status='Dropped').count()
    

    @property
    def initials(self):
        parts = self.name.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        elif parts:
            return parts[0][:2].upper()
        return "??"
    
    @property
    def avatar_color(self):
        colors = ['#2563eb', '#16a34a', '#d97706', '#9333ea', '#e11d48', '#0891b2', '#be123c']
        # Use length or simple hash to keep it consistent
        return colors[len(self.name) % len(colors)]

    def __str__(self):
        return self.name

class Student(models.Model):
    student_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=[('Active', 'Active'), ('Onboarding', 'Onboarding'), ('Completed', 'Completed'), ('Dropped', 'Dropped')], default='Active')
    term_credits = models.CharField(max_length=50, blank=True, null=True, default='Semester 1 / 4 Cr')
    topics_count = models.IntegerField(default=12)
    hands_on_labs = models.IntegerField(default=4)
    compute_env = models.CharField(max_length=100, blank=True, null=True, default='AWS Cloud9')
    username = models.CharField(max_length=50, blank=True, null=True)
    portal_password = models.CharField(max_length=50, blank=True, null=True)
    parent_username = models.CharField(max_length=50, blank=True, null=True)
    parent_password = models.CharField(max_length=50, blank=True, null=True)
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    course = models.CharField(max_length=100, blank=True)
    timing_preference = models.CharField(max_length=20, choices=[('Morning', 'Morning'), ('Afternoon', 'Afternoon'), ('Evening', 'Evening')], default='Morning')
    join_date = models.DateField(default=timezone.now)
    avatar_url = models.URLField(blank=True, null=True)
    approval_status = models.CharField(max_length=20, choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')], default='Pending')
    mentor = models.ForeignKey('AppUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='mentees', limit_choices_to={'role': 'Mentor'})

    

    @property
    def initials(self):
        parts = self.name.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        elif parts:
            return parts[0][:2].upper()
        return "??"
    
    @property
    def avatar_color(self):
        colors = ['#2563eb', '#16a34a', '#d97706', '#9333ea', '#e11d48', '#0891b2', '#be123c']
        # Use length or simple hash to keep it consistent
        return colors[len(self.name) % len(colors)]

    def __str__(self):
        return self.name

class FeePayment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    balance_due = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_method = models.CharField(max_length=50, default='UPI')
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    due_date = models.DateField(blank=True, null=True)
    payment_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=20, choices=[('Paid', 'Paid'), ('Pending', 'Pending'), ('Failed', 'Failed')], default='Paid')
    

    @property
    def initials(self):
        parts = self.name.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        elif parts:
            return parts[0][:2].upper()
        return "??"
    
    @property
    def avatar_color(self):
        colors = ['#2563eb', '#16a34a', '#d97706', '#9333ea', '#e11d48', '#0891b2', '#be123c']
        # Use length or simple hash to keep it consistent
        return colors[len(self.name) % len(colors)]

    def __str__(self):
        return f"{self.student.name} - {self.amount}"

class PlacementOffer(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='offers')
    company = models.CharField(max_length=100)
    offer_date = models.DateField(default=timezone.now)
    

    @property
    def initials(self):
        parts = self.name.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        elif parts:
            return parts[0][:2].upper()
        return "??"
    
    @property
    def avatar_color(self):
        colors = ['#2563eb', '#16a34a', '#d97706', '#9333ea', '#e11d48', '#0891b2', '#be123c']
        # Use length or simple hash to keep it consistent
        return colors[len(self.name) % len(colors)]

    def __str__(self):
        return f"{self.student.name} at {self.company}"

class ClassSchedule(models.Model):
    module = models.ForeignKey('CourseModule', on_delete=models.SET_NULL, null=True, blank=True, related_name='scheduled_classes')
    topic = models.ForeignKey('CourseTopic', on_delete=models.SET_NULL, null=True, blank=True, related_name='scheduled_classes')
    subject = models.CharField(max_length=100)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='classes')
    trainer = models.ForeignKey('AppUser', on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateField(default=timezone.now)
    time = models.TimeField()
    end_time = models.TimeField(null=True, blank=True)
    duration = models.CharField(max_length=50, blank=True, default='90 Mins')
    description = models.TextField(blank=True, default='')
    mode = models.CharField(max_length=20, choices=[('Online', 'Online'), ('Offline', 'Offline')], default='Online')
    meeting_link = models.URLField(blank=True, null=True)
    

    @property
    def session(self):
        if self.batch and self.batch.timing:
            t = str(self.batch.timing).strip().capitalize()
            if t in ['Morning', 'Afternoon', 'Evening']:
                return t
        if self.time:
            if self.time.hour < 12:
                return 'Morning'
            elif self.time.hour < 17:
                return 'Afternoon'
            else:
                return 'Evening'
        return 'Morning'

    @property
    def session_lower(self):
        return self.session.lower()

    def get_end_time(self):
        if self.end_time:
            return self.end_time
        if not self.time:
            return None
        from datetime import datetime, timedelta
        dummy = datetime.combine(datetime.today(), self.time)
        return (dummy + timedelta(minutes=90)).time()

    def get_status(self):
        from datetime import datetime, time, timedelta
        from django.utils import timezone

        if not self.date:
            return 'Upcoming'

        now_dt = timezone.localtime()
        today = now_dt.date()
        now_time = now_dt.time()

        start_t = self.time or time(0, 0)
        end_t = self.get_end_time() or start_t

        if self.date > today:
            return 'Upcoming'
        elif self.date < today:
            return 'Past'
        else: # c.date == today
            if now_time < start_t:
                return 'Upcoming'
            elif end_t and now_time >= end_t:
                return 'Past'
            else:
                return 'Live Now'

    @property
    def is_completed(self):
        return self.get_status() == 'past'

    @property
    def is_past(self):
        return self.get_status() == 'past'

    @property
    def is_live(self):
        return self.get_status() == 'live'

    @property
    def is_today_unstarted(self):
        return self.get_status() == 'today'

    @property
    def is_future(self):
        return self.get_status() == 'upcoming'

    @property
    def initials(self):
        subject_name = self.subject or 'Class'
        parts = subject_name.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        elif parts:
            return parts[0][:2].upper()
        return "CL"
    
    @property
    def avatar_color(self):
        colors = ['#2563eb', '#16a34a', '#d97706', '#9333ea', '#e11d48', '#0891b2', '#be123c']
        subject_name = self.subject or 'Class'
        return colors[len(subject_name) % len(colors)]

    def __str__(self):
        batch_name = self.batch.name if self.batch else 'No Batch'
        return f"{self.subject} - {batch_name}"

class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendances')
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True, related_name='attendances')
    class_schedule = models.ForeignKey(ClassSchedule, on_delete=models.CASCADE, null=True, blank=True, related_name='attendances')
    status = models.CharField(max_length=20, choices=[('Present', 'Present'), ('Absent', 'Absent'), ('Late', 'Late'), ('Leave', 'Leave')], default='Present')
    date = models.DateField(default=timezone.now)

    class Meta:
        unique_together = ('student', 'class_schedule')


class Activity(models.Model):
    description = models.CharField(max_length=255)
    activity_type = models.CharField(max_length=50) # 'admission', 'fee', 'material'
    timestamp = models.DateTimeField(default=timezone.now)
    icon_svg = models.TextField(blank=True, null=True)
    color_class = models.CharField(max_length=50, blank=True, null=True)
    

    @property
    def initials(self):
        parts = self.name.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        elif parts:
            return parts[0][:2].upper()
        return "??"
    
    @property
    def avatar_color(self):
        colors = ['#2563eb', '#16a34a', '#d97706', '#9333ea', '#e11d48', '#0891b2', '#be123c']
        # Use length or simple hash to keep it consistent
        return colors[len(self.name) % len(colors)]

    def __str__(self):
        return self.description

class AcademicModule(models.Model):
    name = models.CharField(max_length=100)
    course = models.CharField(max_length=100, default='Gen AI')
    status = models.CharField(max_length=20, default='Active')
    term_credits = models.CharField(max_length=50, blank=True, null=True, default='Semester 1 / 4 Cr')
    topics_count = models.IntegerField(default=12)
    hands_on_labs = models.IntegerField(default=4)
    compute_env = models.CharField(max_length=100, blank=True, null=True, default='AWS Cloud9')

class Assessment(models.Model):
    title = models.CharField(max_length=100)
    module = models.ForeignKey(AcademicModule, on_delete=models.CASCADE, null=True, blank=True)
    date = models.DateField(default=timezone.now)

class AssessmentResult(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE)
    score = models.IntegerField()
    max_score = models.IntegerField(default=100)

class Notification(models.Model):
    DIRECTION_CHOICES = [('sent', 'Sent by Mentor'), ('question', 'Student Question')]
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    category = models.CharField(max_length=50, default='System')
    target_group = models.CharField(max_length=100, default='All Users')
    target_student = models.ForeignKey('Student', on_delete=models.CASCADE, null=True, blank=True, related_name='received_notifications')
    sender_student = models.ForeignKey('Student', on_delete=models.CASCADE, null=True, blank=True, related_name='sent_questions')
    sender_mentor = models.ForeignKey('AppUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_notifications')
    direction = models.CharField(max_length=20, choices=DIRECTION_CHOICES, default='sent')
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"[{self.direction}] {self.title}"

class AppUser(models.Model):
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=50)
    email = models.EmailField()
    status = models.CharField(max_length=20, default='Active')
    term_credits = models.CharField(max_length=50, blank=True, null=True, default='Semester 1 / 4 Cr')
    topics_count = models.IntegerField(default=12)
    hands_on_labs = models.IntegerField(default=4)
    compute_env = models.CharField(max_length=100, blank=True, null=True, default='AWS Cloud9')
    username = models.CharField(max_length=50, blank=True, null=True)
    portal_password = models.CharField(max_length=50, blank=True, null=True)


class StudentRequest(models.Model):
    student = models.ForeignKey('Student', on_delete=models.CASCADE)
    category = models.CharField(max_length=100)
    subject = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(max_length=50, default='Normal')
    status = models.CharField(max_length=50, default='Open')
    admin_reply = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.subject} - {self.student.name}"

class Task(models.Model):
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=50, default='Laboratory')
    module_code = models.CharField(max_length=50, default='AI-101')
    max_marks = models.IntegerField(default=100)
    description = models.TextField(blank=True, null=True)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='tasks')
    trainer = models.ForeignKey('AppUser', on_delete=models.SET_NULL, null=True, blank=True)
    due_date = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=50, default='Active')
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def submissions_count(self):
        return self.submissions.count()

    def __str__(self):
        return f"{self.title} - {self.batch.name}"

class TaskSubmission(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='task_submissions')
    submission_url = models.URLField(blank=True, null=True)
    submission_text = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('Submitted', 'Submitted'), ('Evaluated', 'Evaluated')], default='Submitted')
    marks_obtained = models.IntegerField(null=True, blank=True)
    mentor_feedback = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ('task', 'student')
        
    def __str__(self):
        return f"{self.student.name} - {self.task.title}"

class CurriculumMonth(models.Model):
    number = models.IntegerField()
    title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, default="Upcoming") # Current, Completed, Upcoming
    
    def __str__(self):
        return f"Month {self.number}: {self.title}"

class CurriculumModule(models.Model):
    month = models.ForeignKey(CurriculumMonth, on_delete=models.CASCADE, related_name='modules')
    code = models.CharField(max_length=50)
    title = models.CharField(max_length=200)
    week_range = models.CharField(max_length=50) # e.g. "Week 1 - 2"
    status = models.CharField(max_length=20, default="Not Started") # Completed, In Progress, Not Started
    learning_objectives = models.JSONField(default=list) # List of strings
    
    def __str__(self):
        return self.code + " " + self.title

class CurriculumTopic(models.Model):
    module = models.ForeignKey(CurriculumModule, on_delete=models.CASCADE, related_name='topics')
    title = models.CharField(max_length=200)
    description = models.TextField()
    type = models.CharField(max_length=50) # Video, Reading, Hands-on Lab, Project
    duration = models.CharField(max_length=50) # e.g. "45m", "2h"
    status = models.CharField(max_length=20, default="Not Started")
    
    def __str__(self):
        return self.title


class CourseModule(models.Model):
    course_name = models.CharField(max_length=200, default='Generative AI & LLMs')
    order = models.IntegerField(default=1)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.order}. {self.name}"


class CourseTopic(models.Model):
    module = models.ForeignKey(CourseModule, on_delete=models.CASCADE, related_name='topics')
    order = models.IntegerField(default=1)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    duration = models.CharField(max_length=50, default='90 Mins')
    class_type = models.CharField(max_length=50, default='Online Class')
    status = models.CharField(max_length=50, default='Active')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.order}. {self.name}"

