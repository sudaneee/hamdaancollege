from django.contrib import admin

from payments.models import ApplicationInvoice, ApplicationPayment


class ApplicationPaymentInline(admin.TabularInline):
    model = ApplicationPayment
    extra = 0
    readonly_fields = ('reference', 'gateway_reference', 'gateway_response', 'paid_at', 'receipt_number', 'created_at')


@admin.register(ApplicationInvoice)
class ApplicationInvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'application', 'amount', 'status', 'generated_at')
    list_filter = ('status',)
    search_fields = ('invoice_number', 'application__application_number', 'application__applicant__email')
    readonly_fields = ('invoice_number', 'generated_at')
    inlines = [ApplicationPaymentInline]


@admin.register(ApplicationPayment)
class ApplicationPaymentAdmin(admin.ModelAdmin):
    list_display = ('reference', 'invoice', 'amount', 'gateway', 'status', 'paid_at')
    list_filter = ('gateway', 'status')
    search_fields = ('reference', 'gateway_reference', 'invoice__invoice_number')
    readonly_fields = ('reference', 'gateway_reference', 'gateway_response', 'created_at')
