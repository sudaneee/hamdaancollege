from django.core.management.base import BaseCommand

from students.models import FeeStructure, FeeStructureItem
from website.models import Programme

SESSION = '2026/2027'

# Every fee-breakdown document the school issued lists the same ten fixed
# first-semester line items, in the same order — only the amounts differ
# per programme (see FEE_SCHEDULES below).
FIRST_SEMESTER_LABELS = [
    'Admission/Application Form', 'Registration Fee', 'Tuition/School Fees', 'Acceptance Fee',
    'Laboratory/Practical Fees', 'Examination Fee', 'ID Card', 'Primary Health Insurance Fee',
    'ICT Fee', 'Late Registration Fee',
]

# Charges every schedule lists as not-yet-fixed — shown to students for
# transparency but never counted in FeeStructure.amount (see its docstring).
VARIABLE_ITEMS = [
    ('Hostel Accommodation', 'To Be Announced'),
    ('Uniforms/Scrubs', 'To Be Announced'),
    ('Books/Handouts', 'To Be Announced'),
    ('Any Other Charges', 'As Applicable'),
]

# Programme codes (website.models.Programme) sharing one fee schedule ->
# (first-semester amounts in FIRST_SEMESTER_LABELS order, second-semester
# tuition amount). Source: the school's official 2026/2027 fee-breakdown
# documents — one PDF per schedule, some covering several programmes at
# once (e.g. HIM/Environmental Health/Nutrition share one document).
FEE_SCHEDULES = {
    ('ND-CHEW',): ([5000, 5000, 65000, 5000, 10000, 5000, 5000, 10000, 5000, 5000], 60000),
    ('ND-HIM', 'ND-EH', 'ND-ND'): ([3000, 5000, 30000, 5000, 7000, 5000, 5000, 10000, 5000, 5000], 40000),
    ('ND-PT', 'ND-MLT'): ([5000, 5000, 85000, 5000, 10000, 5000, 5000, 10000, 5000, 5000], 70000),
    ('ND-PH',): ([3000, 5000, 50000, 5000, 7000, 5000, 5000, 10000, 5000, 5000], 50000),
    # Professional Certifications — one semester only, no second-semester charge.
    ('CERT-BES',): ([3000, 3000, 30000, 3000, 5000, 3000, 3000, 4000, 3000, 3000], 0),
    ('CERT-BNC',): ([3000, 3000, 30000, 3000, 5000, 3000, 3000, 4000, 3000, 3000], 0),
    ('CERT-BOC',): ([3000, 3000, 30000, 3000, 5000, 3000, 3000, 4000, 3000, 3000], 0),
}


class Command(BaseCommand):
    help = (
        "Seed/reset the 2026/2027 fee structures + breakdown items from the "
        "school's official fee-breakdown documents. Safe to re-run — each "
        "programme's items are replaced wholesale, so this always matches "
        "the source documents exactly (use the console's Fee Structures / "
        "Fee Breakdown Items pages for day-to-day edits or new sessions)."
    )

    def handle(self, *args, **options):
        for codes, (first_sem_amounts, second_sem_amount) in FEE_SCHEDULES.items():
            for code in codes:
                try:
                    programme = Programme.objects.get(code=code)
                except Programme.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f'No Programme with code {code} — skipped.'))
                    continue

                structure, _ = FeeStructure.objects.get_or_create(programme=programme, session=SESSION)
                structure.items.all().delete()

                order = 0
                for label, amount in zip(FIRST_SEMESTER_LABELS, first_sem_amounts):
                    order += 1
                    FeeStructureItem.objects.create(
                        fee_structure=structure, category='First Semester',
                        label=label, amount=amount, order=order,
                    )
                if second_sem_amount:
                    order += 1
                    FeeStructureItem.objects.create(
                        fee_structure=structure, category='Second Semester',
                        label='Tuition & Academic Charges', amount=second_sem_amount, order=order,
                    )
                for label, note in VARIABLE_ITEMS:
                    order += 1
                    FeeStructureItem.objects.create(
                        fee_structure=structure, category='Variable / Additional Charges',
                        label=label, amount=None, note=note, order=order,
                    )

                self.stdout.write(self.style.SUCCESS(
                    f'{programme.code} ({programme.name}) - {SESSION}: NGN {structure.amount:,.2f}'
                ))
