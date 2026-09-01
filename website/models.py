from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django_ckeditor_5.fields import CKEditor5Field


class SingletonModel(models.Model):
    """Base for content that only ever has one row (e.g. site-wide settings)."""
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


# =========================================================
# SITE-WIDE SETTINGS — everything in the topbar, navbar CTAs,
# footer, contact page and hero/admissions banners.
# =========================================================
class SiteSettings(SingletonModel):
    # Identity
    site_name = models.CharField(max_length=150, default="Hamdaan International College")
    site_short_name = models.CharField(max_length=20, default="HIC", help_text="Shown in the compact navbar lockup.")
    tagline = models.CharField(max_length=200, default="Empowering Careers. Transforming Lives. Building a Healthier Future.")
    marketing_phrase = models.CharField(max_length=200, blank=True, default="Build Skills. Save Lives. Impact Communities.")
    logo = models.ImageField(upload_to='branding/', blank=True, null=True, help_text="Leave blank to use the default crest.")

    # Top announcement bar
    announcement_text = models.CharField(max_length=200, blank=True, default="2026/2027 Admission is Now Open — Apply Today")
    announcement_link_text = models.CharField(max_length=50, blank=True, default="Apply Now")
    show_announcement_bar = models.BooleanField(default=True)

    # Admissions status (drives the "OPEN"/"CLOSED" badges site-wide)
    admission_session = models.CharField(max_length=20, default="2026/2027")
    admission_open = models.BooleanField(default=True)

    # Hero section
    hero_badge_text = models.CharField(max_length=100, default="2026/2027 Academic Session — Admission Open")
    hero_headline = models.CharField(max_length=200, default="Build Your Future in Health, Science & Technology.")
    hero_highlight = models.CharField(max_length=100, blank=True, default="Health, Science & Technology.",
                                       help_text="The portion of the headline shown in gold — must match text within the headline.")
    hero_subtext = models.TextField(default="At Hamdaan International College, we equip students with practical knowledge, "
                                             "professional skills and real-world experience to build meaningful careers and "
                                             "contribute to healthier communities.")
    hero_image = models.ImageField(upload_to='hero/', blank=True, null=True)
    hero_primary_cta_text = models.CharField(max_length=50, default="Apply for Admission")
    hero_secondary_cta_text = models.CharField(max_length=50, default="Explore Programmes")

    # About teaser (home page)
    who_we_are_short = models.TextField(
        default="Hamdaan International College of Health, Science and Technology is committed to developing "
                "competent, ethical and innovative professionals equipped to serve communities and contribute to "
                "the healthcare and technology sectors.")

    # Contact & footer
    address_line = models.CharField(max_length=250, default="No. 20 Hayin Bako, Sabon-gari, Zaria, Kaduna State, Nigeria.")
    phone_1 = models.CharField(max_length=30, default="09063447124")
    phone_2 = models.CharField(max_length=30, blank=True, default="09122641898")
    phone_3 = models.CharField(max_length=30, blank=True, default="0912 630 2484")
    email = models.EmailField(default="hamdaanglobalmail@gmail.com")
    office_hours = models.CharField(max_length=200, default="Monday – Friday: 8:00 AM – 5:00 PM · Saturday: 9:00 AM – 1:00 PM")

    # blank, not "#" — URLField validates its value even when the field
    # is only blank=True, so a placeholder like "#" fails validation on
    # every future save of this form until the field is filled with a
    # real URL or cleared. Templates fall back to "#" for display instead
    # (see partials/footer.html / website/contact.html).
    facebook_url = models.URLField(blank=True, default="")
    instagram_url = models.URLField(blank=True, default="")
    twitter_url = models.URLField(blank=True, default="")
    linkedin_url = models.URLField(blank=True, default="")
    whatsapp_number = models.CharField(max_length=30, blank=True, default="2349063447124",
                                        help_text="International format, no plus sign — used for the floating WhatsApp button.")

    footer_about = models.TextField(
        default="Empowering careers, transforming lives and building a healthier future through practical, "
                "industry-relevant health science education.")
    footer_cta_heading = models.CharField(max_length=200, default="Your Future in Health, Science & Technology Starts Here.")
    admission_requirement_note = models.TextField(
        default="Five (5) O'Level credit passes including English Language, Mathematics, Chemistry, Physics and Biology.")
    admission_requirement_disclaimer = models.TextField(
        default="This is sample / general admission information provided for demonstration purposes. Specific "
                "programmes may have additional requirements — please contact the Admissions Office for full details.")

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return "Site Settings"


class Statistic(models.Model):
    """Animated counters on the homepage (e.g. '1,200+ Students')."""
    label = models.CharField(max_length=60)
    value = models.PositiveIntegerField(help_text="Numeric value the counter animates up to, e.g. 1200.")
    suffix = models.CharField(max_length=5, blank=True, default="+", help_text="Shown after the number, e.g. '+' or '%'.")
    icon = models.CharField(max_length=50, blank=True, help_text="Font Awesome class, e.g. fa-user-graduate.")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.value}{self.suffix} {self.label}"


class WhyChooseItem(models.Model):
    """The six 'Why Choose Hamdaan' feature cards."""
    icon = models.CharField(max_length=50, default="fa-star", help_text="Font Awesome class, e.g. fa-award.")
    title = models.CharField(max_length=100)
    description = models.TextField()
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.title


class CoreValue(models.Model):
    """Core values shown on the About page (Excellence, Integrity, ...)."""
    icon = models.CharField(max_length=50, default="fa-star")
    title = models.CharField(max_length=60)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']
        verbose_name_plural = "Core Values"

    def __str__(self):
        return self.title


# =========================================================
# ABOUT PAGE
# =========================================================
class AboutContent(SingletonModel):
    who_we_are = CKEditor5Field(config_name='default', 
        default="<p>Hamdaan International College of Health, Science and Technology is committed to developing "
                "competent, ethical and innovative professionals equipped to serve communities and contribute "
                "meaningfully to the healthcare and technology sectors.</p>")
    about_image = models.ImageField(upload_to='about/', blank=True, null=True)
    mission = CKEditor5Field(config_name='default', default="<p>To provide accessible, practical and industry-relevant health science and "
                                     "technology education that prepares graduates to deliver excellent service to "
                                     "their communities and advance in their chosen careers.</p>")
    vision = CKEditor5Field(config_name='default', default="<p>To be a leading health, science and technology institution in West Africa, "
                                    "recognised for producing skilled, ethical and innovative professionals who "
                                    "transform lives and communities.</p>")

    principal_name = models.CharField(max_length=100, default="Dr. Amina Yusuf")
    principal_title = models.CharField(max_length=100, default="Principal / Chief Executive")
    principal_message = CKEditor5Field(config_name='default',
        default="<p>At Hamdaan International College, we believe education is the most powerful tool for "
                "transforming lives and communities. Our commitment goes beyond the classroom — we are building a "
                "generation of health, science and technology professionals who are skilled, compassionate and "
                "ready to serve.</p>")
    principal_photo = models.ImageField(upload_to='about/', blank=True, null=True)
    principal_bio = CKEditor5Field(
        config_name='default', blank=True,
        help_text="A short biography — shown under the welcome message on the About page and the homepage's "
                   "Founder & CEO section.",
        default="",
    )

    class Meta:
        verbose_name = "About Page Content"
        verbose_name_plural = "About Page Content"

    def __str__(self):
        return "About Page Content"


# =========================================================
# ACADEMICS
# =========================================================
class Department(models.Model):
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    head_name = models.CharField(max_length=100, blank=True)
    icon = models.CharField(max_length=50, default="fa-building-columns")
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Programme(models.Model):
    CATEGORY_CHOICES = [
        ('ND', 'National Diploma'),
        ('PD', 'Professional Diploma'),
        ('CERT', 'Professional Certification'),
    ]

    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    code = models.CharField(max_length=20, blank=True)
    category = models.CharField(max_length=6, choices=CATEGORY_CHOICES, default='ND')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='programmes')
    duration = models.CharField(max_length=40, default="2 Years")
    image = models.ImageField(upload_to='programmes/', blank=True, null=True)
    description = models.TextField()
    requirement = models.TextField(
        default="Five (5) O'Level credit passes including English Language, Mathematics, Chemistry, Physics and Biology.")
    careers = models.TextField(
        blank=True, help_text="One career opportunity per line.",
        default="Government Health Facilities\nPrivate Hospitals & Clinics\nNGOs & Community Health Programmes\nFurther Professional Studies")
    is_featured = models.BooleanField(default=False, help_text="Feature this programme prominently on the Programmes page.")
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug, i = base, 1
            while Programme.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                i += 1
                slug = f"{base}-{i}"
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def career_list(self):
        return [c.strip() for c in self.careers.splitlines() if c.strip()]

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('website:programme_detail', args=[self.slug])


# =========================================================
# FACILITIES & STUDENT LIFE
# =========================================================
class Facility(models.Model):
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=250)
    image = models.ImageField(upload_to='facilities/')
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name_plural = "Facilities"

    def __str__(self):
        return self.name


class StudentLifeActivity(models.Model):
    icon = models.CharField(max_length=50, default="fa-people-group")
    title = models.CharField(max_length=100)
    description = models.TextField()
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name_plural = "Student Life Activities"

    def __str__(self):
        return self.title


# =========================================================
# NEWS & EVENTS
# =========================================================
class NewsArticle(models.Model):
    STATUS_CHOICES = [('draft', 'Draft'), ('published', 'Published')]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    category = models.CharField(max_length=60, default="Academics")
    author = models.CharField(max_length=100, default="Public Relations Unit")
    date = models.DateField(default=timezone.now)
    image = models.ImageField(upload_to='news/', blank=True, null=True)
    excerpt = models.TextField(max_length=300)
    content = CKEditor5Field(config_name='default')
    is_featured = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='published')

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)
            slug, i = base, 1
            while NewsArticle.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                i += 1
                slug = f"{base}-{i}"
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('website:news_detail', args=[self.slug])


class Event(models.Model):
    title = models.CharField(max_length=200)
    date = models.DateField()
    location = models.CharField(max_length=150)
    category = models.CharField(max_length=60, default="Academics")
    description = models.TextField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['date']

    def __str__(self):
        return self.title


# =========================================================
# GALLERY
# =========================================================
class GalleryCategory(models.Model):
    name = models.CharField(max_length=80, unique=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = "Gallery Categories"

    def __str__(self):
        return self.name


class GalleryImage(models.Model):
    category = models.ForeignKey(GalleryCategory, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='gallery/')
    caption = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', '-id']

    def __str__(self):
        return self.caption or f"Image #{self.pk}"


# =========================================================
# CONTACT & ADMISSIONS
# =========================================================
class ContactMessage(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.name} — {self.subject}"


# Application/Application-fee moved to the `admissions` and `payments` apps
# (see admissions.models.Application, payments.models.ApplicationInvoice).


# =========================================================
# CAREERS
# =========================================================
class JobPosting(models.Model):
    EMPLOYMENT_TYPE_CHOICES = [
        ('Full-time', 'Full-time'), ('Part-time', 'Part-time'),
        ('Contract', 'Contract'), ('Internship', 'Internship'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    department = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=150, default='Zaria, Kaduna State')
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE_CHOICES, default='Full-time')
    description = CKEditor5Field(config_name='default')
    requirements = CKEditor5Field(config_name='default', blank=True)
    deadline = models.DateField(
        help_text="Applications close at the end of this date — the posting is then automatically "
                   "hidden from the public Careers page, no manual step needed.",
    )
    is_active = models.BooleanField(default=True, help_text="Uncheck to close a posting early, before its deadline.")
    posted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-posted_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)
            slug, i = base, 1
            while JobPosting.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                i += 1
                slug = f"{base}-{i}"
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def is_open(self):
        """Whether this posting still accepts applications — the single
        source of truth both the public list (which just filters on it)
        and the detail page's Apply form (which checks it directly) use."""
        return self.is_active and self.deadline >= timezone.now().date()

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('website:job_detail', args=[self.slug])


class JobApplication(models.Model):
    STATUS_CHOICES = [
        ('new', 'New'), ('shortlisted', 'Shortlisted'), ('rejected', 'Rejected'), ('hired', 'Hired'),
    ]

    job = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='applications')
    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    cover_letter = models.TextField(blank=True)
    resume = models.FileField(upload_to='job_applications/')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='new')
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.full_name} — {self.job.title}"
