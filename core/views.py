from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib import messages
from .models import Bill, WarrantyCard, Notification, SharedWarranty, UserBadge
from .forms import BillUploadForm, BillEditForm
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
    # Force fresh data by not using any caching
    bills = Bill.objects.filter(user=request.user).order_by('-created_at').select_related('warrantycard')
    current_date = timezone.now().date()
    thirty_days_later = current_date + timezone.timedelta(days=30)

    notifications = Notification.objects.filter(
        user=request.user,
        warranty_card__warranty_end_date__lte=thirty_days_later
    ).select_related('warranty_card__bill')
    has_unread = notifications.filter(is_read=False).exists()

    context = {
        'bills': bills,
        'notifications': notifications,
        'has_unread': has_unread,
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

            # Update lifetime upload count in the base UserBadge
            user_badge, created = UserBadge.objects.get_or_create(user=request.user, defaults={'badge_name': None})
            user_badge.lifetime_upload_count += 1
            user_badge.save()

            messages.success(request, 'Bill uploaded successfully!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please correct the form errors.')
    else:
        form = BillUploadForm()

    return render(request, 'core/upload.html', {'form': form})

@login_required
def profile(request):
    user = request.user
    upload_count = Bill.objects.filter(user=user).count()
    
    # Get or create user badge record to access lifetime count
    user_badge, created = UserBadge.objects.get_or_create(user=request.user, defaults={'badge_name': None})
    lifetime_upload_count = user_badge.lifetime_upload_count
    
    # Get existing badges (split if stored as comma-separated string)
    existing_badges = set(user_badge.badge_name.split(',') if user_badge.badge_name else [])
    
    # Define badge thresholds and names
    badge_thresholds = [
        (1, "Receipt Rookie"),
        (10, "Ledger Learner"),
        (20, "Warranty Watcher"),
        (30, "Bill Guardian"),
        (40, "Archive Ace"),
        (50, "Financial Fortress"),
        (60, "Record Keeper"),
        (70, "Warranty Wizard"),
        (80, "Bill Bastion"),
        (90, "Ledger Legend"),
        (100, "Financial Titan"),
    ]
    
    # Award new badges based on lifetime count
    badges_to_add = []
    for threshold, badge_name in badge_thresholds:
        if lifetime_upload_count >= threshold and badge_name not in existing_badges:
            badges_to_add.append(badge_name)
    
    # Update existing badge_name with new badges
    if badges_to_add:
        new_badges = existing_badges.union(set(badges_to_add))
        user_badge.badge_name = ','.join(new_badges) if new_badges else None
        user_badge.save()
    
    # Combine existing and new badges
    all_badges = list(existing_badges.union(set(badges_to_add)))

    context = {
        'user': user,
        'upload_count': upload_count,
        'badges': all_badges,
        'join_date': user.date_joined.date(),
    }
    return render(request, 'core/profile.html', context)

logger = logging.getLogger(__name__)

@login_required
def edit_bill(request, bill_id):
    bill = get_object_or_404(Bill, id=bill_id, user=request.user)
    if request.method == 'POST':
        form = BillEditForm(request.POST, request.FILES, instance=bill)
        if form.is_valid():
            try:
                # Save bill data (bill_image is optional)
                bill = form.save()

                # Update or create warranty data (warranty_image is optional)
                warranty_period_years = form.cleaned_data.get('warranty_period_years', 0)
                warranty_image = request.FILES.get('warranty_image')

                if hasattr(bill, 'warrantycard'):
                    warranty = bill.warrantycard
                    if warranty_image:
                        warranty.warranty_image = warranty_image
                    warranty.warranty_period_years = warranty_period_years
                    warranty.save()
                elif warranty_period_years or warranty_image:
                    warranty = WarrantyCard(
                        bill=bill,
                        warranty_image=warranty_image,
                        warranty_period_years=warranty_period_years
                    )
                    warranty.save()

                messages.success(request, 'Bill updated successfully!')
                return redirect('dashboard')
            except Exception as e:
                logger.error(f"Error updating bill {bill_id}: {str(e)}")
                messages.error(request, f'Failed to update bill: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        # Initialize form with existing bill data
        initial_data = {
            'shop_name': bill.shop_name,
            'contact_number': bill.contact_number,
            'bill_date': bill.bill_date,
            'total_amount': bill.total_amount,
            'items': bill.items,
        }
        if hasattr(bill, 'warrantycard'):
            initial_data['warranty_period_years'] = bill.warrantycard.warranty_period_years
        form = BillEditForm(initial=initial_data, instance=bill)
    return render(request, 'core/edit.html', {'bill': bill, 'form': form})

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


def login_view(request):
    login_form = AuthenticationForm()
    register_form = UserCreationForm()

    if request.method == 'POST':
        if 'login' in request.POST:
            login_form = AuthenticationForm(request, data=request.POST)
            if login_form.is_valid():
                user = login_form.get_user()
                auth_login(request, user)
                messages.success(request, 'Logged in successfully!')
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': True})
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'message': 'Invalid username or password'})
        elif 'register' in request.POST:
            register_form = UserCreationForm(request.POST)
            if register_form.is_valid():
                user = register_form.save()
                auth_login(request, user)
                messages.success(request, 'Registration successful!')
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': True})
                return redirect('dashboard')
            else:
                messages.error(request, 'Please correct the form errors.')
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'message': 'Please correct the form errors'})

    context = {
        'login_form': login_form,
        'register_form': register_form,
    }
    return render(request, 'core/login.html', context)

@login_required
def logout(request):
    auth_logout(request)
    messages.success(request, 'Logged out successfully!')
    return redirect('login')