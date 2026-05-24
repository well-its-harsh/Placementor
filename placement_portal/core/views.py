from django.shortcuts import render, redirect, get_object_or_404
from .forms import StudentForm, RecruiterForm
from .models import Student, Recruiter, Job, Application, Interview
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta, date, time
import os
import google.generativeai as genai
from PyPDF2 import PdfReader
import io

def signup(request):
    if request.method == 'POST':
        if 'student' in request.POST:
            email = request.POST['email']
            # Prevent duplicate user creation
            if User.objects.filter(username=email).exists():
                messages.error(request, 'A user with this email already exists. Please log in or use a different email.')
                return render(request, 'signup.html')
            # Prevent duplicate student profile creation
            if Student.objects.filter(email=email).exists():
                messages.error(request, 'A student profile with this email already exists. Please log in or use a different email.')
                return render(request, 'signup.html')
            user = User.objects.create_user(
                username=email,
                email=email,
                password=request.POST['password']
            )
            Student.objects.create(
                full_name=request.POST['full_name'],
                email=email,
                password=request.POST['password'],
                department=request.POST['department'],
                year_of_study=request.POST['year_of_study']
            )
            messages.success(request, 'Signup successful! Please log in.')
            return redirect('login')

        elif 'recruiter' in request.POST:
            email = request.POST['email']
            if Recruiter.objects.filter(email=email).exists():
                messages.error(request, 'A recruiter profile with this email already exists. Please log in or use a different email.')
                return render(request, 'signup.html')
            # Create Django User for recruiter
            if not User.objects.filter(username=email).exists():
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=request.POST['password']
                )
            Recruiter.objects.create(
                full_name=request.POST['full_name'],
                email=email,
                password=request.POST['password'],
                company_name=request.POST['company_name'],
                designation=request.POST['designation']
            )
            messages.success(request, 'Recruiter signup successful! Please log in.')
            return redirect('login')

    return render(request, 'signup.html')

@login_required
def student_dashboard(request):
    student = None
    department = None
    # Try session first
    student_id = request.session.get('student_id')
    if student_id:
        try:
            student = Student.objects.get(id=student_id)
            department = getattr(student, 'department', None)
        except Student.DoesNotExist:
            student = None
            department = None
    # Fallback: try to get by email from Django user
    if not student and request.user.is_authenticated:
        try:
            student = Student.objects.get(email=request.user.email)
            department = getattr(student, 'department', None)
        except Student.DoesNotExist:
            student = None
            department = None
    # Stats
    applications_count = 0
    interviews_count = 0
    offers_count = 0  # No Offer model, so set to 0 or calculate from Application if you add it
    ats_score = None
    recent_activities = []
    upcoming_interviews = []
    if student:
        from .models import Application, Interview
        applications_count = Application.objects.filter(user__email=student.email).count()
        interviews_count = Interview.objects.filter(application__user__email=student.email).count()
        # For ATS score, if you calculate/store it somewhere, fetch it here
        # For offers, if status 'approved' means offer, count those:
        offers_count = Application.objects.filter(user__email=student.email, status='approved').count()
        # Recent activities: last 3 applications or interviews
        recent_apps = Application.objects.filter(user__email=student.email).order_by('-applied_at')[:3]
        for app in recent_apps:
            recent_activities.append({
                'type': 'application',
                'job': app.job.title,
                'company': app.job.company,
                'when': app.applied_at,
                'status': app.status,
            })
        recent_ints = Interview.objects.filter(application__user__email=student.email).order_by('-scheduled_time')[:3]
        for iv in recent_ints:
            recent_activities.append({
                'type': 'interview',
                'job': iv.application.job.title,
                'company': iv.application.job.company,
                'when': iv.scheduled_time,
                'status': iv.status,
            })
        # Sort by time, latest first
        recent_activities = sorted(recent_activities, key=lambda x: x['when'], reverse=True)[:3]
        # Upcoming interviews: next 2
        from django.utils import timezone
        now = timezone.now()
        upcoming_interviews = Interview.objects.filter(application__user__email=student.email, scheduled_time__gte=now).order_by('scheduled_time')[:2]
    return render(request, 'student-dashboard.html', {
        'user': student,
        'department': department,
        'applications_count': applications_count,
        'interviews_count': interviews_count,
        'offers_count': offers_count,
        'ats_score': ats_score,
        'recent_activities': recent_activities,
        'upcoming_interviews': upcoming_interviews,
    })

def recruiter_dashboard(request):
    recruiter = None
    # Try session first
    recruiter_id = request.session.get('recruiter_id')
    if recruiter_id:
        try:
            recruiter = Recruiter.objects.get(id=recruiter_id)
        except Recruiter.DoesNotExist:
            recruiter = None
    # Fallback: try to get by email from Django user
    if not recruiter and request.user.is_authenticated:
        try:
            recruiter = Recruiter.objects.get(email=request.user.email)
        except Recruiter.DoesNotExist:
            recruiter = None
    if not recruiter:
        messages.error(request, 'You must be logged in as a recruiter to access this page.')
        return redirect('login')
    # Stats
    from .models import Job, Application, Interview
    jobs = Job.objects.filter(recruiter__email=recruiter.email)
    job_ids = jobs.values_list('id', flat=True)
    total_applications = Application.objects.filter(job_id__in=job_ids).count()
    shortlisted = Application.objects.filter(job_id__in=job_ids, status='approved').count()
    interviews = Interview.objects.filter(application__job_id__in=job_ids).count()
    offers_made = Application.objects.filter(job_id__in=job_ids, status='approved').count()  # Same as shortlisted
    # Recent applications
    recent_applications = Application.objects.filter(job_id__in=job_ids).select_related('user', 'job').order_by('-applied_at')[:3]
    # Upcoming interviews
    from django.utils import timezone
    now = timezone.now()
    upcoming_interviews = Interview.objects.filter(application__job_id__in=job_ids, scheduled_time__gte=now).select_related('application__user', 'application__job').order_by('scheduled_time')[:2]
    return render(request, 'recruiter-dashboard.html', {
        'user': recruiter,
        'total_applications': total_applications,
        'shortlisted': shortlisted,
        'interviews': interviews,
        'offers_made': offers_made,
        'recent_applications': recent_applications,
        'upcoming_interviews': upcoming_interviews,
    })

def login(request):
    return render(request, 'login.html')

def home(request):
    return render(request, 'place.html')

from django.contrib import messages

def login_view(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']
        # Try recruiter authentication first
        try:
            recruiter = Recruiter.objects.get(email=email)
            # Authenticate using recruiter email and password (from Recruiter table)
            if recruiter.password == password:
                # Set up a dummy Django user session for recruiter
                request.session['recruiter_id'] = recruiter.id
                request.session['is_authenticated_recruiter'] = True
                messages.success(request, 'Recruiter login successful!')
                return redirect('recruiter_dashboard')
            else:
                messages.error(request, 'Invalid recruiter password.')
                return render(request, 'login.html')
        except Recruiter.DoesNotExist:
            pass
        # If not recruiter, try Django User authentication for student
        users = User.objects.filter(email=email)
        if users.exists():
            user = users.first()
            user_auth = authenticate(request, username=user.username, password=password)
            if user_auth is not None:
                auth_login(request, user_auth)
                try:
                    student = Student.objects.get(email=email)
                    request.session['student_id'] = student.id
                    messages.success(request, 'Student login successful!')
                    return redirect('student_dashboard')
                except Student.DoesNotExist:
                    pass
                messages.error(request, 'No student profile found for this email.')
                return render(request, 'login.html')
            else:
                messages.error(request, 'Invalid email or password. (Password may not be set with Django password hasher)')
        else:
            messages.error(request, 'Invalid email or password. (User not found)')
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
        job.skill_list = job.skills.split(',') if job.skills else []
    user = None
    department = None
    student_id = request.session.get('student_id')
    if student_id:
        try:
            student = Student.objects.get(id=student_id)
            user = student
            department = getattr(student, 'department', None)
        except Student.DoesNotExist:
            user = None
            department = None
    # Exclude jobs already applied to
    if user:
        applied_job_ids = Application.objects.filter(user__email=user.email).values_list('job_id', flat=True)
        jobs = jobs.exclude(id__in=applied_job_ids)
    return render(request, 'job-openings.html', {'jobs': jobs, 'query': query, 'user': user, 'department': department})

from django.views.decorators.http import require_POST
from django.http import JsonResponse

@require_POST
def apply_job(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required.'}, status=403)
    job_id = request.POST.get('job_id')
    try:
        job = Job.objects.get(id=job_id)
        Application.objects.create(user=request.user, job=job)
        return JsonResponse({'success': True})
    except Job.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Job not found.'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

def my_applications(request):
    student = None
    department = None
    applications = []
    student_id = request.session.get('student_id')
    if student_id:
        try:
            student = Student.objects.get(id=student_id)
            department = getattr(student, 'department', None)
            # Find applications by matching Application.user.email == student.email
            from .models import Application
            applications = Application.objects.filter(user__email=student.email).select_related('job').order_by('-applied_at')
        except Student.DoesNotExist:
            student = None
            department = None
    return render(request, 'my-applications.html', {'user': student, 'department': department, 'applications': applications})

def application_detail(request, application_id):
    user = request.user if request.user.is_authenticated else None
    department = None
    if user:
        try:
            student = Student.objects.get(email=user.email)
            department = getattr(student, 'department', None)
        except Exception:
            department = None
    application = get_object_or_404(Application, id=application_id, user=user)
    skills_list = application.job.skills.split(',') if application.job.skills else []
    return render(request, 'application-detail.html', {'application': application, 'user': user, 'department': department, 'skills_list': skills_list})

import os
import google.generativeai as genai
from PyPDF2 import PdfReader
import io

# ATS Score Analysis with Gemini LLM
@login_required
def ats_score(request):
    import google.generativeai as genai
    from PyPDF2 import PdfReader
    student = None
    department = None
    ats_result = None
    ats_error = None
    raw_llm_response = None
    resume_url = None
    student_id = request.session.get('student_id')
    if student_id:
        try:
            student = Student.objects.get(id=student_id)
            department = getattr(student, 'department', None)
            resume_text = None
            if student.resume:
                resume_url = student.resume.url
                try:
                    resume_file = student.resume.open('rb')
                    reader = PdfReader(resume_file)
                    resume_text = " ".join([page.extract_text() or '' for page in reader.pages])
                    resume_file.close()
                except Exception as e:
                    resume_text = f"[Resume extraction error: {str(e)}]"
                    ats_error = resume_text
            if resume_text and not ats_error:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                prompt = f'''
You are an advanced ATS (Applicant Tracking System) and resume analysis AI. Analyze the following resume text and provide a detailed ATS report with the following:
1. ATS Score (0-100): A number representing how well this resume would pass an ATS.
2. Keywords Match Bar: Give a percentage bar for each of these: Technical Skills, Soft Skills, Domain Skills (estimate based on resume content).
3. Format Compliance: For each of these (font size, sections, margins), give status as either "correct" (show tick icon) or "incorrect" (show exclamation icon), and for any incorrect, provide a one-line suggestion for improvement.
4. Improvement Suggestions: 5 one-line bullet points for improving the resume.
5. Candidate Summary: A short summary (70-80 words) of the candidate based on their resume, mentioning strengths and notable qualities.

Resume Text:
"""
{resume_text}
"""

Output format (JSON):
{{
    "score": <int>,
    "skills": {{
        "technical": <int>,
        "soft": <int>,
        "domain": <int>
    }},
    "format_compliance": {{
        "font_size": {{"status": "correct"|"incorrect", "suggestion": <string>}},
        "sections": {{"status": "correct"|"incorrect", "suggestion": <string>}},
        "margins": {{"status": "correct"|"incorrect", "suggestion": <string>}}
    }},
    "suggestions": [<string>, ...],
    "summary": <string>
}}
'''
                try:
                    model = genai.GenerativeModel('gemini-2.0-flash')
                    response = model.generate_content(prompt)
                    raw_llm_response = response.text
                    import json as pyjson
                    # Strip markdown code block if present
                    llm_text = response.text.strip()
                    if llm_text.startswith('```json'):
                        llm_text = llm_text[7:]
                    if llm_text.startswith('```'):
                        llm_text = llm_text[3:]
                    if llm_text.endswith('```'):
                        llm_text = llm_text[:-3]
                    llm_text = llm_text.strip()
                    ats_result = pyjson.loads(llm_text)
                except Exception as e:
                    ats_error = f"LLM/JSON error: {str(e)}"
        except Student.DoesNotExist:
            student = None
            department = None
    return render(request, 'ats-score.html', {'user': student, 'department': department, 'ats_result': ats_result, 'resume_url': resume_url, 'ats_error': ats_error, 'raw_llm_response': raw_llm_response})

def interviews(request):
    student = None
    student_id = request.session.get('student_id')
    if student_id:
        try:
            student = Student.objects.get(id=student_id)
            department = getattr(student, 'department', None)
        except Student.DoesNotExist:
            student = None
            department = None
    else:
        department = None

    # Fetch all interviews for this student (by Application.user)
    interviews_qs = Interview.objects.filter(application__user__email=student.email).select_related('application', 'application__job').order_by('scheduled_time') if student else []

    # Split into categories
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    todays_interviews = [iv for iv in interviews_qs if today_start <= iv.scheduled_time < today_end]
    upcoming_interviews = [iv for iv in interviews_qs if iv.scheduled_time >= now and iv.scheduled_time >= today_end]
    history_interviews = [iv for iv in interviews_qs if iv.scheduled_time < now]

    # Find next interview
    next_interview = None
    if interviews_qs:
        for iv in interviews_qs:
            if iv.scheduled_time >= now:
                next_interview = iv
                break

    return render(request, 'interviews.html', {
        'user': student,
        'department': department,
        'todays_interviews': todays_interviews,
        'upcoming_interviews': upcoming_interviews,
        'history_interviews': history_interviews,
        'next_interview': next_interview,
    })

def notifications(request):
    user = None
    department = None
    notifications_today = []
    notifications_yesterday = []
    notifications_older = []
    from django.utils import timezone
    from .models import Student, Application, Interview, Job
    now = timezone.now()
    today = now.date()
    yesterday = today - timezone.timedelta(days=1)
    # Get current student
    student_id = request.session.get('student_id')
    if student_id:
        try:
            student = Student.objects.get(id=student_id)
            user = student
            department = getattr(student, 'department', None)
        except Student.DoesNotExist:
            user = None
            department = None
    elif request.user.is_authenticated:
        try:
            student = Student.objects.get(email=request.user.email)
            user = student
            department = getattr(student, 'department', None)
        except Student.DoesNotExist:
            user = None
            department = None
    # Fetch notifications for the student
    if user:
        # Application status changes (shortlisted, rejected)
        app_statuses = Application.objects.filter(user__email=user.email).order_by('-applied_at')
        for app in app_statuses:
            app_url = None
            try:
                from django.urls import reverse
                app_url = reverse('application_detail', args=[app.id])
            except Exception:
                app_url = None
            if app.status == 'approved':
                notif = {
                    'type': 'shortlisted',
                    'title': 'Application Shortlisted',
                    'desc': f"Your application for {app.job.title} at {app.job.company} has been shortlisted.",
                    'time': app.applied_at,
                    'icon': 'fa-check',
                    'icon_bg': 'bg-green-100',
                    'icon_color': 'text-green-600',
                    'cta': 'View Application →',
                    'url': app_url,
                }
                if app.applied_at.date() == today:
                    notifications_today.append(notif)
                elif app.applied_at.date() == yesterday:
                    notifications_yesterday.append(notif)
                else:
                    notifications_older.append(notif)
            elif app.status == 'rejected':
                notif = {
                    'type': 'rejected',
                    'title': 'Application Rejected',
                    'desc': f"Your application for {app.job.title} at {app.job.company} was not shortlisted.",
                    'time': app.applied_at,
                    'icon': 'fa-times',
                    'icon_bg': 'bg-red-100',
                    'icon_color': 'text-red-600',
                    'cta': 'View Application →',
                    'url': app_url,
                }
                if app.applied_at.date() == today:
                    notifications_today.append(notif)
                elif app.applied_at.date() == yesterday:
                    notifications_yesterday.append(notif)
                else:
                    notifications_older.append(notif)
        # Interview scheduled
        interviews = Interview.objects.filter(application__user__email=user.email).order_by('-scheduled_time')
        for iv in interviews:
            notif = {
                'type': 'interview',
                'title': 'Interview Scheduled',
                'desc': f"Interview scheduled with {iv.application.job.company} for {iv.application.job.title} at {iv.scheduled_time.strftime('%b %d, %H:%M')}",
                'time': iv.scheduled_time,
                'icon': 'fa-calendar',
                'icon_bg': 'bg-blue-100',
                'icon_color': 'text-blue-600',
                'cta': 'View Details →',
            }
            if iv.scheduled_time.date() == today:
                notifications_today.append(notif)
            elif iv.scheduled_time.date() == yesterday:
                notifications_yesterday.append(notif)
            else:
                notifications_older.append(notif)
        # ATS Score updated (if available in session or context)
        ats_score = request.session.get('ats_score')
        ats_score_time = request.session.get('ats_score_time')
        if ats_score and ats_score_time:
            ats_notif = {
                'type': 'ats',
                'title': 'ATS Score Updated',
                'desc': f"Your resume's ATS score is now {ats_score}.",
                'time': ats_score_time,
                'icon': 'fa-robot',
                'icon_bg': 'bg-purple-100',
                'icon_color': 'text-purple-600',
                'cta': 'View Score →',
            }
            # Assume ats_score_time is a datetime string or object
            from datetime import datetime as dt
            ats_time = ats_score_time
            if isinstance(ats_score_time, str):
                try:
                    ats_time = dt.fromisoformat(ats_score_time)
                except Exception:
                    ats_time = now
            if ats_time.date() == today:
                notifications_today.append(ats_notif)
            elif ats_time.date() == yesterday:
                notifications_yesterday.append(ats_notif)
            else:
                notifications_older.append(ats_notif)
        # Job match (new jobs matching department)
        from django.db.models import Q
        jobs = Job.objects.filter(
            Q(skills__icontains=department) | Q(title__icontains=department)
        ).order_by('-created_at')[:2] if department else Job.objects.all().order_by('-created_at')[:2]
        for job in jobs:
            notif = {
                'type': 'job',
                'title': 'New Job Match',
                'desc': f"A new job posting matches your profile: {job.title} at {job.company}",
                'time': job.created_at,
                'icon': 'fa-briefcase',
                'icon_bg': 'bg-yellow-100',
                'icon_color': 'text-yellow-600',
                'cta': 'View Job →',
            }
            if job.created_at.date() == today:
                notifications_today.append(notif)
            elif job.created_at.date() == yesterday:
                notifications_yesterday.append(notif)
            else:
                notifications_older.append(notif)
        # Application deadline reminders (jobs not yet applied to, deadline soon)
        from datetime import timedelta
        soon = now.date() + timedelta(days=2)
        print("Type of soon:", type(soon), soon)
        print("Type of today:", type(today), today)
        for job in Job.objects.all():
            print("Type of job.deadline:", type(job.deadline), job.deadline)
        apps = Application.objects.filter(user__email=user.email)
        applied_job_ids = apps.values_list('job_id', flat=True)
        # Defensive fix: ensure all Job.deadline values are date objects
        for job in Job.objects.all():
            if isinstance(job.deadline, datetime):
                job.deadline = job.deadline.date()
                job.save(update_fields=['deadline'])
        deadline_jobs = Job.objects.exclude(id__in=applied_job_ids).filter(deadline__lte=soon, deadline__gte=today)
        for job in deadline_jobs:
            deadline = job.deadline
            if isinstance(deadline, datetime):
                deadline = deadline.date()
            notif = {
                'type': 'deadline',
                'title': 'Application Deadline Reminder',
                'desc': f"Only { (deadline - today).days } days left to apply for {job.title} at {job.company}",
                'time': job.deadline,
                'icon': 'fa-exclamation-circle',
                'icon_bg': 'bg-red-100',
                'icon_color': 'text-red-600',
                'cta': 'Apply Now →',
            }
            if deadline == today:
                notifications_today.append(notif)
            elif deadline == yesterday:
                notifications_yesterday.append(notif)
            else:
                notifications_older.append(notif)
    # --- Unify notif['time'] type for all notifications, make all timezone-aware ---
    from django.utils.timezone import make_aware, is_aware
    def to_datetime(val):
        if isinstance(val, datetime):
            dt = val
        elif isinstance(val, date):
            dt = datetime.combine(val, time.min)
        else:
            return None
        # Ensure timezone-aware (use current timezone)
        if not is_aware(dt):
            dt = make_aware(dt, timezone.get_current_timezone())
        return dt

    # Before sorting notifications, normalize 'time' to datetime for all
    for notif in notifications_today:
        notif['time'] = to_datetime(notif['time'])
    for notif in notifications_yesterday:
        notif['time'] = to_datetime(notif['time'])
    for notif in notifications_older:
        notif['time'] = to_datetime(notif['time'])
    # Sort notifications by time, newest first
    notifications_today = sorted(notifications_today, key=lambda n: n['time'], reverse=True)
    notifications_yesterday = sorted(notifications_yesterday, key=lambda n: n['time'], reverse=True)
    notifications_older = sorted(notifications_older, key=lambda n: n['time'], reverse=True)
    return render(request, 'notifications.html', {
        'user': user,
        'department': department,
        'notifications_today': notifications_today,
        'notifications_yesterday': notifications_yesterday,
        'notifications_older': notifications_older,
    })

def Ssettings(request):
    student = None
    department = None
    student_id = request.session.get('student_id')
    if student_id:
        try:
            student = Student.objects.get(id=student_id)
            department = getattr(student, 'department', None)
        except Student.DoesNotExist:
            student = None
            department = None
    return render(request, 'Ssettings.html', {'user': student, 'department': department})
    
def job_postings(request):
    recruiter = None
    recruiter_id = request.session.get('recruiter_id')
    if recruiter_id:
        try:
            recruiter = Recruiter.objects.get(id=recruiter_id)
        except Recruiter.DoesNotExist:
            recruiter = None
    # If not recruiter, redirect to login
    if not recruiter:
        messages.error(request, 'You must be logged in as a recruiter to view job postings.')
        return redirect('login')
    # Find the User instance matching the recruiter's email
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        user_instance = User.objects.get(email=recruiter.email)
    except User.DoesNotExist:
        messages.error(request, 'Recruiter user account not found. Please contact support.')
        return redirect('login')
    # Fetch jobs for this recruiter (by User instance)
    jobs = Job.objects.filter(recruiter=user_instance).order_by('-id')
    for job in jobs:
        job.skill_list = job.skills.split(',') if job.skills else []
    return render(request, 'job-postings.html', {'jobs': jobs, 'user': recruiter})

# REMOVE @login_required from applications and make it recruiter-session aware
def applications(request):
    recruiter = None
    recruiter_id = request.session.get('recruiter_id')
    if recruiter_id:
        try:
            recruiter = Recruiter.objects.get(id=recruiter_id)
        except Recruiter.DoesNotExist:
            recruiter = None
    if not recruiter:
        messages.error(request, 'You must be logged in as a recruiter to view applications.')
        return redirect('login')
    # Filter by application_id query param if present
    application_id = request.GET.get('application_id')
    if application_id:
        applications = Application.objects.filter(id=application_id, job__recruiter__email=recruiter.email).select_related('user', 'job').order_by('-applied_at')
    else:
        applications = Application.objects.filter(job__recruiter__email=recruiter.email).select_related('user', 'job').order_by('-applied_at')
    for application in applications:
        application.skill_list = application.job.skills.split(',') if application.job.skills else []
    return render(request, 'applications.html', {'applications': applications, 'user': recruiter})

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import google.generativeai as genai
from PyPDF2 import PdfReader
import io

from django.views.decorators.http import require_GET, require_POST

@require_GET
@login_required
@csrf_exempt
def job_positions_api(request):
    """
    API endpoint to get all job positions for which there are applicants for this recruiter.
    """
    recruiter = request.user
    # Get jobs which have at least one application
    jobs = Job.objects.filter(recruiter=recruiter, application__isnull=False).distinct()
    positions = [
        {
            'id': job.id,
            'title': job.title,
            'company': job.company
        } for job in jobs
    ]
    return JsonResponse({'positions': positions})

@require_POST
@csrf_exempt
# Removed @login_required to allow custom recruiter session checking
#@login_required
def ai_shortlisting_api(request):
    """
    POST endpoint to run AI shortlisting for a selected job, with custom parameters and number to shortlist.
    Now expects params as an array of objects: [{name: ..., checked: ...}, ...]
    """
    import json
    genai.configure(api_key=settings.GEMINI_API_KEY)
    # Custom recruiter session check
    recruiter_id = request.session.get('recruiter_id')
    if not recruiter_id:
        return JsonResponse({'error': 'Not authenticated as recruiter. Please log in again.'}, status=401)
    try:
        recruiter = Recruiter.objects.get(id=recruiter_id)
        # Get corresponding User instance for recruiter
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user_instance = User.objects.get(email=recruiter.email)
    except Recruiter.DoesNotExist:
        return JsonResponse({'error': 'Recruiter not found.'}, status=401)
    except User.DoesNotExist:
        return JsonResponse({'error': 'Recruiter User not found.'}, status=401)
    data = json.loads(request.body.decode())
    job_id = data.get('job_id')
    raw_params = data.get('params', [])
    # Only keep parameters that are checked
    params = [p['name'] for p in raw_params if p.get('checked')]
    num_shortlist = int(data.get('num_shortlist', 3))
    # Only applications for the selected job
    applications = Application.objects.filter(job__recruiter=user_instance, job_id=job_id).select_related('user', 'job')
    results = []
    debug_errors = []
    for app in applications:
        # Extract student info
        student = None
        try:
            student = Student.objects.get(email=app.user.email)
        except Exception as e:
            debug_errors.append(f"Student fetch error for {app.user.email}: {e}")
        resume_text = None
        if student and getattr(student, 'resume', None):
            try:
                resume_file = student.resume.open('rb')
                reader = PdfReader(resume_file)
                resume_text = " ".join([page.extract_text() or '' for page in reader.pages])
                resume_file.close()
            except Exception as e:
                resume_text = None
                debug_errors.append(f"Resume extraction error for {app.user.email}: {e}")
        applicant_data = f"""
Name: {getattr(student, 'full_name', app.user.username)}
Email: {app.user.email}
Department: {getattr(student, 'department', '-')}
Year of Study: {getattr(student, 'year_of_study', '-')}
Resume Text: {resume_text or '-'}
Job Title: {app.job.title}
Company: {app.job.company}
Location: {app.job.location}
Skills: {app.job.skills}
Notes: {app.notes}
"""
        param_prompt = '\n'.join(f'- {p}' for p in params) if params else 'None selected.'
        prompt = f"""
You are an expert recruiter. Given the following applicant information, evaluate and rank the candidate for shortlisting for the position of {app.job.title} at {app.job.company} based on these criteria (in order of importance):
{param_prompt}

For each criterion, provide a brief assessment and assign a score from 1 to 10. Limit your assessment to the 5 most important or relevant criteria for this applicant (if more than 5 are selected, only provide 5 bullet points). Then, provide an overall score (out of {max(len(params)*10, 10)}) and a recommendation: "Shortlist", "Consider", or "Reject", with a short justification.

Applicant Data:
{applicant_data}

Output Format:
- [Assessment for parameter 1]
- [Assessment for parameter 2]
- [Assessment for parameter 3]
- [Assessment for parameter 4]
- [Assessment for parameter 5]
Overall Score: X/{max(len(params)*10, 10)}
Overall Recommendation: [Shortlist/Consider/Reject]
Justification: [Brief explanation]
"""
        try:
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(prompt)
            llm_result = response.text
            import re
            score_match = re.search(r'Overall Score:\s*(\d+)', llm_result)
            overall_score = int(score_match.group(1)) if score_match else 0
        except Exception as e:
            llm_result = f"Error: {str(e)}"
            overall_score = 0
            debug_errors.append(f"LLM error for {app.user.email}: {e}")
        results.append({
            'application_id': app.id,
            'applicant_name': getattr(student, 'full_name', app.user.username),
            'email': app.user.email,
            'llm_result': llm_result,
            'overall_score': overall_score,
        })
    # Sort by score descending and take top N
    results = sorted(results, key=lambda x: x['overall_score'], reverse=True)[:num_shortlist]
    # Add rank
    for idx, r in enumerate(results):
        r['rank'] = idx+1
    # If all results have llm_result with 'Error:', surface debug_errors
    if all('Error:' in r['llm_result'] for r in results) and debug_errors:
        return JsonResponse({'results': results, 'debug_errors': debug_errors}, status=200)
    return JsonResponse({'results': results})

def ai_shortlisting(request):
    recruiter = None
    recruiter_id = request.session.get('recruiter_id')
    jobs = []
    if recruiter_id:
        try:
            recruiter = Recruiter.objects.get(id=recruiter_id)
            # Get User instance for recruiter
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user_instance = User.objects.get(email=recruiter.email)
                jobs = Job.objects.filter(recruiter=user_instance).order_by('-id')
            except User.DoesNotExist:
                jobs = []
        except Recruiter.DoesNotExist:
            recruiter = None
    return render(request, 'ai-shortlisting.html', {'user': recruiter, 'jobs': jobs})

def schedule_interviews(request):
    recruiter = None
    recruiter_id = request.session.get('recruiter_id')
    if recruiter_id:
        try:
            recruiter = Recruiter.objects.get(id=recruiter_id)
        except Recruiter.DoesNotExist:
            recruiter = None
    if not recruiter:
        messages.error(request, 'You must be logged in as a recruiter to schedule interviews.')
        return redirect('login')

    approved_apps = Application.objects.filter(job__recruiter__email=recruiter.email, status='approved')
    upcoming_interviews = Interview.objects.filter(application__job__recruiter__email=recruiter.email, scheduled_time__gte=timezone.now()).select_related('application', 'application__user', 'application__job').order_by('scheduled_time')

    if request.method == 'POST':
        print('--- DEBUG: schedule_interviews POST handler entered ---')
        app_id = request.POST.get('application_id')
        scheduled_time = request.POST.get('scheduled_time')
        gmeet_link_input = request.POST.get('gmeet_link', '').strip()
        print(f'--- DEBUG: Received app_id={app_id}, scheduled_time={scheduled_time}, gmeet_link_input={gmeet_link_input}')
        if not app_id or not scheduled_time:
            print('--- DEBUG: Missing form data ---')
            messages.error(request, 'Please select an applicant and a valid interview date/time.')
            return redirect('schedule_interviews')
        try:
            application = Application.objects.get(id=app_id, job__recruiter__email=recruiter.email)
            print(f'--- DEBUG: Application found: {application}')
        except Application.DoesNotExist:
            print('--- DEBUG: Application not found ---')
            messages.error(request, 'Selected applicant not found or not authorized.')
            return redirect('schedule_interviews')

        # Parse and format scheduled_time safely
        try:
            start_dt = datetime.fromisoformat(scheduled_time)
            print(f'--- DEBUG: Parsed datetime: {start_dt}')
        except Exception as ex:
            print(f'--- DEBUG: Datetime parse error: {ex}')
            messages.error(request, 'Invalid date/time format. Please select a valid date and time.')
            return redirect('schedule_interviews')
        end_dt = start_dt + timedelta(hours=1)
        print(f'--- DEBUG: Calculated end_dt: {end_dt}')

        event = {
            'summary': f'Interview: {application.user.get_full_name() or application.user.email} - {application.job.title}',
            'description': 'Interview scheduled via PlaceMentor',
            'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'Asia/Kolkata'},
            'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'Asia/Kolkata'},
            'attendees': [{'email': application.user.email}],
            'conferenceData': {
                'createRequest': {
                    'requestId': f"meet-{app_id}-{int(timezone.now().timestamp())}"
                }
            }
        }
        print(f'--- DEBUG: Event dict prepared: {event}')
        gmeet_link = gmeet_link_input  # Use manually entered link if provided
        calendar_event_id = ''
        api_success = False
        if not gmeet_link:
            try:
                credentials = service_account.Credentials.from_service_account_file(str(settings.GOOGLE_SERVICE_ACCOUNT_FILE), scopes=['https://www.googleapis.com/auth/calendar'])
                service = build('calendar', 'v3', credentials=credentials)
                created_event = service.events().insert(
                    calendarId='primary',
                    body=event,
                    conferenceDataVersion=1
                ).execute()
                print(f'--- DEBUG: Google Calendar event created: {created_event}')
                calendar_event_id = created_event.get('id', '')
                entry_points = created_event.get('conferenceData', {}).get('entryPoints', [])
                for ep in entry_points:
                    if ep.get('entryPointType') == 'video':
                        gmeet_link = ep.get('uri', '')
                        break
                api_success = True
            except Exception as e:
                print(f'--- DEBUG: Google Calendar API error: {e}')
                messages.error(request, f"Failed to create event: {e}")
        try:
            Interview.objects.create(application=application, scheduled_time=start_dt, gmeet_link=gmeet_link, calendar_event_id=calendar_event_id)
            print(f'--- DEBUG: Interview created in DB for application={application.id}, scheduled_time={start_dt}, gmeet_link={gmeet_link}, calendar_event_id={calendar_event_id}')
            if gmeet_link:
                messages.success(request, 'Interview scheduled and Google Meet link added!')
            elif api_success:
                messages.warning(request, 'Interview scheduled, but Google Meet link could not be generated. Check your Google API configuration.')
            else:
                messages.warning(request, 'Interview scheduled, but Google Calendar event was not created.')
        except Exception as db_ex:
            print(f'--- DEBUG: Interview DB create error: {db_ex}')
            messages.error(request, f'Interview could not be saved: {db_ex}')
        print('--- DEBUG: schedule_interviews POST handler completed ---')
        return redirect('schedule_interviews')
    return render(request, 'schedule-interviews.html', {
        'approved_apps': approved_apps,
        'upcoming_interviews': upcoming_interviews,
        'user': recruiter,
    })

from django.views.decorators.http import require_POST
from django.http import HttpResponseRedirect

@require_POST
def delete_interview(request, interview_id):
    try:
        interview = Interview.objects.get(id=interview_id)
        # Optional: Add permission checks here (e.g., recruiter owns the interview)
        interview.delete()
        messages.success(request, 'Interview deleted successfully!')
    except Interview.DoesNotExist:
        messages.error(request, 'Interview not found.')
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/schedule-interviews/'))

def analytics(request):
    recruiter = None
    recruiter_id = request.session.get('recruiter_id')
    if recruiter_id:
        try:
            recruiter = Recruiter.objects.get(id=recruiter_id)
        except Recruiter.DoesNotExist:
            recruiter = None
    return render(request, 'analytics.html', {'user': recruiter})

def Rsettings(request):
    recruiter = None
    recruiter_id = request.session.get('recruiter_id')
    if recruiter_id:
        try:
            recruiter = Recruiter.objects.get(id=recruiter_id)
        except Recruiter.DoesNotExist:
            recruiter = None
    return render(request, 'Rsettings.html', {'user': recruiter})

from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods


def edit_job(request, job_id):
    recruiter = None
    recruiter_id = request.session.get('recruiter_id')
    if recruiter_id:
        try:
            recruiter = Recruiter.objects.get(id=recruiter_id)
        except Recruiter.DoesNotExist:
            recruiter = None
    if not recruiter:
        messages.error(request, 'You must be logged in as a recruiter to edit jobs.')
        return redirect('login')

    job = get_object_or_404(Job, id=job_id, recruiter__email=recruiter.email)
    if request.method == 'POST':
        job.title = request.POST.get('title')
        job.company = request.POST.get('company')
        job.location = request.POST.get('location')
        job.description = request.POST.get('description')
        job.skills = request.POST.get('skills')
        job.salary = request.POST.get('salary')
        job.deadline = request.POST.get('deadline')
        job.save()
        messages.success(request, 'Job updated successfully!')
        return redirect('job_postings')
    return render(request, 'edit-job.html', {'job': job})

@require_http_methods(["POST"])
def delete_job(request, job_id):
    recruiter = None
    recruiter_id = request.session.get('recruiter_id')
    if recruiter_id:
        try:
            recruiter = Recruiter.objects.get(id=recruiter_id)
        except Recruiter.DoesNotExist:
            recruiter = None
    if not recruiter:
        messages.error(request, 'You must be logged in as a recruiter to delete jobs.')
        return redirect('login')
    job = get_object_or_404(Job, id=job_id, recruiter__email=recruiter.email)
    job.delete()
    messages.success(request, 'Job deleted successfully!')
    return redirect('job_postings')

def create_job(request):
    recruiter = None
    recruiter_id = request.session.get('recruiter_id')
    if recruiter_id:
        try:
            recruiter = Recruiter.objects.get(id=recruiter_id)
        except Recruiter.DoesNotExist:
            recruiter = None
    if not recruiter:
        messages.error(request, 'You must be logged in as a recruiter to create a job.')
        return redirect('login')
    if request.method == 'POST':
        title = request.POST.get('title')
        company = request.POST.get('company')
        location = request.POST.get('location')
        description = request.POST.get('description')
        skills = request.POST.get('skills')
        salary = request.POST.get('salary')
        deadline = request.POST.get('deadline')
        # Find the User instance matching the recruiter's email
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user_instance = User.objects.get(email=recruiter.email)
        except User.DoesNotExist:
            messages.error(request, 'Recruiter user account not found. Please contact support.')
            return redirect('job_postings')
        Job.objects.create(
            recruiter=user_instance,
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
    return render(request, 'create-job.html', {'user': recruiter})

@login_required
@require_POST
def upload_resume(request):
    student = None
    if request.user.is_authenticated:
        try:
            student = Student.objects.get(email=request.user.email)
        except Student.DoesNotExist:
            student = None
    if student and 'resume' in request.FILES:
        resume_file = request.FILES['resume']
        if resume_file.content_type == 'application/pdf':
            student.resume = resume_file
            student.save()
            # Optionally, add a success message
        else:
            # Optionally, add an error message for invalid file type
            pass
    return redirect('student_dashboard')


@csrf_exempt
def application_detail_api(request, application_id):
    from .models import Application, Student
    app = Application.objects.select_related('user', 'job').get(id=application_id)
    # Try to get student profile
    student = None
    try:
        student = Student.objects.get(email=app.user.email)
    except Exception:
        pass
    resume_url = student.resume.url if student and student.resume else None
    data = {
        'id': app.id,
        'status': app.status,
        'applied_at': app.applied_at.strftime('%Y-%m-%d %H:%M'),
        'user': {
            'full_name': getattr(student, 'full_name', app.user.username),
            'email': app.user.email,
            'department': getattr(student, 'department', None),
            'year_of_study': getattr(student, 'year_of_study', None),
        },
        'resume_url': resume_url,
        'job': {
            'title': app.job.title,
            'company': app.job.company,
            'location': app.job.location,
        },
        'notes': app.notes,
    }
    return JsonResponse(data)


@require_POST
@csrf_exempt
def application_action(request, application_id):
    import json
    from .models import Application
    action = request.POST.get('action')
    notes = request.POST.get('notes', '')
    app = Application.objects.get(id=application_id)
    if action == 'approve':
        app.status = 'approved'
    elif action == 'reject':
        app.status = 'rejected'
    if notes:
        app.notes = notes
    app.save()
    return JsonResponse({'success': True, 'status': app.status})

def logout_view(request):
    auth_logout(request)
    return redirect('login')

# REMOVE @login_required from job_list and make it recruiter-session aware
def job_list(request):
    recruiter = None
    recruiter_id = request.session.get('recruiter_id')
    if recruiter_id:
        try:
            recruiter = Recruiter.objects.get(id=recruiter_id)
        except Recruiter.DoesNotExist:
            recruiter = None
    if not recruiter:
        messages.error(request, 'You must be logged in as a recruiter to view job postings.')
        return redirect('login')
    # Fetch jobs for this recruiter
    jobs = Job.objects.filter(recruiter__email=recruiter.email).order_by('-id')
    for job in jobs:
        job.skill_list = job.skills.split(',') if job.skills else []
    return render(request, 'job-postings.html', {'jobs': jobs, 'user': recruiter})
