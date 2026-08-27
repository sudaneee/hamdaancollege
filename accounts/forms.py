from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django import forms


def _attrs(placeholder, extra=None):
    attrs = {'class': 'field-input', 'placeholder': placeholder}
    if extra:
        attrs.update(extra)
    return attrs


class RegisterForm(forms.Form):
    first_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs=_attrs('First name')))
    last_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs=_attrs('Last name')))
    email = forms.EmailField(widget=forms.EmailInput(attrs=_attrs('you@example.com')))
    phone = forms.CharField(max_length=30, widget=forms.TextInput(attrs=_attrs('080XXXXXXXX')))
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput(attrs=_attrs('Create a password')))
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput(attrs=_attrs('Re-enter your password')))

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists. Try logging in instead.')
        return email

    def clean(self):
        cleaned = super().clean()
        password1, password2 = cleaned.get('password1'), cleaned.get('password2')
        if password1 and password2 and password1 != password2:
            self.add_error('password2', "Passwords don't match.")
        if password1:
            try:
                validate_password(password1)
            except forms.ValidationError as exc:
                self.add_error('password1', exc)
        return cleaned


class VerifyCodeForm(forms.Form):
    code = forms.CharField(
        max_length=6, min_length=6,
        widget=forms.TextInput(attrs=_attrs('000000', {'inputmode': 'numeric', 'autocomplete': 'one-time-code'})),
    )


class LoginForm(forms.Form):
    identifier = forms.CharField(
        label='Email or Username',
        widget=forms.TextInput(attrs=_attrs('you@example.com or username')),
    )
    password = forms.CharField(widget=forms.PasswordInput(attrs=_attrs('Your password')))
