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
    path('seeker/add-experience/', add_experience, name='add-experience'),
    path('seeker/add-education/', add_education, name='add-education'),
    path('seeker/add-certification/', add_certification, name='add-certification'),
    path('seeker/add-portfolio/', add_portfolio, name='add-portfolio'),
    path('seeker/experience/<int:pk>/edit/', edit_experience, name='edit-experience'),
    path('seeker/experience/<int:pk>/delete/', delete_experience, name='delete-experience'),
    path('seeker/education/<int:pk>/edit/', edit_education, name='edit-education'),
    path('seeker/education/<int:pk>/delete/', delete_education, name='delete-education'),
    path('seeker/certification/<int:pk>/edit/', edit_certification, name='edit-certification'),
    path('seeker/certification/<int:pk>/delete/', delete_certification, name='delete-certification'),
    path('seeker/portfolio/<int:pk>/edit/', edit_portfolio, name='edit-portfolio'),
    path('seeker/portfolio/<int:pk>/delete/', delete_portfolio, name='delete-portfolio'),
    path('jobs/<int:job_id>/save/', save_job, name='save-job'),
    path('jobs/<int:job_id>/unsave/', unsave_job, name='unsave-job'),

]