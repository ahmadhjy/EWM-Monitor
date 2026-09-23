from django import forms

from .i18n import is_arabic, ui_text
from .models import ContactMessage, MediaAsset, NewsletterSubscriber


class MediaAssetUploadForm(forms.ModelForm):
    class Meta:
        model = MediaAsset
        fields = ("title", "file", "alt_text", "caption", "credit")

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("file"):
            self.add_error("file", "Choose an image to upload.")
        return cleaned_data


class ContactForm(forms.ModelForm):
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = ContactMessage
        fields = ("name", "email", "subject", "message")
        widgets = {
            "name": forms.TextInput(attrs={"autocomplete": "name", "placeholder": "Your name"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "you@example.com"}),
            "subject": forms.TextInput(attrs={"placeholder": "How can we help?"}),
            "message": forms.Textarea(attrs={"rows": 7, "placeholder": "Write your message"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if is_arabic():
            labels = {"name": "Name", "email": "Email", "subject": "Subject", "message": "Message"}
            placeholders = {
                "name": "Your name",
                "email": "you@example.com",
                "subject": "How can we help?",
                "message": "Write your message",
            }
            for field_name, label in labels.items():
                self.fields[field_name].label = ui_text(label)
                self.fields[field_name].widget.attrs["placeholder"] = ui_text(placeholders[field_name])
                self.fields[field_name].widget.attrs["dir"] = "ltr" if field_name == "email" else "rtl"

    def clean_website(self):
        value = self.cleaned_data.get("website")
        if value:
            raise forms.ValidationError("Spam detected.")
        return value


class NewsletterForm(forms.Form):
    email = forms.EmailField(max_length=254)
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Spam detected.")
        return ""
