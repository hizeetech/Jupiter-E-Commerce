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


admin.site.register(Payment)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderedProduct)
