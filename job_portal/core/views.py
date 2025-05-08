from django.shortcuts import render, redirect, get_object_or_404
from .forms import *
from django.contrib.auth.views import LoginView,LogoutView
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import login
from .models import *
from django.db.models import Q
from django.views.decorators.http import require_POST

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('dashboard')
    else:
        form = UserRegisterForm()
    return render(request, 'core/register.html', {'form': form})


class CustomLoginView(LoginView):
    template_name = 'core/login.html'
    authentication_form = UserLoginForm

    def form_valid(self, form):
        messages.success(self.request, 'Login successful!')
        return super().form_valid(form)
    
class CustomLogoutView(LogoutView):
    def dispatch(self, request, *args, **kwargs):
        messages.info(request, 'You have been logged out.')
        return super().dispatch(request, *args, **kwargs)


@login_required
def dashboard(request):
    if request.user.role == 'seeker':
        return redirect('seeker-dashboard')
    elif request.user.role == 'employer':
        return redirect('employer-dashboard')
    else:
        return redirect('/admin/')
    
@login_required
def seeker_profile(request):
    if request.user.role != 'seeker':
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    profile, created = JobSeekerProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = JobSeekerProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect('seeker-profile')
    else:
        form = JobSeekerProfileForm(instance=profile)
    return render(request, 'core/seeker_profile.html', {'form': form})


@login_required
def employer_profile(request):
    if request.user.role != 'employer':
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    profile, created = EmployerProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = EmployerProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Company profile updated.")
            return redirect('employer-profile')
    else:
        form = EmployerProfileForm(instance=profile)
    return render(request, 'core/employer_profile.html', {'form': form})


@login_required
def post_job(request):
    if request.user.role != 'employer':
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.employer = request.user.employerprofile  # requires related_name or OneToOne
            job.save()
            messages.success(request, "Job posted successfully!")
            return redirect('my-jobs')
    else:
        form = JobForm()
    return render(request, 'core/post_job.html', {'form': form})


@login_required
def my_jobs(request):
    if request.user.role != 'employer':
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    jobs = Job.objects.filter(employer=request.user.employerprofile)
    return render(request, 'core/my_jobs.html', {'jobs': jobs})

@login_required
def edit_job(request, job_id):
    job = get_object_or_404(Job, id=job_id, employer=request.user.employerprofile)
    
    if request.method == 'POST':
        form = JobForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            messages.success(request, 'Job updated successfully.')
            return redirect('my-jobs')
    else:
        form = JobForm(instance=job)
    
    return render(request, 'core/edit_job.html', {'form': form})


@login_required
def delete_job(request, job_id):
    job = get_object_or_404(Job, id=job_id, employer=request.user.employerprofile)

    if request.method == 'POST':
        job.delete()
        messages.success(request, 'Job deleted successfully.')
        return redirect('my-jobs')
    
    return render(request, 'core/delete_job.html', {'job': job})

@login_required
def job_list(request):
    if request.user.role != 'seeker':
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    query = request.GET.get('q')
    jobs = Job.objects.filter(is_active=True).order_by('-created_at')

    if query:
        jobs = jobs.filter(
            Q(title__icontains=query) |
            Q(location__icontains=query) |
            Q(skills_required__icontains=query)
        )

    applied_ids = Application.objects.filter(seeker=request.user.jobseekerprofile).values_list('job_id', flat=True)
    
    return render(request, 'core/job_list.html', {'jobs': jobs,'query': query,'applied_ids': applied_ids})

@login_required
def apply_job(request, job_id):
    if request.user.role != 'seeker':
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    job = get_object_or_404(Job, id=job_id, is_active=True)
    seeker_profile = request.user.jobseekerprofile

    if Application.objects.filter(job=job, seeker=seeker_profile).exists():
        messages.warning(request, "You've already applied to this job.")
        return redirect('job-list')

    if request.method == 'POST':
        cover_letter = request.POST.get('cover_letter')
        Application.objects.create(
            job=job,
            seeker=seeker_profile,
            resume=seeker_profile.resume,
            cover_letter=cover_letter,
        )
        messages.success(request, "Application submitted!")
        return redirect('job-list')

    return render(request, 'core/apply_job.html', {'job': job})


@login_required
def seeker_dashboard(request):
    if request.user.role != 'seeker':
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    seeker = request.user.jobseekerprofile
    seeker_skills = set(seeker.skills.values_list('name', flat=True))
    jobs = Job.objects.filter(is_active=True).order_by('-created_at')

    # Get applied job IDs
    applied_ids = set(Application.objects.filter(seeker=seeker).values_list('job_id', flat=True))

    # Recommended jobs with match score
    recommended = []
    for job in jobs:
        job_skills = set(map(str.strip, job.skills_required.lower().split(',')))
        matched = seeker_skills.intersection(job_skills)
        score = round((len(matched) / len(job_skills) * 100), 1) if job_skills else 0
        if score > 0:
            recommended.append((job, score))

    context = {
        'recommended_jobs': recommended[:5],
        'all_jobs': jobs[:5],
        'applied_ids': applied_ids,
    }
    return render(request, 'core/seeker_dashboard.html', context)

@login_required
def employer_dashboard(request):
    if request.user.role != 'employer':
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    employer_profile = request.user.employerprofile
    jobs = Job.objects.filter(employer=employer_profile)

    job_data = []
    for job in jobs:
        applicants = Application.objects.filter(job=job)
        job_data.append({
            'job': job,
            'applicant_count': applicants.count()
        })

    return render(request, 'core/employer_dashboard.html', {'job_data': job_data})

@login_required
def view_applicants(request, job_id):
    if request.user.role != 'employer':
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    job = get_object_or_404(Job, id=job_id, employer=request.user.employerprofile)
    applications = Application.objects.filter(job=job).select_related('seeker__user')

    return render(request, 'core/view_applicants.html', {
        'job': job,
        'applications': applications
    })
    
@require_POST
@login_required
def update_applicant_status(request, application_id):
    if request.user.role != 'employer':
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    app = get_object_or_404(Application, id=application_id)
    if app.job.employer != request.user.employerprofile:
        messages.error(request, "You are not authorized.")
        return redirect('employer-dashboard')

    new_status = request.POST.get('status')
    if new_status in dict(Application._meta.get_field('status').choices):
        app.status = new_status
        app.save()
        messages.success(request, f"Status updated to {new_status.capitalize()}.")

    return redirect('view-applicants', job_id=app.job.id)