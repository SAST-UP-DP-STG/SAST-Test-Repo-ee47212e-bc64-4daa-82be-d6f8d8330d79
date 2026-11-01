from django import forms

from .models import Clinic


class ClinicEditForm(forms.ModelForm):
    class Meta:
        model = Clinic
        fields = "__all__"
