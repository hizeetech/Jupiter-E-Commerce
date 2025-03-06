# orders/admin.py
from django.contrib import admin
from .models import Payment, Order, OrderedProduct

class OrderedProductInline(admin.TabularInline):
    model = OrderedProduct
    readonly_fields = ('order', 'payment', 'user', 'productitem', 'quantity', 'price', 'amount')
    extra = 0


class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'name', 'phone', 'email', 'total', 'payment_method', 'status', 'order_placed_to', 'is_ordered']
    inlines = [OrderedProductInline]
    
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'transaction_id', 'payment_method', 'amount', 'status', 'created_at')
    list_filter = ('payment_method', 'status')
    search_fields = ('transaction_id', 'user__username')


admin.site.register(Payment, PaymentAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderedProduct)
