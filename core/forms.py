from django import forms
from .models import Bill, WarrantyCard

class BillUploadForm(forms.ModelForm):
    class Meta:
        model = Bill
        fields = ['bill_image', 'shop_name', 'contact_number', 'bill_date', 'total_amount', 'items']
        widgets = {
            'bill_date': forms.DateInput(attrs={'type': 'date'}),
            'items': forms.Textarea(attrs={'rows': 3}),
        }

    warranty_image = forms.ImageField(required=False)
    warranty_period_years = forms.IntegerField(required=False, min_value=0)

class BillEditForm(forms.ModelForm):
    class Meta:
        model = Bill
        fields = ['bill_image', 'shop_name', 'contact_number', 'bill_date', 'total_amount', 'items']
        widgets = {
            'bill_date': forms.DateInput(attrs={'type': 'date'}),
            'items': forms.Textarea(attrs={'rows': 3}),
        }

class WarrantyEditForm(forms.ModelForm):
    class Meta:
        model = WarrantyCard
        fields = ['warranty_image', 'warranty_period_years']