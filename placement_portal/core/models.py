

# Create your models here.
from django.db import models

class Student(models.Model):
    full_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    year_of_study = models.IntegerField()

class Recruiter(models.Model):
    full_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100)
    company_name = models.CharField(max_length=100)
    designation = models.CharField(max_length=100)

from django.contrib.auth.models import User

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
