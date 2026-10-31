import re
from django import forms
from .models import Product


class OrderRequestForm(forms.Form):
    product = forms.ModelChoiceField(queryset=Product.objects.filter(is_published=True), required=False)
    customer_name = forms.CharField(max_length=100)
    phone = forms.CharField(max_length=40)
    comment = forms.CharField(max_length=3000, required=False)
    submission_id = forms.UUIDField()

    def clean_phone(self):
        phone = self.cleaned_data["phone"]
        if not re.fullmatch(r"[+0-9()\s-]+", phone) or not 7 <= len(re.sub(r"\D", "", phone)) <= 15:
            raise forms.ValidationError("Введите номер телефона: от 7 до 15 цифр.")
        return phone
