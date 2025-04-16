from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta

class Bill(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    bill_image = models.ImageField(upload_to='bills/', null=False, blank=False)
    shop_name = models.CharField(max_length=255)
    contact_number = models.CharField(max_length=20, blank=True)
    bill_date = models.DateField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    items = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Bill from {self.shop_name} on {self.bill_date}"

class WarrantyCard(models.Model):
    bill = models.OneToOneField(Bill, on_delete=models.CASCADE)
    warranty_image = models.ImageField(upload_to='warranties/', blank=True, null=True)
    warranty_period_years = models.IntegerField(default=0)
    warranty_end_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.warranty_period_years and self.bill.bill_date:
            self.warranty_end_date = self.bill.bill_date + timedelta(days=self.warranty_period_years * 365)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Warranty for bill {self.bill.id}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    warranty_card = models.ForeignKey(WarrantyCard, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message}"

class SharedWarranty(models.Model):
    warranty_card = models.ForeignKey(WarrantyCard, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    shared_text = models.TextField()
    shared_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Shared by {self.user.username} at {self.shared_at}"