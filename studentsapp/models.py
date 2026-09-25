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
    capacity = models.IntegerField(default=20)
    schedule_days = models.CharField(max_length=50, default='Mon-Fri')
    schedule_time = models.CharField(max_length=50, default='9:00 AM - 1:00 PM')
    

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
    status = models.CharField(max_length=20, default='Active')
    username = models.CharField(max_length=50, blank=True, null=True)
    portal_password = models.CharField(max_length=50, blank=True, null=True)
    phone = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=[('Active', 'Active'), ('Onboarding', 'Onboarding'), ('Completed', 'Completed'), ('Dropped', 'Dropped')], default='Active')
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    course = models.CharField(max_length=100, blank=True)
    join_date = models.DateField(default=timezone.now)
    avatar_url = models.URLField(blank=True, null=True)
    username = models.CharField(max_length=50, blank=True, null=True)
    portal_password = models.CharField(max_length=50, blank=True, null=True)
    approval_status = models.CharField(max_length=20, choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')], default='Pending')

    

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
    subject = models.CharField(max_length=100)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='classes')
    trainer = models.ForeignKey(Trainer, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateField(default=timezone.now)
    time = models.TimeField()
    mode = models.CharField(max_length=20, choices=[('Online', 'Online'), ('Offline', 'Offline')], default='Online')
    

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
        return f"{self.subject} - {self.batch.name}"

class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    class_schedule = models.ForeignKey(ClassSchedule, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=[('Present', 'Present'), ('Absent', 'Absent'), ('Late', 'Late')], default='Present')
    date = models.DateField(default=timezone.now)

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
    title = models.CharField(max_length=100)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(default=timezone.now)

class AppUser(models.Model):
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=50)
    email = models.EmailField()
    status = models.CharField(max_length=20, default='Active')
    username = models.CharField(max_length=50, blank=True, null=True)
    portal_password = models.CharField(max_length=50, blank=True, null=True)

