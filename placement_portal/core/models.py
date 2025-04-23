# Create your models here.
from django.db import models
from django.contrib.auth.models import User

def student_resume_path(instance, filename):
    # Store resumes in a per-student folder (by email), no extra 'resumes/' prefix
    return f"{instance.email}/{filename}"

class Student(models.Model):
    full_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    year_of_study = models.IntegerField()
    resume = models.FileField(upload_to=student_resume_path, null=True, blank=True)

class Recruiter(models.Model):
    full_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100)
    company_name = models.CharField(max_length=100)
    designation = models.CharField(max_length=100)

class Job(models.Model):
    recruiter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='jobs')
    title = models.CharField(max_length=100)
    company = models.CharField(max_length=100)
    location = models.CharField(max_length=100)
    description = models.TextField()
    skills = models.CharField(max_length=255)
    salary = models.CharField(max_length=50)
    deadline = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} at {self.company}"

# Application model to track which user applied to which job
class Application(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    applied_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('applied','Applied'),('approved','Approved'),('rejected','Rejected')], default='applied')
    notes = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('user', 'job')

    def __str__(self):
        return f"{self.user.username} applied to {self.job.title}"

class Interview(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    scheduled_time = models.DateTimeField()
    gmeet_link = models.CharField(max_length=512)
    calendar_event_id = models.CharField(max_length=256)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('scheduled', 'Scheduled'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='scheduled')

    def __str__(self):
        return f"Interview for {self.application.user.username} - {self.application.job.title} at {self.scheduled_time}"
