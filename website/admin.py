from django.contrib import admin
from django.utils.html import format_html

from . import models


# =========================================================
# SITE SETTINGS / ABOUT — singletons, no add/delete allowed
# =========================================================
class SingletonAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not self.model.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = self.model.load()
        from django.shortcuts import redirect
        from django.urls import reverse
        return redirect(reverse(f'admin:{self.model._meta.app_label}_{self.model._meta.model_name}_change', args=[obj.pk]))


@admin.register(models.SiteSettings)
class SiteSettingsAdmin(SingletonAdmin):
    fieldsets = (
        ("Identity", {'fields': ('site_name', 'site_short_name', 'tagline', 'marketing_phrase', 'logo')}),
        ("Announcement Bar", {'fields': ('show_announcement_bar', 'announcement_text', 'announcement_link_text')}),
        ("Admissions Status", {'fields': ('admission_session', 'admission_open')}),
        ("Homepage Hero", {'fields': (
            'hero_badge_text', 'hero_headline', 'hero_highlight', 'hero_subtext', 'hero_image',
            'hero_primary_cta_text', 'hero_secondary_cta_text')}),
        ("About Teaser (Homepage)", {'fields': ('who_we_are_short',)}),
        ("Contact Details", {'fields': (
            'address_line', 'phone_1', 'phone_2', 'phone_3', 'email', 'office_hours')}),
        ("Social Media", {'fields': (
            'facebook_url', 'instagram_url', 'twitter_url', 'linkedin_url', 'whatsapp_number')}),
        ("Footer", {'fields': ('footer_about', 'footer_cta_heading')}),
        ("Admission Requirements", {'fields': ('admission_requirement_note', 'admission_requirement_disclaimer')}),
    )


@admin.register(models.AboutContent)
class AboutContentAdmin(SingletonAdmin):
    fieldsets = (
        ("Who We Are", {'fields': ('who_we_are', 'about_image')}),
        ("Mission & Vision", {'fields': ('mission', 'vision')}),
        ("Principal's Message", {'fields': ('principal_name', 'principal_title', 'principal_message', 'principal_photo')}),
    )


# =========================================================
# HOMEPAGE CONTENT LISTS
# =========================================================
@admin.register(models.Statistic)
class StatisticAdmin(admin.ModelAdmin):
    list_display = ('label', 'value', 'suffix', 'icon', 'order')
    list_editable = ('value', 'suffix', 'order')
    ordering = ('order',)


@admin.register(models.WhyChooseItem)
class WhyChooseItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'icon', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    ordering = ('order',)


@admin.register(models.CoreValue)
class CoreValueAdmin(admin.ModelAdmin):
    list_display = ('title', 'icon', 'order')
    list_editable = ('order',)
    ordering = ('order',)


# =========================================================
# ACADEMICS
# =========================================================
class ProgrammeInline(admin.TabularInline):
    model = models.Programme
    fields = ('name', 'category', 'is_active', 'order')
    extra = 0
    show_change_link = True


@admin.register(models.Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'head_name', 'is_active', 'order')
    list_editable = ('order', 'is_active')
    search_fields = ('name', 'head_name')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProgrammeInline]


@admin.register(models.Programme)
class ProgrammeAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'department', 'duration', 'is_featured', 'is_active', 'order')
    list_editable = ('is_featured', 'is_active', 'order')
    list_filter = ('category', 'department', 'is_active')
    search_fields = ('name', 'code', 'description')
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
        (None, {'fields': ('name', 'slug', 'code', 'category', 'department', 'duration', 'image')}),
        ("Content", {'fields': ('description', 'requirement', 'careers')}),
        ("Visibility", {'fields': ('is_featured', 'is_active', 'order')}),
    )


# =========================================================
# FACILITIES & STUDENT LIFE
# =========================================================
@admin.register(models.Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ('name', 'thumb', 'order', 'is_active')
    list_editable = ('order', 'is_active')

    def thumb(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:40px;border-radius:6px;">', obj.image.url)
        return "—"
    thumb.short_description = "Preview"


@admin.register(models.StudentLifeActivity)
class StudentLifeActivityAdmin(admin.ModelAdmin):
    list_display = ('title', 'icon', 'order', 'is_active')
    list_editable = ('order', 'is_active')


# =========================================================
# NEWS & EVENTS
# =========================================================
@admin.register(models.NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'date', 'author', 'status', 'is_featured')
    list_editable = ('status', 'is_featured')
    list_filter = ('status', 'category', 'is_featured')
    search_fields = ('title', 'excerpt', 'content')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'date'


@admin.register(models.Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'location', 'category', 'is_active')
    list_editable = ('is_active',)
    list_filter = ('category', 'is_active')
    date_hierarchy = 'date'


# =========================================================
# GALLERY
# =========================================================
class GalleryImageInline(admin.TabularInline):
    model = models.GalleryImage
    fields = ('image', 'caption', 'order')
    extra = 1


@admin.register(models.GalleryCategory)
class GalleryCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'order', 'image_count')
    list_editable = ('order',)
    inlines = [GalleryImageInline]

    def image_count(self, obj):
        return obj.images.count()
    image_count.short_description = "Images"


@admin.register(models.GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ('caption', 'category', 'thumb', 'order')
    list_editable = ('order',)
    list_filter = ('category',)

    def thumb(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:40px;border-radius:6px;">', obj.image.url)
        return "—"
    thumb.short_description = "Preview"


# =========================================================
# CONTACT & ADMISSIONS
# =========================================================
@admin.register(models.ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'submitted_at', 'is_read')
    list_editable = ('is_read',)
    list_filter = ('is_read',)
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('name', 'email', 'subject', 'message', 'submitted_at')

    def has_add_permission(self, request):
        return False


# Application admin now lives in admissions/admin.py (models.Application
# moved to the admissions app).
