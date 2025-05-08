from django import forms
from django.contrib.auth.forms import UserCreationForm,AuthenticationForm
from .models import *

class UserRegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'role']

class UserLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    
    
class JobSeekerProfileForm(forms.ModelForm):
    skill_input = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter skills like: Python, React, SQL'
        }),
        label='Your Skills'
    )

    class Meta:
        model = JobSeekerProfile
        fields = ['phone', 'location', 'resume', 'bio', 'skill_input']

    def __init__(self, *args, **kwargs):
        super(JobSeekerProfileForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            existing_skills = ", ".join([s.name for s in self.instance.skills.all()])
            self.fields['skill_input'].initial = existing_skills

    def save(self, commit=True):
        instance = super().save(commit=False)

        if commit:
            instance.save()

            # Handle skill creation
            raw_skills = self.cleaned_data.get('skill_input', '')
            skill_names = [s.strip().lower() for s in raw_skills.split(',') if s.strip()]

            # Remove old skills
            instance.skills.clear()

            for name in skill_names:
                skill_obj, created = Skill.objects.get_or_create(name=name)
                instance.skills.add(skill_obj)

        return instance
        
        
class EmployerProfileForm(forms.ModelForm):
    class Meta:
        model = EmployerProfile
        fields = ['company_name', 'industry', 'website', 'logo', 'description']
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'industry': forms.TextInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'logo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
        }
        
        
class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = [
            'title', 'description', 'skills_required',
            'location', 'salary_min', 'salary_max',
            'job_type', 'expiry_date'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
            'skills_required': forms.Textarea(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'salary_min': forms.NumberInput(attrs={'class': 'form-control'}),
            'salary_max': forms.NumberInput(attrs={'class': 'form-control'}),
            'job_type': forms.Select(attrs={'class': 'form-control'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }