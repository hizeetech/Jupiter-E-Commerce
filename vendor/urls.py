# vendor/urls.py
from django.urls import path, include
from . import views
from accounts import views as AccountViews


urlpatterns = [
    path('', AccountViews.vendorDashboard, name='vendor'),
    path('profile/', views.vprofile, name='vprofile'),
    path('store-builder/', views.store_builder, name='store_builder'),
    path('store-builder/category/<int:pk>/', views.productitems_by_category, name='productitems_by_category'),

    # Category CRUD
    path('store-builder/category/add/', views.add_category, name='add_category'),
    path('store-builder/category/edit/<int:pk>/', views.edit_category, name='edit_category'),
    path('store-builder/category/delete/<int:pk>/', views.delete_category, name='delete_category'),

    # ProductItem CRUD
    path('store-builder/product/add/', views.add_product, name='add_product'),
    path('store-builder/product/edit/<int:pk>/', views.edit_product, name='edit_product'),
    path('store-builder/product/delete/<int:pk>/', views.delete_product, name='delete_product'),

    # Opening Hour CRUD
    # path('opening-hours/', views.opening_hours, name='opening_hours'),
    # path('opening-hours/add/', views.add_opening_hours, name='add_opening_hours'),
    # path('opening-hours/remove/<int:pk>/', views.remove_opening_hours, name='remove_opening_hours'),

    # path('order_detail/<int:order_number>/', views.order_detail, name='vendor_order_detail'),
    # path('my_orders/', views.my_orders, name='vendor_my_orders'),


]