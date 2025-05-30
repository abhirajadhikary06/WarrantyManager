from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('upload/', views.upload_bill, name='upload_bill'),
    path('edit/<int:bill_id>/', views.edit_bill, name='edit_bill'),
    path('edit/', views.edit_bill, name='edit_bill'),
    path('delete/<int:bill_id>/', views.delete_bill, name='delete_bill'),
    path('ajax/search/', views.ajax_search, name='ajax_search'),
    path('ajax/extract-image/', views.ajax_extract_image, name='ajax_extract_image'),
    path('logout/', views.logout, name='logout'),
    path('accounts/login/', views.login_view, name='login'),
    path('profile/', views.profile, name='profile'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)