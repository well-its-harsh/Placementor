from django.shortcuts import render

from django.shortcuts import render, redirect
from .forms import StudentForm, RecruiterForm
from .models import Student, Recruiter 

def signup(request):
    if request.method == 'POST':
        if 'student' in request.POST:
            Student.objects.create(
                full_name=request.POST['full_name'],
                email=request.POST['email'],
                password=request.POST['password'],
                department=request.POST['department'],
                year_of_study=request.POST['year_of_study']
            )
            return redirect('/student-dashboard/')

        elif 'recruiter' in request.POST:
            Recruiter.objects.create(
                full_name=request.POST['full_name'],
                email=request.POST['email'],
                password=request.POST['password'],
                company_name=request.POST['company_name'],
                designation=request.POST['designation']
            )
            return redirect('/recruiter-dashboard/')

    return render(request, 'signup.html')

def student_dashboard(request):
    user = None
    department = None
    if request.user.is_authenticated:
        try:
            from .models import Student
            user = Student.objects.get(email=request.user.email)
            department = getattr(user, 'department', None)
        except Exception:
            user = None
            department = None
    return render(request, 'student-dashboard.html', {'user': user, 'department': department})

def recruiter_dashboard(request):
    return render(request, 'recruiter-dashboard.html')
def login(request):
    return render(request, 'login.html')

def home(request):
    return render(request, 'place.html')

from django.contrib import messages


def login_view(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']

        # Check if the user is a student
        try:
            student = Student.objects.get(email=email)
            if student.password == password:
                request.session['student_id'] = student.id
                return redirect('student_dashboard')  # Replace with your actual URL name
        except Student.DoesNotExist:
            pass

        # Check if the user is a recruiter
        try:
            recruiter = Recruiter.objects.get(email=email)
            if recruiter.password == password:
                request.session['recruiter_id'] = recruiter.id
                return redirect('recruiter_dashboard')  # Replace with your actual URL name
        except Recruiter.DoesNotExist:
            pass

        messages.error(request, 'Invalid email or password.')

    return render(request, 'login.html')
def job_openings(request):
    query = request.GET.get('q', '').strip() if 'q' in request.GET else ''
    jobs = Job.objects.all().order_by('-created_at')
    if query:
        from django.db.models import Q
        jobs = jobs.filter(
            Q(title__icontains=query) |
            Q(company__icontains=query) |
            Q(location__icontains=query) |
            Q(skills__icontains=query)
        )
    for job in jobs:
        job.skill_list = job.skills.split(',')
    user = None
    department = None
    if request.user.is_authenticated:
        try:
            from .models import Student
            user = Student.objects.get(email=request.user.email)
            department = getattr(user, 'department', None)
        except Exception:
            user = None
            department = None
    return render(request, 'job-openings.html', {'jobs': jobs, 'query': query, 'user': user, 'department': department})
def my_applications(request):
    return render(request, 'my-applications.html')
def ats_score(request):
    return render(request, 'ats-score.html')
def interviews(request):
    return render(request, 'interviews.html')
def notifications(request):
    return render(request, 'notifications.html')

def Ssettings(request):
    return render(request, 'Ssettings.html')

def job_postings(request):
    jobs = Job.objects.all()

    for job in jobs:
        job.skill_list = job.skills.split(',') 
    return render(request, 'job-postings.html')

def applications(request):
    return render(request, 'applications.html')

def ai_shortlisting(request):
    return render(request, 'ai-shortlisting.html')

def schedule_interviews(request):
    return render(request, 'schedule-interviews.html')

def analytics(request):
    return render(request, 'analytics.html')

def Rsettings(request):
    return render(request, 'Rsettings.html')



from django.contrib.auth.decorators import login_required
from .models import Job
from django.contrib import messages


def create_job(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        company = request.POST.get('company')
        location = request.POST.get('location')
        description = request.POST.get('description')
        skills = request.POST.get('skills')
        salary = request.POST.get('salary')
        deadline = request.POST.get('deadline')

        Job.objects.create(
            recruiter=request.user,
            title=title,
            company=company,
            location=location,
            description=description,
            skills=skills,
            salary=salary,
            deadline=deadline
        )

        messages.success(request, 'Job posted successfully!')
        return redirect('job_postings')
    return render(request, 'create-job.html')
def job_list(request):
    jobs = Job.objects.filter(recruiter=request.user).order_by('-id')  # Show jobs created by the logged-in recruiter
    for job in jobs:
        job.skill_list = job.skills.split(',')  # Split skills into list for template
    return render(request, 'job-postings.html', {'jobs': jobs})
