from django.contrib import admin
from django.urls import path, include
from . import views
from .views import (BookListView, BookCreateView, 
                    BookDetailView, BookUpdateView, 
                    UserBookDeleteView, book_query,
                    add_book, book_view_status_filter,
                    update_book_page, favourite_toggle,
                    )
urlpatterns = [
    path('', views.homepage, name='home-page'),
    path('home/', BookListView.as_view(), name='library-home'),
    path('user/', book_view_status_filter, name='user-books'),
    path('book/new/', BookCreateView.as_view(), name='book-create'),
    path('book/<int:pk>/', BookDetailView.as_view(), name='book-detail'),
    path('book/<int:pk>/update/', BookUpdateView.as_view(), name='book-update'),
    path('book/<int:pk>/delete/', UserBookDeleteView.as_view(), name='book-delete'),
    path('book/explore/', book_query, name='book-explore'),
    path('book/add/', add_book, name='add_book'),
    path('user/bookfilter', book_view_status_filter, name='filter-book'),
    path('book/pageupdate/<int:pk>/', update_book_page, name='book-page-update'), 
    path('book/favourite/<int:pk>/', favourite_toggle, name='favourite-toggle')
]