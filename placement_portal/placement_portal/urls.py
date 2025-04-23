"""
URL configuration for placement_portal project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.conf.urls.static import static

from core import views
from core.views import logout_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('signup/', views.signup, name='signup'),
    path('student-dashboard/', views.student_dashboard, name='student_dashboard'),
    path('recruiter-dashboard/', views.recruiter_dashboard, name='recruiter_dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('', views.home, name='home'),
    path('job-openings/', views.job_openings, name='job_openings'),
    path('apply-job/', views.apply_job, name='apply_job'),
    path('my-applications/', views.my_applications, name='my_applications'),
    path('my-applications/<int:application_id>/', views.application_detail, name='application_detail'),
    path('ats-score/', views.ats_score, name='ats_score'),
    path('interviews/', views.interviews, name='interviews'),
    path('notifications/', views.notifications, name='notifications'),
    path('Ssettings/', views.Ssettings, name='Ssettings'),
    path('job-postings/', views.job_list, name='job_postings'),
    path('applications/', views.applications, name='applications'),
    path('ai-shortlisting/', views.ai_shortlisting, name='ai_shortlisting'),
    path('schedule-interviews/', views.schedule_interviews, name='schedule_interviews'),
    path('delete-interview/<int:interview_id>/', views.delete_interview, name='delete_interview'),
    path('analytics/', views.analytics, name='analytics'),
    path('Rsettings/', views.Rsettings, name='Rsettings'),
    path('create-job/', views.create_job, name='create_job'),
    path('edit-job/<int:job_id>/', views.edit_job, name='edit_job'),
    path('delete-job/<int:job_id>/', views.delete_job, name='delete_job'),
    path('upload-resume/', views.upload_resume, name='upload_resume'),
    path('core/application/<int:application_id>/detail/', views.application_detail_api, name='application_detail_api'),
    path('core/application/<int:application_id>/action/', views.application_action, name='application_action'),
    path('core/ai_shortlist/', views.ai_shortlisting_api, name='ai_shortlisting_api'),
    path('core/api/job_positions/', views.job_positions_api, name='job_positions_api'),
   
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
