# marketplace/admin.py
from django.contrib import admin
from .models import Cart

class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'productitem', 'quantity', 'updated_at')



admin.site.register(Cart, CartAdmin)
