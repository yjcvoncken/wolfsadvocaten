from django import forms
from .models import ContactSubmission
from .localization import translate

class ContactForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.label = translate(field.label)

    class Meta:
        model = ContactSubmission
        fields = ('first_name','last_name','email','phone','message')
        widgets = {'message': forms.Textarea(attrs={'rows': 5})}
