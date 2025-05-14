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

    seeker, created = JobSeekerProfile.objects.get_or_create(user=request.user)

    form = JobSeekerProfileForm(request.POST or None, request.FILES or None, instance=seeker)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect('seeker-profile')

    context = {
        'form': form,
        'experiences': Experience.objects.filter(seeker=seeker),
        'educations': Education.objects.filter(seeker=seeker),
        'certifications': Certification.objects.filter(seeker=seeker),
        'portfolios': Portfolio.objects.filter(seeker=seeker),
    }
    return render(request, 'core/seeker_profile.html', context)


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

    employer = request.user.employerprofile
    subscription = getattr(employer, 'employersubscription', None)
    job_count = Job.objects.filter(employer=employer).count()

    # Check job posting limit
    if not subscription and job_count >= 1:
        messages.error(request, "You can only post 1 job for free. Purchase a subscription to post more.")
        return redirect('my-jobs')

    if subscription and subscription.plan.max_jobs is not None:
        if job_count >= subscription.plan.max_jobs:
            messages.error(request, "Job posting limit reached for your plan.")
            return redirect('my-jobs')

    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.employer = employer
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
    jobs = Job.objects.filter(is_active=True).order_by('-created_at')
    query = request.GET.get('q')
    if query:
        jobs = jobs.filter(title__icontains=query)

    applied_ids = set()
    saved_job_ids = set()

    if request.user.role == 'seeker':
        seeker = request.user.jobseekerprofile
        applied_ids = set(Application.objects.filter(seeker=seeker).values_list('job_id', flat=True))
        saved_job_ids = set(SavedJob.objects.filter(seeker=seeker).values_list('job_id', flat=True))

    return render(request, 'core/job_list.html', {
        'jobs': jobs,
        'applied_ids': applied_ids,
        'saved_job_ids': saved_job_ids,
        'query': query,
    })
    
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
        return redirect('dashboard')

    seeker = request.user.jobseekerprofile
    seeker_skills = set(seeker.skills.values_list('name', flat=True))
    jobs = Job.objects.filter(is_active=True).order_by('-created_at')

    applied_ids = set(Application.objects.filter(seeker=seeker).values_list('job_id', flat=True))
    saved_jobs = SavedJob.objects.filter(seeker=seeker).select_related('job')
    saved_job_ids = set(saved_jobs.values_list('job__id', flat=True))  # ✅ prepare for template

    # Build recommended
    recommended = []
    for job in jobs:
        job_skills = set(map(str.strip, job.skills_required.lower().split(',')))
        matched = seeker_skills.intersection(job_skills)
        score = round((len(matched) / len(job_skills) * 100), 1) if job_skills else 0
        if score > 0:
            recommended.append((job, score))

    return render(request, 'core/seeker_dashboard.html', {
    'recommended_jobs': recommended[:5],
    'all_jobs': jobs[:5],
    'applied_ids': applied_ids,
    'saved_jobs': saved_jobs,
    'saved_job_ids': saved_job_ids,  # ✅ added
    })

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

@login_required
def add_experience(request):
    if request.user.role != 'seeker':
        return redirect('dashboard')
    seeker = request.user.jobseekerprofile
    form = ExperienceForm(request.POST or None)
    if form.is_valid():
        exp = form.save(commit=False)
        exp.seeker = seeker
        exp.save()
        messages.success(request, "Experience added.")
        return redirect('seeker-profile')
    return render(request, 'core/form_page.html', {'form': form, 'title': 'Add Experience'})


@login_required
def add_education(request):
    if request.user.role != 'seeker':
        return redirect('dashboard')
    seeker = request.user.jobseekerprofile
    form = EducationForm(request.POST or None)
    if form.is_valid():
        edu = form.save(commit=False)
        edu.seeker = seeker
        edu.save()
        messages.success(request, "Education added.")
        return redirect('seeker-profile')
    return render(request, 'core/form_page.html', {'form': form, 'title': 'Add Education'})


@login_required
def add_certification(request):
    if request.user.role != 'seeker':
        return redirect('dashboard')
    seeker = request.user.jobseekerprofile
    form = CertificationForm(request.POST or None)
    if form.is_valid():
        cert = form.save(commit=False)
        cert.seeker = seeker
        cert.save()
        messages.success(request, "Certification added.")
        return redirect('seeker-profile')
    return render(request, 'core/form_page.html', {'form': form, 'title': 'Add Certification'})


@login_required
def add_portfolio(request):
    if request.user.role != 'seeker':
        return redirect('dashboard')
    seeker = request.user.jobseekerprofile
    form = PortfolioForm(request.POST or None)
    if form.is_valid():
        project = form.save(commit=False)
        project.seeker = seeker
        project.save()
        messages.success(request, "Portfolio project added.")
        return redirect('seeker-profile')
    return render(request, 'core/form_page.html', {'form': form, 'title': 'Add Portfolio'})

@login_required
def edit_experience(request, pk):
    exp = get_object_or_404(Experience, id=pk, seeker=request.user.jobseekerprofile)
    form = ExperienceForm(request.POST or None, instance=exp)
    if form.is_valid():
        form.save()
        messages.success(request, "Experience updated.")
        return redirect('seeker-profile')
    return render(request, 'core/form_page.html', {'form': form, 'title': 'Edit Experience'})

@login_required
def delete_experience(request, pk):
    exp = get_object_or_404(Experience, id=pk, seeker=request.user.jobseekerprofile)
    exp.delete()
    messages.success(request, "Experience deleted.")
    return redirect('seeker-profile')

@login_required
def edit_education(request, pk):
    edu = get_object_or_404(Education, id=pk, seeker=request.user.jobseekerprofile)
    form = EducationForm(request.POST or None, instance=edu)
    if form.is_valid():
        form.save()
        messages.success(request, "Education updated.")
        return redirect('seeker-profile')
    return render(request, 'core/form_page.html', {'form': form, 'title': 'Edit Education'})

@login_required
def delete_education(request, pk):
    edu = get_object_or_404(Education, id=pk, seeker=request.user.jobseekerprofile)
    edu.delete()
    messages.success(request, "Education deleted.")
    return redirect('seeker-profile')

@login_required
def edit_certification(request, pk):
    cert = get_object_or_404(Certification, id=pk, seeker=request.user.jobseekerprofile)
    form = CertificationForm(request.POST or None, instance=cert)
    if form.is_valid():
        form.save()
        messages.success(request, "Certification updated.")
        return redirect('seeker-profile')
    return render(request, 'core/form_page.html', {'form': form, 'title': 'Edit Certification'})

@login_required
def delete_certification(request, pk):
    cert = get_object_or_404(Certification, id=pk, seeker=request.user.jobseekerprofile)
    cert.delete()
    messages.success(request, "Certification deleted.")
    return redirect('seeker-profile')

@login_required
def edit_portfolio(request, pk):
    portfolio = get_object_or_404(Portfolio, id=pk, seeker=request.user.jobseekerprofile)
    form = PortfolioForm(request.POST or None, instance=portfolio)
    if form.is_valid():
        form.save()
        messages.success(request, "Portfolio project updated.")
        return redirect('seeker-profile')
    return render(request, 'core/form_page.html', {'form': form, 'title': 'Edit Portfolio'})

@login_required
def delete_portfolio(request, pk):
    portfolio = get_object_or_404(Portfolio, id=pk, seeker=request.user.jobseekerprofile)
    portfolio.delete()
    messages.success(request, "Portfolio project deleted.")
    return redirect('seeker-profile')


@login_required
def save_job(request, job_id):
    if request.user.role != 'seeker':
        return redirect('dashboard')

    seeker = request.user.jobseekerprofile
    job = get_object_or_404(Job, id=job_id)

    # Prevent duplicates
    SavedJob.objects.get_or_create(seeker=seeker, job=job)
    messages.success(request, "Job saved.")
    return redirect('job-list')


@login_required
def unsave_job(request, job_id):
    if request.user.role != 'seeker':
        return redirect('dashboard')

    seeker = request.user.jobseekerprofile
    SavedJob.objects.filter(seeker=seeker, job_id=job_id).delete()
    messages.success(request, "Job removed from saved list.")
    return redirect('seeker-dashboard')  # or 'job-list'


@login_required
def subscription_plans(request):
    if request.user.role != 'employer':
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    plans = SubscriptionPlan.objects.all()
    return render(request, 'core/subscription_plans.html', {'plans': plans})


@login_required
def purchase_subscription(request, plan_id):
    if request.user.role != 'employer':
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    plan = get_object_or_404(SubscriptionPlan, id=plan_id)
    employer = request.user.employerprofile

    # Save subscription
    EmployerSubscription.objects.update_or_create(
        employer=employer,
        defaults={'plan': plan}
    )

    # Save payment
    Payment.objects.create(
        employer=employer,
        plan=plan,
        amount=plan.price
    )

    messages.success(request, f"{plan.name} plan activated!")
    return redirect('my-jobs')


@login_required
def payment_history(request):
    if request.user.role != 'employer':
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    payments = Payment.objects.filter(employer=request.user.employerprofile).order_by('-timestamp')
    return render(request, 'core/payment_history.html', {'payments': payments})