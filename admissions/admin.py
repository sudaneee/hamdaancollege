from django.contrib import admin

from admissions.models import AdmissionCycle, Application, ApplicationStatusLog


class ApplicationStatusLogInline(admin.TabularInline):
    model = ApplicationStatusLog
    extra = 0
    readonly_fields = ('stage', 'note', 'changed_by', 'created_at')
    can_delete = False


@admin.register(AdmissionCycle)
class AdmissionCycleAdmin(admin.ModelAdmin):
    list_display = ('session', 'is_active', 'fee', 'opens_at', 'closes_at', 'created_at')
    list_editable = ('is_active', 'fee')
    ordering = ['-created_at']


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('application_number', 'full_name', 'cycle', 'programme', 'status', 'payment_status', 'is_submitted', 'submitted_at')
    list_filter = ('status', 'is_submitted', 'cycle', 'programme')
    search_fields = ('application_number', 'surname', 'first_name', 'email', 'phone', 'applicant__email')
    readonly_fields = ('application_number', 'applicant', 'cycle', 'created_at', 'submitted_at')
    date_hierarchy = 'submitted_at'
    inlines = [ApplicationStatusLogInline]
    fieldsets = (
        ('Application', {'fields': ('application_number', 'applicant', 'cycle', 'status', 'is_submitted', 'submitted_at')}),
        ('Section A — Personal Information', {'fields': (
            'surname', 'first_name', 'middle_name', 'date_of_birth', 'gender', 'nationality',
            'state_of_origin', 'lga', 'marital_status', 'religion', 'address', 'phone', 'alt_phone', 'email')}),
        ('Section B — Next of Kin / Guardian', {'fields': (
            'guardian_name', 'guardian_relationship', 'guardian_occupation', 'guardian_address', 'guardian_phone')}),
        ('Section C — Programme', {'fields': ('programme',)}),
        ('Section D — Educational Background', {'fields': (
            'previous_school', 'qualification_obtained', 'qualification_year')}),
        ("Section E — O'Level Results", {'fields': (
            ('english_grade', 'english_exam_body', 'english_year'),
            ('maths_grade', 'maths_exam_body', 'maths_year'),
            ('chemistry_grade', 'chemistry_exam_body', 'chemistry_year'),
            ('physics_grade', 'physics_exam_body', 'physics_year'),
            ('biology_grade', 'biology_exam_body', 'biology_year'),
        )}),
        ('Documents', {'fields': (
            'passport_photo', 'olevel_result', 'birth_certificate', 'identification_document')}),
        ('Section F — Declaration', {'fields': ('declaration_accepted',)}),
    )
