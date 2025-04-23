from django import forms
from .models import Student, Recruiter

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['full_name', 'email', 'password', 'department', 'year_of_study', 'resume']

class RecruiterForm(forms.ModelForm):
    class Meta:
        model = Recruiter
        fields = ['full_name', 'email', 'password', 'company_name', 'designation']
from .models import Job

class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = '__all__'
