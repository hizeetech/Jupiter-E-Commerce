# vendor/views.py
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from accounts.forms import UserProfileForm
from django.db import IntegrityError
from accounts.models import UserProfile
from .models import OpeningHour, Vendor
from .forms import VendorForm, OpeningHourForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from accounts.views import check_role_vendor
from store.models import Category, ProductItem
from store.forms import CategoryForm, ProductItemForm
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
  
from django.utils.text import slugify

@login_required(login_url='login')
@user_passes_test(check_role_vendor)
def add_category(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category_name = form.cleaned_data['category_name']
            category = form.save(commit=False)
            category.vendor = get_vendor(request)
            
            # Generate a unique slug before saving
            base_slug = slugify(category_name)
            unique_slug = base_slug
            counter = 1

            # Check for duplicate slugs
            while Category.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1

            category.slug = unique_slug  # Assign the unique slug before saving
            category.save()

            messages.success(request, 'Category added successfully!')
            return redirect('store_builder')
        else:
            print(form.errors)

    else:
        form = CategoryForm()

    context = {'form': form}
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


@login_required(login_url='login')
@user_passes_test(check_role_vendor)
def add_product(request):
    if request.method == 'POST':
        form = ProductItemForm(request.POST, request.FILES)
        if form.is_valid():
            producttitle = form.cleaned_data['product_title']
            product = form.save(commit=False)
            product.vendor = get_vendor(request)
            product.slug = slugify(producttitle)
            form.save()
            messages.success(request, 'Product Item added successfully!')
            return redirect('productitems_by_category', product.category.id)
        else:
            print(form.errors)
    else:
        form = ProductItemForm()
        # modify this form
        form.fields['category'].queryset = Category.objects.filter(vendor=get_vendor(request))
    context = {
        'form': form,
    }
    return render(request, 'vendor/add_product.html', context)
  
  
@login_required(login_url='login')
@user_passes_test(check_role_vendor)
def edit_product(request, pk=None):
    product = get_object_or_404(ProductItem, pk=pk)
    if request.method == 'POST':
        form = ProductItemForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            producttitle = form.cleaned_data['product_title']
            product = form.save(commit=False)
            product.vendor = get_vendor(request)
            product.slug = slugify(producttitle)
            form.save()
            messages.success(request, 'Product Item updated successfully!')
            return redirect('productitems_by_category', product.category.id)
        else:
            print(form.errors)

    else:
        form = ProductItemForm(instance=product)
        form.fields['category'].queryset = Category.objects.filter(vendor=get_vendor(request))
    context = {
        'form': form,
        'product': product,
    }
    return render(request, 'vendor/edit_product.html', context)


@login_required(login_url='login')
@user_passes_test(check_role_vendor)
def delete_product(request, pk=None):
    product = get_object_or_404(ProductItem, pk=pk)
    product.delete()
    messages.success(request, 'Product Item has been deleted successfully!')
    return redirect('productitems_by_category', product.category.id)
  
  
def opening_hours(request):
    opening_hours = OpeningHour.objects.filter(vendor=get_vendor(request))
    form = OpeningHourForm()
    context = {
        'form': form,
        'opening_hours': opening_hours,
    }
    return render(request, 'vendor/opening_hours.html', context)
  
  
def add_opening_hours(request):
    # handle the data and save them inside the database
    if request.user.is_authenticated:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' and request.method == 'POST':
            day = request.POST.get('day')
            from_hour = request.POST.get('from_hour')
            to_hour = request.POST.get('to_hour')
            is_closed = request.POST.get('is_closed')
            
            try:
                hour = OpeningHour.objects.create(vendor=get_vendor(request), day=day, from_hour=from_hour, to_hour=to_hour, is_closed=is_closed)
                if hour:
                    day = OpeningHour.objects.get(id=hour.id)
                    if day.is_closed:
                        response = {'status': 'success', 'id': hour.id, 'day': day.get_day_display(), 'is_closed': 'Closed'}
                    else:
                        response = {'status': 'success', 'id': hour.id, 'day': day.get_day_display(), 'from_hour': hour.from_hour, 'to_hour': hour.to_hour}
                return JsonResponse(response)
            except IntegrityError as e:
                response = {'status': 'failed', 'message': from_hour+'-'+to_hour+' already exists for this day!'}
                return JsonResponse(response)
        else:
            HttpResponse('Invalid request')
            
            
def remove_opening_hours(request, pk=None):
    if request.user.is_authenticated:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            hour = get_object_or_404(OpeningHour, pk=pk)
            hour.delete()
            return JsonResponse({'status': 'success', 'id': pk})