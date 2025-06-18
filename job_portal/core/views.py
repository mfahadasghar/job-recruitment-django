from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from .forms import *
from django.contrib.auth.views import LoginView,LogoutView
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import login
from .models import *
from django.db.models import Q
from django.views.decorators.http import require_POST
from datetime import datetime
from django.core.paginator import Paginator

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful!')

            if user.role == 'seeker':
                JobSeekerProfile.objects.create(user=user)
                return redirect('job-list')
            elif user.role == 'employer':
                EmployerProfile.objects.create(user=user)
                return redirect('employer-dashboard')
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

    def get_success_url(self):
        if self.request.user.role == 'seeker':
            from django.urls import reverse
            return reverse('job-list')
        elif self.request.user.role == 'employer':
            from django.urls import reverse
            return reverse('employer-dashboard')
        from django.urls import reverse
        return reverse('dashboard')
    
class CustomLogoutView(LogoutView):
    def dispatch(self, request, *args, **kwargs):
        messages.info(request, 'You have been logged out.')
        return super().dispatch(request, *args, **kwargs)


@login_required
def dashboard(request):
    if request.user.role == 'seeker':
        return redirect('job-list')
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
        return redirect('subscription-plans')

    if subscription and subscription.plan.max_jobs is not None:
        if job_count >= subscription.plan.max_jobs:
            messages.error(request, "Job posting limit reached for your plan.")
            return redirect('subscription-plans')

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
            return redirect('employer-dashboard')
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
    
def job_list(request):
    search = request.GET.get('search', '')
    location = request.GET.get('location', '')

    jobs = Job.objects.all()
    if search:
        jobs = jobs.filter(title__icontains=search)
    if location:
        jobs = jobs.filter(location__icontains=location)

    applied_ids = set()
    saved_job_ids = set()

    if request.user.role == 'seeker':
        seeker = request.user.jobseekerprofile
        applied_ids = set(Application.objects.filter(seeker=seeker).values_list('job_id', flat=True))
        saved_job_ids = set(SavedJob.objects.filter(seeker=seeker).values_list('job_id', flat=True))
        
    paginator = Paginator(jobs, 5)  # 10 jobs per page
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)

    context = {
        'page_obj': page_obj,
        'search': search,
        'location': location,
        'applied_ids': applied_ids,  # previously defined
        'saved_job_ids': saved_job_ids,  # previously defined
    }
    return render(request, 'core/job_list.html', context)

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

    paginator = Paginator(job_data, 6)  # show 6 per page
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)

    context = {
        'job_data': page_obj,
    }
    return render(request, 'core/employer_dashboard.html', context)

def view_applicants(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    applications = Application.objects.filter(job=job)

    status = request.GET.get('status')
    if status:
        applications = applications.filter(status=status)

    return render(request, 'core/view_applicants.html', {
        'job': job,
        'applications': applications,
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

    SavedJob.objects.get_or_create(seeker=seeker, job=job)
    messages.success(request, "Job saved.")
    search = request.GET.get('search', '')
    location = request.GET.get('location', '')
    selected = request.GET.get('job', '')
    page_num = request.GET.get('page', '')

    return redirect(f"{reverse('job-list')}?search={search}&location={location}&job={selected}&page={page_num}")


@login_required
def unsave_job(request, job_id):
    if request.user.role != 'seeker':
        return redirect('dashboard')

    seeker = request.user.jobseekerprofile
    SavedJob.objects.filter(seeker=seeker, job_id=job_id).delete()
    messages.success(request, "Job removed from saved.")
    search = request.GET.get('search', '')
    location = request.GET.get('location', '')
    selected = request.GET.get('job', '')
    page_num = request.GET.get('page', '')

    return redirect(f"{reverse('job-list')}?search={search}&location={location}&job={selected}&page={page_num}")


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

@login_required
def report_job(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    if request.method == 'POST':
        form = JobReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.reported_job = job
            report.save()
            messages.success(request, "Your report has been submitted.")
            return redirect('job-detail', job_id=job_id)
    else:
        form = JobReportForm()
    return render(request, 'core/report_job.html', {'form': form, 'job': job})

@login_required
def job_detail(request, job_id):
    job = get_object_or_404(Job, id=job_id)

    applied = False
    saved = False

    if request.user.role == 'seeker':
        seeker = request.user.jobseekerprofile
        applied = Application.objects.filter(job=job, seeker=seeker).exists()
        saved = SavedJob.objects.filter(job=job, seeker=seeker).exists()

    return render(request, 'core/job_detail.html', {
        'job': job,
        'applied': applied,
        'saved': saved
    })
    
@login_required
def view_reports(request):
    if request.user.role != 'admin':  # Adjust this as per your user roles
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    reports = Report.objects.select_related('reporter', 'reported_job').order_by('-created_at')
    return render(request, 'core/view_reports.html', {'reports': reports})


def landing_page(request):
    if request.user.is_authenticated:
        if request.user.role == 'seeker':
            return redirect('job-list')
        elif request.user.role == 'employer':
            return redirect('employer-dashboard')
        else:
            return redirect('/admin/')
    else:
        return render(request, 'core/landing.html')
    
    
@login_required
def saved_jobs_page(request):
    if request.user.role != 'seeker':
        messages.error(request, "Not authorized.")
        return redirect('dashboard')

    seeker = request.user.jobseekerprofile
    saved_jobs = SavedJob.objects.filter(seeker=seeker).select_related('job')

    paginator = Paginator(saved_jobs, 6)  # show 6 per page
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)

    return render(request, 'core/saved_jobs.html', {
        'saved_jobs': page_obj
    })
    
@login_required
def applied_jobs_page(request):
    if request.user.role != 'seeker':
        messages.error(request, "Not authorized.")
        return redirect('dashboard')

    seeker = request.user.jobseekerprofile
    applications = Application.objects.filter(seeker=seeker).select_related('job')

    paginator = Paginator(applications, 6)  # show 6 applications per page
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)

    return render(request, 'core/applied_jobs.html', {
        'applications': page_obj
    })
    
@login_required
def inbox(request):
    """Show all conversations for the current user with last message and unread count."""
    messages_qs = Message.objects.filter(
        Q(sender=request.user) | Q(recipient=request.user)
    ).order_by('-timestamp')

    conversations = []
    counterpart_ids = set()

    for message in messages_qs:
        counterpart = message.sender if message.sender != request.user else message.recipient
        if counterpart.id not in counterpart_ids:
            unread_count = Message.objects.filter(
                sender=counterpart, recipient=request.user, is_read=False
            ).count()
            conversations.append((counterpart, message, unread_count))
            counterpart_ids.add(counterpart.id)

    thread_recipient = None
    messages = []
    thread_recipient_id = None

    thread = request.GET.get('thread')
    if thread and thread.isdigit():
        thread_recipient = User.objects.get(id=int(thread))
        thread_recipient_id = int(thread)

        messages = Message.objects.filter(
            Q(sender=request.user, recipient=thread_recipient) | Q(sender=thread_recipient, recipient=request.user)
        ).order_by('timestamp')

        messages.update(is_read=True)  # marking messages as read when opening thread

    context = {
        'conversations': conversations,
        'thread_recipient': thread_recipient,
        'thread_recipient_id': thread_recipient_id,
        'inbox_messages': messages,
    }
    return render(request, 'core/inbox.html', context)

@login_required
def thread(request, recipient_id):
    recipient = User.objects.get(id=recipient_id)
    messages = Message.objects.filter(
        Q(sender=request.user, recipient=recipient) | Q(sender=recipient, recipient=request.user)
    ).order_by('timestamp')

    if request.method == "POST":
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = request.user
            message.recipient = recipient
            message.timestamp = datetime.now()
            message.save()
            return redirect(f"{reverse('inbox')}?thread={recipient.id}")
    else:
        form = MessageForm()

    context = {
        "messages": messages,
        "form": form,
        "recipient": recipient,
    }
    return render(request, 'core/thread.html', context)


def schedule_interview(request, application_id):
    application = get_object_or_404(Application, id=application_id, job__employer__user=request.user)

    if request.method == "POST":
        scheduled_at = request.POST['scheduled_at']  # ISO format or "2025-06-14T15:30"
        location = request.POST['location']

        interview = Interview.objects.create(
            application=application,
            scheduled_at=datetime.fromisoformat(scheduled_at),
            location=location
        )
        messages.success(request, "Interview successfully scheduled.")
        return redirect('view-applicants', application.job.id)

    return render(request, 'core/schedule_interview.html', {
        'application': application
    })