from django import forms
from .models import ContactMessage, JobApplication


class ContactForm(forms.Form):
    name = forms.CharField(max_length=120, widget=forms.TextInput(attrs={'placeholder': 'Enter your full name'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'you@example.com'}))
    subject = forms.CharField(max_length=200, widget=forms.TextInput(attrs={'placeholder': 'What is this regarding?'}))
    message = forms.CharField(widget=forms.Textarea(attrs={'placeholder': 'Write your message here...'}))

    def save(self):
        return ContactMessage.objects.create(**self.cleaned_data)


class JobApplicationForm(forms.ModelForm):
    class Meta:
        model = JobApplication
        fields = ['full_name', 'email', 'phone', 'cover_letter', 'resume']
        widgets = {
            'full_name': forms.TextInput(attrs={'placeholder': 'Enter your full name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'you@example.com'}),
            'phone': forms.TextInput(attrs={'placeholder': '08012345678'}),
            'cover_letter': forms.Textarea(attrs={'placeholder': 'Tell us why you\'re a good fit for this role...', 'rows': 5}),
        }
