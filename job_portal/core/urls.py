from django.urls import path
from .views import *


urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('register/', register, name='register'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(next_page='login'), name='logout'),
    path('seeker/profile/', seeker_profile, name='seeker-profile'),
    path('employer/profile/', employer_profile, name='employer-profile'),
    path('employer/jobs/post/', post_job, name='post-job'),
    path('employer/jobs/', my_jobs, name='my-jobs'),
    path('employer/jobs/<int:job_id>/edit/', edit_job, name='edit-job'),
    path('employer/jobs/<int:job_id>/delete/', delete_job, name='delete-job'),
    path('jobs/', job_list, name='job-list'),
    path('jobs/<int:job_id>/apply/', apply_job, name='apply-job'),
    path('seeker/dashboard/', seeker_dashboard, name='seeker-dashboard'),
    path('employer/dashboard/', employer_dashboard, name='employer-dashboard'),
    path('employer/job/<int:job_id>/applicants/', view_applicants, name='view-applicants'),
    path('employer/applicant/<int:application_id>/update/', update_applicant_status, name='update-applicant-status'),
]