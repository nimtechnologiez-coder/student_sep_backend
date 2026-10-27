from django.contrib import admin
from django.utils.html import format_html
from .models import FeePayment, Student, Batch

@admin.register(FeePayment)
class FeePaymentAdmin(admin.ModelAdmin):
    list_display = (
        'record_id_display',
        'student',
        'amount_display',
        'balance_due_display',
        'payment_method_display',
        'transaction_id_display',
        'order_id_display',
        'payment_status_badge',
        'installment_status_badge',
        'payment_date'
    )
    list_filter = ('payment_status', 'status', 'payment_method', 'payment_date')
    search_fields = (
        'student__name',
        'student__student_id',
        'transaction_id',
        'order_id',
        'payment_method'
    )
    readonly_fields = ('order_id', 'transaction_id')

    def record_id_display(self, obj):
        return f"REC-#{obj.id}"
    record_id_display.short_description = "Record ID"

    def amount_display(self, obj):
        return f"₹{obj.amount:,.2f}"
    amount_display.short_description = "Amount"

    def balance_due_display(self, obj):
        return f"₹{obj.balance_due:,.2f}"
    balance_due_display.short_description = "Balance Due"

    def payment_method_display(self, obj):
        return obj.payment_method or "-"
    payment_method_display.short_description = "Payment Method"

    def transaction_id_display(self, obj):
        return obj.transaction_id or "-"
    transaction_id_display.short_description = "Transaction ID"

    def order_id_display(self, obj):
        return obj.order_id or "-"
    order_id_display.short_description = "Razorpay Order ID"

    def payment_status_badge(self, obj):
        st = obj.clean_payment_status
        styles = {
            'Success': 'background:#ecfdf5; color:#059669; border:1px solid #a7f3d0;',
            'Failed': 'background:#fef2f2; color:#dc2626; border:1px solid #fecaca;',
            'Pending': 'background:#fffbeb; color:#d97706; border:1px solid #fde68a;',
            'Created': 'background:#f1f5f9; color:#475569; border:1px solid #cbd5e1;',
            'Refunded': 'background:#faf5ff; color:#7e22ce; border:1px solid #e9d5ff;',
        }
        style = styles.get(st, styles['Pending'])
        dot_colors = {
            'Success': '#10b981',
            'Failed': '#ef4444',
            'Pending': '#f59e0b',
            'Created': '#94a3b8',
            'Refunded': '#a855f7'
        }
        dot = dot_colors.get(st, '#f59e0b')
        return format_html(
            '<span style="display:inline-flex; align-items:center; gap:6px; padding:3px 10px; border-radius:9999px; font-weight:700; font-size:11px; {}">'
            '<span style="display:inline-block; width:6px; height:6px; border-radius:50%; background:{};"></span>{}</span>',
            style, dot, st
        )
    payment_status_badge.short_description = "Payment Status"

    def installment_status_badge(self, obj):
        if obj.status == 'Paid':
            return format_html('<span style="color:#059669; font-weight:700; background:#ecfdf5; padding:2px 8px; border-radius:6px; border:1px solid #a7f3d0;">Paid</span>')
        elif obj.status == 'Pending':
            return format_html('<span style="color:#d97706; font-weight:700; background:#fffbeb; padding:2px 8px; border-radius:6px; border:1px solid #fde68a;">Pending</span>')
        return format_html('<span style="color:#dc2626; font-weight:700; background:#fef2f2; padding:2px 8px; border-radius:6px; border:1px solid #fecaca;">{}</span>', obj.status)
    installment_status_badge.short_description = "Installment Status"


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'name', 'email', 'phone', 'batch', 'status', 'approval_status')
    search_fields = ('student_id', 'name', 'email', 'phone')
    list_filter = ('status', 'approval_status', 'batch')

