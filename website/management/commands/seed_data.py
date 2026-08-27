from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from admissions.models import AdmissionCycle
from website.models import (
    SiteSettings, AboutContent, Statistic, WhyChooseItem, CoreValue,
    Department, Programme, Facility, StudentLifeActivity, NewsArticle,
    Event, GalleryCategory, GalleryImage,
)

UNSPLASH = "https://images.unsplash.com/photo-{}?auto=format&fit=crop&w={}&q=80"


class Command(BaseCommand):
    help = "Seed the database with the initial Hamdaan International College content."

    def handle(self, *args, **options):
        self.stdout.write("Seeding site settings...")
        SiteSettings.load()
        AboutContent.load()

        if not AdmissionCycle.objects.exists():
            self.stdout.write("Seeding admission cycle...")
            # ₦3,000 matches the fee printed on the school's paper admission form.
            AdmissionCycle.objects.create(session="2026/2027", is_active=True, fee=3000)

        if not Statistic.objects.exists():
            self.stdout.write("Seeding statistics...")
            for label, value, suffix, icon in [
                ("Students", 1200, "+", "fa-user-graduate"),
                ("Qualified Staff", 35, "+", "fa-chalkboard-user"),
                ("Academic Programmes", 12, "+", "fa-graduation-cap"),
                ("Modern Facilities", 8, "+", "fa-building-columns"),
                ("Student Satisfaction", 95, "%", "fa-face-smile"),
            ]:
                Statistic.objects.create(label=label, value=value, suffix=suffix, icon=icon, order=len(Statistic.objects.all()))

        if not WhyChooseItem.objects.exists():
            self.stdout.write("Seeding why-choose items...")
            for icon, title, desc in [
                ("fa-award", "Quality Education", "Learn from experienced and dedicated professionals committed to academic excellence."),
                ("fa-flask", "Practical Training", "Gain hands-on experience through structured practical and laboratory sessions."),
                ("fa-building-columns", "Modern Facilities", "Access laboratories, smart classrooms and well-resourced learning environments."),
                ("fa-briefcase-medical", "Career Development", "Prepare for employment, entrepreneurship and long-term professional growth."),
                ("fa-user-graduate", "Experienced Faculty", "Learn from qualified academic and industry professionals across every department."),
                ("fa-hands-holding-child", "Supportive Environment", "Study in a safe, inclusive and student-focused environment built for growth."),
            ]:
                WhyChooseItem.objects.create(icon=icon, title=title, description=desc, order=len(WhyChooseItem.objects.all()))

        if not CoreValue.objects.exists():
            self.stdout.write("Seeding core values...")
            for icon, title in [
                ("fa-star", "Excellence"), ("fa-handshake", "Integrity"), ("fa-lightbulb", "Innovation"),
                ("fa-people-group", "Service"), ("fa-briefcase", "Professionalism"), ("fa-heart", "Compassion"),
            ]:
                CoreValue.objects.create(icon=icon, title=title, order=len(CoreValue.objects.all()))

        depts = {}
        if not Department.objects.exists():
            self.stdout.write("Seeding departments...")
            for name, head, icon, desc in [
                ("Department of Community Health", "Dr. Amina Yusuf", "fa-heart-pulse", "Preparing community health professionals to deliver primary care and lead public health initiatives."),
                ("Department of Medical Laboratory Science", "Mal. Ibrahim Musa", "fa-microscope", "Training competent laboratory technicians for accurate diagnostic services."),
                ("Department of Environmental Health", "Mrs. Hadiza Sani", "fa-leaf", "Producing environmental health officers safeguarding public sanitation and safety."),
                ("Department of Health Information Management", "Mr. Suleiman Garba", "fa-database", "Equipping students with digital health records and data management expertise."),
                ("Department of Nutrition & Dietetics", "Mrs. Fatima Bello", "fa-apple-whole", "Developing dietetic professionals for clinical and community nutrition practice."),
                ("Department of Pharmacy", "Mal. Yusuf Abdullahi", "fa-prescription-bottle-medical", "Training pharmacy technicians for safe medication dispensing and patient care."),
            ]:
                depts[name] = Department.objects.create(name=name, head_name=head, icon=icon, description=desc, order=len(depts))
        else:
            depts = {d.name: d for d in Department.objects.all()}

        dept_by_key = {
            'chew': depts.get("Department of Community Health"),
            'mlt': depts.get("Department of Medical Laboratory Science"),
            'env': depts.get("Department of Environmental Health"),
            'him': depts.get("Department of Health Information Management"),
            'nut': depts.get("Department of Nutrition & Dietetics"),
            'pharm': depts.get("Department of Pharmacy"),
        }

        if not Programme.objects.exists():
            self.stdout.write("Seeding programmes...")
            careers = "Government Health Facilities\nPrivate Hospitals & Clinics\nNGOs & Community Health Programmes\nFurther Professional Studies"
            nd = [
                ("ND-CHEW", "Community Health Extension Workers", 'chew', "Diagnose common ailments, deliver primary healthcare and lead community health education campaigns across rural and urban settings."),
                ("ND-MLT", "Medical Laboratory Technician", 'mlt', "Perform clinical laboratory investigations including haematology, microbiology and clinical chemistry to support accurate diagnosis."),
                ("ND-PH", "Public Health", 'chew', "Design and implement community health programmes, disease surveillance and health promotion initiatives."),
                ("ND-EH", "Environmental Health", 'env', "Monitor sanitation, food safety and environmental hazards to protect public health standards."),
                ("ND-HIM", "Health Information Management", 'him', "Manage patient records, healthcare data systems and medical information governance."),
                ("ND-ND", "Nutrition and Dietetics", 'nut', "Plan therapeutic diets, promote healthy eating and manage nutrition programmes in clinical and community settings."),
                ("ND-PT", "Pharmacy Technician", 'pharm', "Support pharmacists in dispensing, inventory management and patient medication counselling."),
            ]
            pd = [
                ("DIP-CHEW", "Diploma in Community Health Extension Workers", 'chew', "A professional-track diploma building advanced competence in community health service delivery."),
                ("DIP-MLT", "Diploma in Medical Laboratory Technician", 'mlt', "Advanced diploma deepening laboratory diagnostic skills for working professionals."),
                ("DIP-PH", "Diploma in Public Health", 'chew', "Professional diploma in public health programme design, monitoring and evaluation."),
                ("DIP-EH", "Diploma in Environmental Health", 'env', "Professional diploma covering advanced sanitation inspection and environmental risk management."),
                ("DIP-HIM", "Diploma in Health Information Management", 'him', "Professional diploma in digital health records and information systems management."),
                ("DIP-ND", "Diploma in Nutrition and Dietetics", 'nut', "Professional diploma in clinical nutrition therapy and dietetic practice."),
                ("DIP-PT", "Diploma in Pharmacy Technician", 'pharm', "Professional diploma advancing pharmaceutical dispensing and patient care competence."),
            ]
            cert = [
                ("CERT-BOC", "Certificate in Basic Obstetric Care", 'chew', "Short professional certification in safe delivery practices and maternal emergency care."),
                ("CERT-BNC", "Certificate in Basic Neonatal Care", 'chew', "Certification focused on newborn care, resuscitation and early infant health monitoring."),
                ("CERT-BES", "Certificate in Basic Emergency Services", 'chew', "Certification in first response, trauma stabilisation and emergency service protocols."),
            ]
            order = 0
            for code, name, dept_key, desc in nd:
                Programme.objects.create(code=code, name=name, category='ND', department=dept_by_key[dept_key],
                                          duration="2 Years", description=desc, careers=careers,
                                          is_featured=(code == "ND-MLT"), order=order)
                order += 1
            for code, name, dept_key, desc in pd:
                Programme.objects.create(code=code, name=name, category='PD', department=dept_by_key[dept_key],
                                          duration="1 Year", description=desc, careers=careers, order=order)
                order += 1
            for code, name, dept_key, desc in cert:
                Programme.objects.create(code=code, name=name, category='CERT', department=dept_by_key[dept_key],
                                          duration="3 - 6 Months", description=desc, careers=careers, order=order)
                order += 1

        # Facility and GalleryImage both require a real uploaded image, so they are
        # intentionally left for the admin to add via Django admin rather than
        # seeded with placeholder/hotlinked photos.

        if not StudentLifeActivity.objects.exists():
            self.stdout.write("Seeding student life activities...")
            for icon, title, desc in [
                ("fa-people-group", "Student Clubs", "Join academic and social clubs that build leadership and lasting friendships."),
                ("fa-heart-pulse", "Health Awareness", "Participate in campaigns promoting community health and wellness."),
                ("fa-chalkboard-user", "Seminars", "Attend seminars led by industry professionals and guest lecturers."),
                ("fa-flask-vial", "Practical Training", "Build real skills through structured laboratory and field sessions."),
                ("fa-hands-holding-circle", "Community Outreach", "Serve underserved communities through organised outreach programmes."),
                ("fa-futbol", "Sports", "Compete in inter-departmental sporting events throughout the session."),
                ("fa-flag", "Student Associations", "Represent your voice through departmental and college-wide associations."),
                ("fa-briefcase", "Career Development", "Access mentorship, internships and career-readiness workshops."),
            ]:
                StudentLifeActivity.objects.create(icon=icon, title=title, description=desc, order=len(StudentLifeActivity.objects.all()))

        if not Event.objects.exists():
            self.stdout.write("Seeding events...")
            for title, date, loc, cat, desc in [
                ("Orientation Programme for New Students", "2026-09-10", "Main Auditorium", "Academics", "Welcoming newly admitted students with campus tours and academic briefings."),
                ("Health Awareness Week", "2026-09-22", "College Grounds", "Community", "A week of free health screenings, seminars and public health education."),
                ("Inter-Departmental Sports Fiesta", "2026-10-03", "Sports Complex", "Student Life", "Annual sports competition between academic departments."),
                ("Career Development Seminar", "2026-10-15", "Conference Hall", "Career", "A seminar preparing final-year students for employment and entrepreneurship."),
                ("Matriculation Ceremony", "2026-09-28", "Main Auditorium", "Academics", "Formal induction of newly admitted students into the college."),
            ]:
                Event.objects.create(title=title, date=date, location=loc, category=cat, description=desc)

        if not NewsArticle.objects.exists():
            self.stdout.write("Seeding news...")
            items = [
                ("2026/2027 Admission Now Open", "Admissions", "Admissions Office", "2026-07-01",
                 "Hamdaan International College has officially opened applications for the 2026/2027 academic session across all programmes.",
                 "<p>Prospective students are encouraged to apply early as slots are limited across all departments. The application process is fully online, with applicants required to submit personal information, academic qualifications and supporting documents.</p>", True),
                ("Hamdaan Students Complete Community Health Outreach", "Community", "Public Relations Unit", "2026-06-18",
                 "Final year Community Health Extension Workers students successfully completed a two-week outreach programme in rural communities around Zaria.",
                 "<p>The outreach included free health screenings, immunisation support and health education sessions reaching over 800 community members.</p>", False),
                ("New Laboratory Equipment Commissioned", "Facilities", "Principal's Office", "2026-05-22",
                 "The college has commissioned new diagnostic laboratory equipment to strengthen practical training.",
                 "<p>The equipment upgrade includes modern haematology analysers and microscopy stations.</p>", False),
                ("Orientation Programme Announced for New Students", "Academics", "Registrar's Office", "2026-08-05",
                 "The college has announced the schedule for the orientation programme welcoming newly admitted students.",
                 "<p>The orientation will cover academic expectations, campus facilities and student support services.</p>", False),
            ]
            for title, cat, author, date, excerpt, content, featured in items:
                NewsArticle.objects.create(title=title, category=cat, author=author, date=date, excerpt=excerpt,
                                            content=content, is_featured=featured, status='published')

        if not GalleryCategory.objects.exists():
            self.stdout.write("Seeding gallery categories (upload images via admin)...")
            for name in ["Campus", "Laboratories", "Students", "Events", "Practical Sessions", "Community Outreach"]:
                GalleryCategory.objects.create(name=name, order=len(GalleryCategory.objects.all()))

        User = get_user_model()
        if not User.objects.filter(is_superuser=True).exists():
            self.stdout.write(self.style.WARNING("Creating default superuser admin/admin12345 — change this password immediately."))
            User.objects.create_superuser('admin', 'admin@hamdaancollege.edu.ng', 'admin12345')

        self.stdout.write(self.style.SUCCESS("Seeding complete."))
