from users.models import UserBook
from django import forms
from .models import Book

class BookCreateForm(forms.ModelForm):
    status = forms.ChoiceField(choices=UserBook.STATUS_CHOICES)
    class Meta:
        model = Book
        fields = ['title', 'author', 'isbn', 'genre','published_year', 'source', 'description', 'status', 'page_count']


class BookUpdateForm(forms.ModelForm):
    status = forms.ChoiceField(choices=UserBook.STATUS_CHOICES,
                               required=False)
    class Meta:
        model = Book
        fields = ['title', 'author', 'isbn', 'genre', 'description', 'status']
        


