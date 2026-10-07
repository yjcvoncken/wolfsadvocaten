"""Expose Dutch text fields beside the existing English fields in admin."""
from copy import deepcopy
from django import forms
from .localization import CONTENT_FIELDS


def translation_form(model):
    content_fields = CONTENT_FIELDS[model._meta.concrete_model._meta.model_name]
    declared = {}
    for name in content_fields:
        field = model._meta.get_field(name)
        declared[f'{name}_nl'] = forms.CharField(
            label=f'{field.verbose_name.capitalize()} (Dutch)', required=False,
            max_length=field.max_length,
            widget=forms.Textarea(attrs={'rows': 5}) if field.get_internal_type() == 'TextField' else forms.TextInput,
            help_text='Dutch translation. If left blank, the original text is used.')

    class BilingualForm(forms.ModelForm):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            for name in content_fields:
                if name in self.fields:
                    self.fields[name].label = f'{model._meta.get_field(name).verbose_name.capitalize()} (English)'
                if f'{name}_nl' in self.fields:
                    self.fields[f'{name}_nl'].initial = self.instance.translations.get('nl', {}).get(name, '')

        def save(self, commit=True):
            instance = super().save(commit=False)
            translations = deepcopy(instance.translations or {})
            dutch = translations.setdefault('nl', {})
            for name in content_fields:
                field_name = f'{name}_nl'
                # List editing and partial forms must preserve translations they do not display.
                if self.add_prefix(field_name) in self.data and field_name in self.cleaned_data:
                    dutch[name] = self.cleaned_data[field_name]
            instance.translations = translations
            if commit:
                instance.save()
                self.save_m2m()
            return instance

        class Meta:
            fields = '__all__'
            exclude = ('translations',)

    return type(f'{model.__name__}BilingualForm', (BilingualForm,), declared)


def expand_fields(fields, model):
    content_fields = CONTENT_FIELDS[model._meta.concrete_model._meta.model_name]
    expanded = []
    for field in fields:
        if isinstance(field, (list, tuple)):
            expanded.append(tuple(expand_fields(field, model)))
        else:
            expanded.append(field)
            if field in content_fields:
                expanded.append(f'{field}_nl')
    return tuple(expanded)
