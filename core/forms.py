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
    warranty_period_years = forms.IntegerField(required=False, min_value=0, initial=0, label="Warranty Period (Years)")

    class Meta:
        model = Bill
        fields = ['bill_image', 'shop_name', 'contact_number', 'bill_date', 'total_amount', 'items']
        widgets = {
            'bill_date': forms.DateInput(attrs={'type': 'date'}),
            'items': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make bill_image optional in the form
        self.fields['bill_image'].required = False
        # Ensure existing image is preserved if not updated
        if self.instance.pk and not self.data.get('bill_image'):
            self.fields['bill_image'].initial = self.instance.bill_image

class WarrantyEditForm(forms.ModelForm):
    class Meta:
        model = WarrantyCard
        fields = ['warranty_image', 'warranty_period_years']