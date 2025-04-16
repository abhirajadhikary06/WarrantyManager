from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib import messages
from .models import Bill, WarrantyCard, Notification, SharedWarranty
from .forms import BillUploadForm, BillEditForm, WarrantyEditForm
from .utils import extract_complete_data
from django.db.models import Q
from django.http import JsonResponse
import os
import tempfile
from datetime import datetime, timedelta
from django.utils import timezone
import logging

# Set up logging
logger = logging.getLogger(__name__)

@login_required
def dashboard(request):
    bills = Bill.objects.filter(user=request.user).order_by('-created_at')
    current_date = timezone.now().date()
    seven_days_later = current_date + timezone.timedelta(days=7)

    notifications = Notification.objects.filter(
        user=request.user,
        warranty_card__warranty_end_date__range=(current_date, seven_days_later)
    ).select_related('warranty_card__bill')

    context = {
        'bills': bills,
        'notifications': notifications,
    }
    return render(request, 'core/dashboard.html', context)

@login_required
def ajax_search(request):
    query = request.GET.get('q', '')
    bills = Bill.objects.filter(user=request.user)
    
    if query:
        bills = bills.filter(
            Q(shop_name__icontains=query) |
            Q(items__icontains=query) |
            Q(bill_date__icontains=query)
        )
    
    bills_data = [
        {
            'id': bill.id,
            'shop_name': bill.shop_name,
            'bill_date': bill.bill_date.strftime('%Y-%m-%d'),
            'total_amount': float(bill.total_amount),
            'items': bill.items,
            'contact_number': bill.contact_number,  # Added for search if needed
            'warranty_period_years': bill.warrantycard.warranty_period_years if hasattr(bill, 'warrantycard') else 0,
            'warranty_end_date': bill.warrantycard.warranty_end_date.strftime('%Y-%m-d') if hasattr(bill, 'warrantycard') and bill.warrantycard.warranty_end_date else '',
            'has_warranty': hasattr(bill, 'warrantycard')
        }
        for bill in bills
    ]
    
    return JsonResponse({'bills': bills_data})

@login_required
def ajax_extract_image(request):
    if request.method != 'POST' or not request.FILES.get('bill_image'):
        return JsonResponse({'error': 'No bill image provided'}, status=400)
    
    bill_image = request.FILES['bill_image']
    warranty_image = request.FILES.get('warranty_image', None)
    
    if not bill_image.name.lower().endswith(('.jpg', '.jpeg', '.png')):
        return JsonResponse({'error': 'Bill image must be JPG or PNG'}, status=400)
    if warranty_image and not warranty_image.name.lower().endswith(('.jpg', '.jpeg', '.png')):
        return JsonResponse({'error': 'Warranty image must be JPG or PNG'}, status=400)
    
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_bill:
            for chunk in bill_image.chunks():
                temp_bill.write(chunk)
            temp_bill_path = temp_bill.name
        
        temp_warranty_path = None
        if warranty_image:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_warranty:
                for chunk in warranty_image.chunks():
                    temp_warranty.write(chunk)
                temp_warranty_path = temp_warranty.name
        
        try:
            result = extract_complete_data(temp_bill_path, temp_warranty_path)
            return JsonResponse({
                'structured_data': result['structured_data'],
                'error': result['error']
            })
        finally:
            os.unlink(temp_bill_path)
            if temp_warranty_path:
                os.unlink(temp_warranty_path)
    except Exception as e:
        return JsonResponse({'error': f'File processing failed: {str(e)}'}, status=500)

@login_required
def upload_bill(request):
    if request.method == 'POST':
        form = BillUploadForm(request.POST, request.FILES)
        if form.is_valid():
            bill = Bill(
                user=request.user,
                bill_image=request.FILES['bill_image'],
                shop_name=form.cleaned_data['shop_name'],
                contact_number=form.cleaned_data['contact_number'],
                bill_date=form.cleaned_data['bill_date'],
                total_amount=form.cleaned_data['total_amount'],
                items=form.cleaned_data['items']
            )
            bill.save()

            warranty_period_years = form.cleaned_data.get('warranty_period_years', 0)
            if request.FILES.get('warranty_image') or warranty_period_years:
                warranty = WarrantyCard(
                    bill=bill,
                    warranty_image=request.FILES.get('warranty_image'),
                    warranty_period_years=warranty_period_years
                )
                warranty.save()

                if warranty.warranty_end_date and warranty.warranty_end_date <= datetime.now().date():
                    Notification.objects.create(
                        user=request.user,
                        warranty_card=warranty,
                        message=f"Warranty for {bill.shop_name} has expired."
                    )

            messages.success(request, 'Bill uploaded successfully!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please correct the form errors.')
    else:
        form = BillUploadForm()

    return render(request, 'core/upload.html', {'form': form})

@login_required
def edit_bill(request, bill_id):
    bill = get_object_or_404(Bill, id=bill_id, user=request.user)
    if request.method == 'POST':
        form = BillUploadForm(request.POST, request.FILES)
        if form.is_valid():
            bill.bill_image = request.FILES.get('bill_image', bill.bill_image)
            bill.shop_name = form.cleaned_data['shop_name']
            bill.contact_number = form.cleaned_data['contact_number']
            bill.bill_date = form.cleaned_data['bill_date']
            bill.total_amount = form.cleaned_data['total_amount']
            bill.items = form.cleaned_data['items']
            bill.save()

            warranty = bill.warrantycard
            if warranty:
                warranty.warranty_image = request.FILES.get('warranty_image', warranty.warranty_image)
                warranty.warranty_period_years = form.cleaned_data.get('warranty_period_years', 0)
                warranty.save()
            elif form.cleaned_data.get('warranty_period_years') or request.FILES.get('warranty_image'):
                warranty = WarrantyCard(
                    bill=bill,
                    warranty_image=request.FILES.get('warranty_image'),
                    warranty_period_years=form.cleaned_data.get('warranty_period_years', 0)
                )
                warranty.save()

            messages.success(request, 'Bill updated successfully!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please correct the form errors.')
    else:
        form = BillUploadForm()  # Empty form for GET
    return render(request, 'core/edit.html', {'bill': bill})

@login_required
def delete_bill(request, bill_id):
    bill = get_object_or_404(Bill, id=bill_id, user=request.user)
    if request.method == 'POST':
        try:
            bill.delete()
            logger.info(f"Bill {bill_id} deleted successfully for user {request.user.username}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                messages.success(request, 'Bill deleted successfully!')
                return JsonResponse({'status': 'success', 'message': 'Bill deleted successfully!'})
            messages.success(request, 'Bill deleted successfully!')
            return redirect('dashboard')
        except Exception as e:
            logger.error(f"Error deleting bill {bill_id}: {str(e)}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': f'Failed to delete bill: {str(e)}'}, status=500)
            messages.error(request, f'Failed to delete bill: {str(e)}')
            return redirect('dashboard')
    return redirect('dashboard')  # Handle GET requests safely

def public_warranties(request):
    shared_warranties = SharedWarranty.objects.all().order_by('-shared_at')
    return render(request, 'core/public_warranties.html', {'shared_warranties': shared_warranties})

@login_required
def share_warranty(request, warranty_id):
    warranty = get_object_or_404(WarrantyCard, id=warranty_id, bill__user=request.user)
    if request.method == 'POST':
        shared_text = (
            f"Warranty from {warranty.bill.shop_name}, "
            f"valid until {warranty.warranty_end_date}. "
            f"Contact: {warranty.bill.contact_number or 'N/A'}."
        )
        SharedWarranty.objects.create(
            warranty_card=warranty,
            user=request.user,
            shared_text=shared_text
        )
        messages.success(request, 'Warranty shared successfully!')
        return redirect('dashboard')
    return render(request, 'core/share_confirm.html', {'warranty': warranty})

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'core/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            messages.success(request, 'Logged in successfully!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    return render(request, 'core/login.html', {'form': form})

@login_required
def logout(request):
    auth_logout(request)
    messages.success(request, 'Logged out successfully!')
    return redirect('login')