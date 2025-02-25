# vendor/views.py
from django.shortcuts import get_object_or_404, redirect, render

from accounts.forms import UserProfileForm
from accounts.models import UserProfile
from .models import Vendor
from .forms import VendorForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from accounts.views import check_role_vendor
from store.models import Category, ProductItem
from store.forms import CategoryForm
from django.template.defaultfilters import slugify


def get_vendor(request):
    vendor = Vendor.objects.get(user=request.user)
    return vendor


@login_required(login_url='login')
@user_passes_test(check_role_vendor)
def vprofile(request):
  profile = get_object_or_404(UserProfile, user=request.user)
  vendor = get_object_or_404(Vendor, user=request.user)
  
  if request.method == 'POST':
    profile_form = UserProfileForm(request.POST, request.FILES, instance=profile)
    vendor_form = VendorForm(request.POST, request.FILES, instance=vendor)
    
    if profile_form.is_valid() and vendor_form.is_valid():
      profile_form.save()
      vendor_form.save()
      messages.success(request, 'Settings updated')
      
      return redirect('vprofile')
    else:
      print(profile_form.errors)
      print(vendor_form.errors)
  else:  
    profile_form = UserProfileForm(instance=profile)
    vendor_form = VendorForm(instance=vendor)
  
  context = {
    'profile_form': profile_form,
    'vendor_form': vendor_form,
    'profile': profile,
    'vendor': vendor,
  }
  return render(request, 'vendor/vprofile.html', context)


@login_required(login_url='login')
@user_passes_test(check_role_vendor)
def store_builder(request):
  vendor = get_vendor(request)
  categories = Category.objects.filter(vendor=vendor).order_by('created_at')
  context = {
      'categories': categories,
  }
  return render(request, 'vendor/store_builder.html', context)


@login_required(login_url='login')
@user_passes_test(check_role_vendor)
def productitems_by_category(request, pk=None):
    vendor = get_vendor(request)
    category = get_object_or_404(Category, pk=pk)
    productitems = ProductItem.objects.filter(vendor=vendor, category=category)
    context = {
      'productitems': productitems,
      'category': category,
    }
    return render(request, 'vendor/productitems_by_category.html', context)
  
@login_required(login_url='login')
@user_passes_test(check_role_vendor)  
def add_category(request):
  if request.method == 'POST':
    form = CategoryForm(request.POST)
    if form.is_valid():
      category_name = form.cleaned_data['category_name']
      category_slug = slugify(category_name)
      
      # Check if category already exits
      if Category.objects.filter(slug=category_slug).exists():
        messages.error(request, 'Category with this Category name already exists!')
        return redirect(store_builder) # Prevents duplicate entry
      
      category = form.save(commit=False)
      category.vendor = get_vendor(request)
      category.slug = category_slug
      category.save()
      
      # Update product items with new category
      messages.success(request, 'Category saved Successfully')
      return redirect(store_builder)
    else:
      print(form.errors)
  else:
    form = CategoryForm()
  context = {
    'form': form,
  }
  return render(request, 'vendor/add_category.html', context)


@login_required(login_url='login')
@user_passes_test(check_role_vendor)
def edit_category(request, pk=None):
  category = get_object_or_404(Category, pk=pk)
  if request.method == 'POST':
    form = CategoryForm(request.POST, instance=category)
    if form.is_valid():
      category_name = form.cleaned_data['category_name']
      category_slug = slugify(category_name)
      
      # Check if category already exits
      if Category.objects.filter(slug=category_slug).exists():
        messages.error(request, 'Category with this Category name already exists!')
        return redirect(store_builder) # Prevents duplicate entry
      
      category = form.save(commit=False)
      category.vendor = get_vendor(request)
      category.slug = category_slug
      category.save()
      
      # Update product items with new category
      messages.success(request, 'Category Updated Successfully')
      return redirect(store_builder)
    else:
      print(form.errors)
  else:
    form = CategoryForm(instance=category)
  context = {
    'form': form,
    'category': category,
  }    
  return render(request, 'vendor/edit_category.html', context)


@login_required(login_url='login')
@user_passes_test(check_role_vendor)
def delete_category(request, pk=None):
  category = get_object_or_404(Category, pk=pk)
  category.delete()
  messages.success(request, 'Category has been deleted successfully!')
  return redirect('store_builder')