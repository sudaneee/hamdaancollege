from django import forms
from .models import ContactMessage


class ContactForm(forms.Form):
    name = forms.CharField(max_length=120, widget=forms.TextInput(attrs={'placeholder': 'Enter your full name'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'you@example.com'}))
    subject = forms.CharField(max_length=200, widget=forms.TextInput(attrs={'placeholder': 'What is this regarding?'}))
    message = forms.CharField(widget=forms.Textarea(attrs={'placeholder': 'Write your message here...'}))

    def save(self):
        return ContactMessage.objects.create(**self.cleaned_data)
