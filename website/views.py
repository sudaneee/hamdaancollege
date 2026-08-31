from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404

from .forms import ContactForm
from .models import (
    AboutContent, Statistic, WhyChooseItem, CoreValue, Department, Programme,
    Facility, StudentLifeActivity, NewsArticle, Event, GalleryCategory, GalleryImage,
)


def home(request):
    programmes = Programme.objects.filter(is_active=True, category='ND')[:6]
    featured = Programme.objects.filter(is_featured=True, is_active=True).first() \
        or Programme.objects.filter(is_active=True).first()
    context = {
        'page': 'home',
        'statistics': Statistic.objects.all(),
        'why_choose_items': WhyChooseItem.objects.filter(is_active=True),
        'programmes': programmes,
        'featured_programme': featured,
        'news_items': NewsArticle.objects.filter(status='published')[:3],
        'core_values': CoreValue.objects.all()[:6],
        'about_content': AboutContent.load(),
    }
    return render(request, 'website/home.html', context)


def about(request):
    context = {
        'page': 'about',
        'about_content': AboutContent.load(),
        'core_values': CoreValue.objects.all(),
        'departments': Department.objects.filter(is_active=True),
    }
    return render(request, 'website/about.html', context)


def programmes(request):
    category = request.GET.get('category', 'All')
    qs = Programme.objects.filter(is_active=True)
    if category != 'All':
        qs = qs.filter(category=category)
    featured = Programme.objects.filter(is_featured=True, is_active=True).first()
    context = {
        'page': 'programmes',
        'programmes': qs,
        'active_category': category,
        'categories': Programme.CATEGORY_CHOICES,
        'featured_programme': featured,
    }
    return render(request, 'website/programmes.html', context)


def programme_detail(request, slug):
    programme = get_object_or_404(Programme, slug=slug, is_active=True)
    related = Programme.objects.filter(category=programme.category, is_active=True).exclude(pk=programme.pk)[:3]
    return render(request, 'website/programme_detail.html', {
        'page': 'programmes', 'programme': programme, 'related_programmes': related,
    })


def admissions(request):
    return render(request, 'website/admissions.html', {'page': 'admissions'})


def departments(request):
    return render(request, 'website/departments.html', {
        'page': 'departments',
        'departments': Department.objects.filter(is_active=True).prefetch_related('programmes'),
    })


def facilities(request):
    return render(request, 'website/facilities.html', {
        'page': 'facilities',
        'facilities': Facility.objects.filter(is_active=True),
    })


def student_life(request):
    return render(request, 'website/student_life.html', {
        'page': 'student-life',
        'activities': StudentLifeActivity.objects.filter(is_active=True),
        'events': Event.objects.filter(is_active=True)[:5],
    })


def news_list(request):
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', 'All')

    qs = NewsArticle.objects.filter(status='published')
    if category != 'All':
        qs = qs.filter(category=category)
    if query:
        qs = qs.filter(title__icontains=query)

    featured = NewsArticle.objects.filter(status='published', is_featured=True).first() \
        or NewsArticle.objects.filter(status='published').first()

    paginator = Paginator(qs, 6)
    page_obj = paginator.get_page(request.GET.get('page'))

    categories = NewsArticle.objects.filter(status='published').values_list('category', flat=True).distinct()

    return render(request, 'website/news.html', {
        'page': 'news',
        'featured_article': featured,
        'page_obj': page_obj,
        'categories': categories,
        'active_category': category,
        'query': query,
        'events': Event.objects.filter(is_active=True)[:6],
    })


def news_detail(request, slug):
    article = get_object_or_404(NewsArticle, slug=slug, status='published')
    return render(request, 'website/news_detail.html', {'page': 'news', 'article': article})


def gallery(request):
    category_id = request.GET.get('category', '')
    categories = GalleryCategory.objects.all()
    images = GalleryImage.objects.select_related('category')
    if category_id:
        images = images.filter(category_id=category_id)
    return render(request, 'website/gallery.html', {
        'page': 'gallery',
        'categories': categories,
        'images': images,
        'active_category': category_id,
    })


def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Thank you for contacting us. Our admissions team will respond shortly.")
            return redirect('website:contact')
    else:
        form = ContactForm()
    return render(request, 'website/contact.html', {'page': 'contact', 'form': form})


# Application/apply flow lives in the `admissions` app now (see
# admissions.views.apply) — it's account + payment gated.


def search(request):
    query = request.GET.get('q', '').strip()
    results = {'programmes': [], 'news': [], 'events': []}
    if query:
        results['programmes'] = Programme.objects.filter(is_active=True).filter(name__icontains=query)[:8]
        results['news'] = NewsArticle.objects.filter(status='published').filter(title__icontains=query)[:8]
        results['events'] = Event.objects.filter(is_active=True).filter(title__icontains=query)[:8]
    return render(request, 'website/search_results.html', {'page': 'search', 'query': query, 'results': results})
