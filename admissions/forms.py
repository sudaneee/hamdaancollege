from django import forms

from admissions.models import Application
from website.models import Programme

NIGERIAN_STATES = [
    ('', 'Select state'), ('Kaduna', 'Kaduna'), ('Kano', 'Kano'), ('Katsina', 'Katsina'),
    ('Jigawa', 'Jigawa'), ('Abuja', 'Abuja'), ('Bauchi', 'Bauchi'), ('Plateau', 'Plateau'),
    ('Sokoto', 'Sokoto'), ('Zamfara', 'Zamfara'),
]


def _field_class(extra=''):
    return {'class': ('field-input ' + extra).strip()}


class ApplicationForm(forms.ModelForm):
    state_of_origin = forms.ChoiceField(choices=NIGERIAN_STATES)
    programme = forms.ModelChoiceField(queryset=Programme.objects.none(), empty_label="Select a programme")

    class Meta:
        model = Application
        fields = [
            # Section A — Personal
            'surname', 'first_name', 'middle_name', 'date_of_birth', 'gender', 'nationality',
            'state_of_origin', 'lga', 'marital_status', 'religion', 'address', 'phone', 'alt_phone', 'email',
            # Section B — Guardian / Next of Kin
            'guardian_name', 'guardian_relationship', 'guardian_occupation', 'guardian_address', 'guardian_phone',
            # Section C — Programme
            'programme',
            # Section D — Educational Background
            'previous_school', 'qualification_obtained', 'qualification_year',
            # Section E — O'Level Results
            'english_grade', 'english_exam_body', 'english_year',
            'maths_grade', 'maths_exam_body', 'maths_year',
            'chemistry_grade', 'chemistry_exam_body', 'chemistry_year',
            'physics_grade', 'physics_exam_body', 'physics_year',
            'biology_grade', 'biology_exam_body', 'biology_year',
            # Documents
            'passport_photo', 'olevel_result', 'birth_certificate', 'identification_document',
            # Section F — Declaration
            'declaration_accepted',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs=_field_class() | {'type': 'date'}),
            'surname': forms.TextInput(attrs=_field_class('') | {'placeholder': 'Surname'}),
            'first_name': forms.TextInput(attrs=_field_class() | {'placeholder': 'First name'}),
            'middle_name': forms.TextInput(attrs=_field_class() | {'placeholder': 'Middle name (optional)'}),
            'lga': forms.TextInput(attrs=_field_class() | {'placeholder': 'e.g. Zaria'}),
            'religion': forms.TextInput(attrs=_field_class() | {'placeholder': 'e.g. Islam, Christianity'}),
            'address': forms.TextInput(attrs=_field_class() | {'placeholder': 'Home address'}),
            'phone': forms.TextInput(attrs=_field_class() | {'placeholder': '080XXXXXXXX'}),
            'alt_phone': forms.TextInput(attrs=_field_class() | {'placeholder': 'Optional'}),
            'email': forms.EmailInput(attrs=_field_class() | {'placeholder': 'you@example.com'}),
            'guardian_name': forms.TextInput(attrs=_field_class() | {'placeholder': "Guardian's full name"}),
            'guardian_occupation': forms.TextInput(attrs=_field_class() | {'placeholder': 'Occupation'}),
            'guardian_address': forms.TextInput(attrs=_field_class() | {'placeholder': "Guardian's address"}),
            'guardian_phone': forms.TextInput(attrs=_field_class() | {'placeholder': '080XXXXXXXX'}),
            'previous_school': forms.TextInput(attrs=_field_class() | {'placeholder': 'Name of school attended'}),
            'qualification_obtained': forms.TextInput(attrs=_field_class() | {'placeholder': 'e.g. SSCE'}),
            'qualification_year': forms.TextInput(attrs=_field_class() | {'placeholder': 'e.g. 2024'}),
            'english_year': forms.TextInput(attrs=_field_class() | {'placeholder': 'Year'}),
            'maths_year': forms.TextInput(attrs=_field_class() | {'placeholder': 'Year'}),
            'chemistry_year': forms.TextInput(attrs=_field_class() | {'placeholder': 'Year'}),
            'physics_year': forms.TextInput(attrs=_field_class() | {'placeholder': 'Year'}),
            'biology_year': forms.TextInput(attrs=_field_class() | {'placeholder': 'Year'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['programme'].queryset = Programme.objects.filter(is_active=True)
        self.fields['programme'].widget.attrs.update(_field_class())
        for name in ('gender', 'nationality', 'marital_status', 'guardian_relationship',
                     'english_grade', 'english_exam_body', 'maths_grade', 'maths_exam_body',
                     'chemistry_grade', 'chemistry_exam_body', 'physics_grade', 'physics_exam_body',
                     'biology_grade', 'biology_exam_body', 'state_of_origin'):
            self.fields[name].widget.attrs.update(_field_class())

    def clean_declaration_accepted(self):
        accepted = self.cleaned_data.get('declaration_accepted')
        if not accepted:
            raise forms.ValidationError('You must accept the declaration to submit your application.')
        return accepted
