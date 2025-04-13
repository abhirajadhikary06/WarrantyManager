from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('upload/', views.upload_bill, name='upload_bill'),
    path('edit/<int:bill_id>/', views.edit_bill, name='edit_bill'),
    path('edit/', views.edit_bill, name='edit_bill'),
    path('delete/<int:bill_id>/', views.delete_bill, name='delete_bill'),
    path('ajax/search/', views.ajax_search, name='ajax_search'),
    path('ajax/extract-image/', views.ajax_extract_image, name='ajax_extract_image'),
    path('public-warranties/', views.public_warranties, name='public_warranties'),
    path('share/<int:warranty_id>/', views.share_warranty, name='share_warranty'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout, name='logout'),
    path('accounts/login/', views.login_view, name='login'),
]