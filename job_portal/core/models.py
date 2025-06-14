from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import datetime

class User(AbstractUser):
    ROLE_CHOICES = (
        ('seeker', 'Job Seeker'),
        ('employer', 'Employer'),
        ('admin', 'Admin'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    is_email_verified = models.BooleanField(default=False)

class Skill(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class JobSeekerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20)
    location = models.CharField(max_length=100)
    resume = models.FileField(upload_to='resumes/')
    bio = models.TextField(blank=True)
    skills = models.ManyToManyField(Skill, blank=True) 
    
class Education(models.Model):
    seeker = models.ForeignKey(JobSeekerProfile, related_name='education', on_delete=models.CASCADE)
    institute = models.CharField(max_length=100)
    degree = models.CharField(max_length=100)
    start_year = models.PositiveIntegerField()
    end_year = models.PositiveIntegerField()

class Experience(models.Model):
    seeker = models.ForeignKey(JobSeekerProfile,related_name='experience', on_delete=models.CASCADE)
    company = models.CharField(max_length=100)
    position = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

class Certification(models.Model):
    seeker = models.ForeignKey(JobSeekerProfile,related_name='certificates', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    issuer = models.CharField(max_length=100)
    issue_date = models.DateField()

class Portfolio(models.Model):
    seeker = models.ForeignKey(JobSeekerProfile, related_name='portfolio', on_delete=models.CASCADE)
    project_title = models.CharField(max_length=100)
    url = models.URLField()


class EmployerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=100)
    industry = models.CharField(max_length=100)
    website = models.URLField()
    logo = models.ImageField(upload_to='logos/')
    description = models.TextField()


class Job(models.Model):
    employer = models.ForeignKey(EmployerProfile, on_delete=models.CASCADE)
    title = models.CharField(max_length=150)
    description = models.TextField()
    skills_required = models.TextField()
    location = models.CharField(max_length=100)
    salary_min = models.IntegerField()
    salary_max = models.IntegerField()
    job_type = models.CharField(max_length=20, choices=[('full', 'Full-Time'), ('part', 'Part-Time'), ('remote', 'Remote'), ('intern', 'Internship')])
    created_at = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateField()
    is_active = models.BooleanField(default=True)

class JobSkill(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    skill_name = models.CharField(max_length=50)

class SavedJob(models.Model):
    seeker = models.ForeignKey(JobSeekerProfile, on_delete=models.CASCADE)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('seeker', 'job')  # 🔐 Prevent duplicate saves

class Application(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    seeker = models.ForeignKey(JobSeekerProfile, on_delete=models.CASCADE)
    resume = models.FileField(upload_to='applications/')
    cover_letter = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=[('applied', 'Applied'), ('interview', 'Interview Scheduled'), ('rejected', 'Rejected'), ('hired', 'Hired')], default='applied')
    applied_at = models.DateTimeField(auto_now_add=True)

class ApplicationAnswer(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    question = models.CharField(max_length=200)
    answer = models.TextField()

class Interview(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='interviews')
    scheduled_at = models.DateTimeField()
    location = models.TextField(blank=True, null=True)  # for in-person or Zoom link
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Interview for {self.application.job.title} with {self.application.user.username}"

class InterviewFeedback(models.Model):
    interview = models.OneToOneField(Interview, on_delete=models.CASCADE, related_name='feedback')
    feedback = models.TextField()
    rated = models.IntegerField(blank=True, null=True)  # Rating 1-10
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback for {self.interview}"
    
class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    max_jobs = models.PositiveIntegerField(null=True, blank=True)  # None = unlimited

    def __str__(self):
        return self.name

class EmployerSubscription(models.Model):
    employer = models.OneToOneField(EmployerProfile, on_delete=models.CASCADE)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    start_date = models.DateTimeField(default=timezone.now)

    def remaining_jobs(self):
        if self.plan and self.plan.max_jobs is not None:
            posted_jobs = Job.objects.filter(employer=self.employer).count()
            return max(self.plan.max_jobs - posted_jobs, 0)
        return None  # Unlimited

class Payment(models.Model):
    employer = models.ForeignKey(EmployerProfile, on_delete=models.CASCADE)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    amount = models.DecimalField(max_digits=6, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employer.user.username} - {self.plan.name} - ${self.amount}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class Review(models.Model):
    seeker = models.ForeignKey(JobSeekerProfile, on_delete=models.CASCADE)
    employer = models.ForeignKey(EmployerProfile, on_delete=models.CASCADE)
    rating = models.IntegerField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class Report(models.Model):
    reporter = models.ForeignKey(User, on_delete=models.CASCADE)
    reported_job = models.ForeignKey(Job, on_delete=models.CASCADE)
    reason = models.TextField()
    response = models.TextField(blank=True, null=True)  # ✅ Optional admin response
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report by {self.reporter.username} on {self.reported_job.title}"
    

class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)

class SearchLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    query = models.CharField(max_length=200)
    searched_at = models.DateTimeField(auto_now_add=True)

class Message(models.Model):
    sender = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)
    recipient = models.ForeignKey(User, related_name='received_messages', on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(default=datetime.now)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.sender} -> {self.recipient} at {self.timestamp}"