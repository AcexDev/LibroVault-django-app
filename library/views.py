from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from .models import Book, BookLink
from django.contrib.auth.forms import UserCreationForm
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView
from .models import User
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.core.paginator import Paginator
import requests, pprint
from .utils import query_input, fetch_results, save_book
from django.contrib.auth.decorators import login_required
from users.models import UserBook
from django import forms
from .forms import BookCreateForm, BookUpdateForm
from django.urls import reverse_lazy
from django import template
from django.contrib import messages
from django.db.models import Count




def about(request):
    return render(request, 'library/about.html')


            #HOMEPAGE BOOKS VIEW

class BookListView(ListView, LoginRequiredMixin):
    model = Book
    template_name = 'library/user_homepage.html'
    context_object_name = 'user_books'
    paginate_by = 10 

    def get_queryset(self):
        return UserBook.objects.filter(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user_books = UserBook.objects.filter(user=self.request.user).order_by('-added_at')
        books = [ub.book for ub in user_books]
        popular_books = Book.objects.exclude(source="Manual").annotate(
                            book_count=Count('userbook')
                        ).order_by('-book_count')[:10]
        context['books'] = books
        context['book_count'] = self.get_queryset().count()
    
        context['favourites_count'] = self.get_queryset().filter(favourite=True).count()
        context['reading_count'] = self.get_queryset().filter(status='reading').count()
        context['popular_books'] = popular_books
        
        return context
      
    
def homepage(request):
    if request.user.is_authenticated:
        return redirect('library-home')
    else:
        return render(request, 'library/generic_homepage.html')

            # BOOK DETAIL FEATURES AND CRUD
class BookDetailView(DetailView):
    # model = Book
    model = Book
    template_name = 'library/book_detail.html'
    context_object_name = 'book'
    
    def get_context_data(self, **kwargs):
        context =  super().get_context_data(**kwargs)
        userbook = UserBook.objects.get(user=self.request.user, book=self.object)
        context['pages_read'] = userbook.pages_read
        
        return context

def update_book_page(request,pk):
    if request.method == "POST":
        updated_count = int(request.POST.get('updated_page_count'))
        book = get_object_or_404(Book, pk=pk)
        page_count = book.page_count
        if updated_count == page_count:
            UserBook.objects.update_or_create(
                user=request.user,
                book=book,
                defaults={
                    "pages_read":updated_count,
                    "status": "completed"
                }
            )
        else:
            UserBook.objects.update_or_create(
                user=request.user,
                book=book,
                defaults={
                    "pages_read":updated_count,
                    "status": "reading"
                }
            )

    messages.success(request, "Reading Progress Updated!")
    return redirect(request.META.get('HTTP_REFERER', '/'))

def favourite_toggle(request,pk):
    book = get_object_or_404(Book, pk=pk)
    user_book = get_object_or_404(UserBook, user=request.user, book=book)

    user_book.favourite = not user_book.favourite
    user_book.save()

    messages.success(request, "Book added to favourites!")
    return redirect(request.META.get('HTTP_REFERER', '/'))
    


#PERSONAL ADDITION BOOK CREATION VIEW
class BookCreateView(CreateView, LoginRequiredMixin):
    model = Book    
    # template_name = 'library/book_.html'
    form_class = BookCreateForm
    context_object_name = 'books'
    
    def form_valid(self, form):
        # form.instance.user = self.request.user
        response =  super().form_valid(form)
        book = self.object

        UserBook.objects.create(
            user = self.request.user,
            book = book,
            status = form.cleaned_data['status']
        )
        return response

    # Required as 'user-books' requires a username
    def get_success_url(self):
        messages.success(self.request, 'Book successfully created!')
        return reverse_lazy('user-books')
        
    
    
# @login_required
# def create_book(request, book)
    
class BookUpdateView(LoginRequiredMixin, UpdateView):
    model = Book
    form_class = BookUpdateForm
    
    #SEPARATING UPDATING VIEW FORMS DEPENDING ON BOOK SOURCE
    def get_form(self, form_class=None):
        book = self.get_object()
        form = super().get_form(form_class)
        if book.source == 'Manual':
            allowed =  ['title', 'author', 'isbn', 'genre', 'description', 'status']
        else:
            allowed =  ['status']

        for field in list(form.fields.keys()):
            if field not in allowed:
                form.fields.pop(field)
                
        return form
    
    template_name = 'library/book_update_form.html'
    context_object_name = 'book'

    def form_valid(self, form):
        form.instance.owner = self.request.user
        response =  super().form_valid(form)

        UserBook.objects.update_or_create(
            user = self.request.user,
            book = self.object,
            defaults={
            'status' : form.cleaned_data['status']
            }            
        )

        messages.success(self.request, 'Book successfully updated!')

        return response
    
    
# To delete User books
class UserBookDeleteView(LoginRequiredMixin, DeleteView):
    model = UserBook
    template_name = 'library/book_confirm_delete.html'
    

    def get_object(self):
        book_id = self.kwargs["pk"]  # this is the Book's ID from the URL
        return get_object_or_404(
            UserBook,
            user=self.request.user,
            book_id=book_id
        )
    
    def get_success_url(self):
        messages.success(self.request, "Book succcessfully deleted!")
        return reverse_lazy(
            'user-books',
            # kwargs={'username':self.request.user.username}
        )        


    #Book Explore and Addition Views
def book_query(request):
    query = request.GET.get("q")
    start_index = int(request.GET.get("startIndex", 0))

    query_params = query_input(query)

    if query_params:
        query_params["startIndex"] = start_index

    if not query:
        books = []
    else:
        books = fetch_results(query, query_params)

    context = {
        "books": books,
        "query": query,
        "start_index": start_index,
        "next_index": start_index + 40,
        "prev_index": max(start_index - 40, 0),
        "original_page": 0
    }

    return render(request, "library/query.html", context)

@login_required
def add_book(request):
    if request.method == "POST":
        book_data = {
            "book_title": request.POST.get('title'),
            "book_author": request.POST.get('author'),
            "book_thumbnail" : request.POST.get('cover'),
            "book_categories": request.POST.get('categories'),
            "book_description": request.POST.get('description'),
            "isbn": request.POST.get('isbn', None),
            "book_google_id": request.POST.get('google_id', None),
            "book_link": request.POST.get('link', None),
            "book_viewability": request.POST.get('viewability'),
            "page_count": int(request.POST.get("page_count") or 0)  #Convert to int and handle null results
        }

    save_book(request.user, book_data)
    messages.success(request, "Book added successfully!")
    return redirect(request.META.get('HTTP_REFERER', '/'))   #To return to Previous Page

#USER BOOK COLLECTION VIEW
def book_view_status_filter(request):
    book_status = request.GET.get('status')
    favourite = request.GET.get('favourite')
    active_user = request.user
    context = None
    book_list = []
    if favourite:
        fave_books = UserBook.objects.filter(
            user=active_user,
            favourite=True
        ).order_by('-added_at')
        
        for item in fave_books:
            book_obj = item.book
            book_obj.favourite = item.favourite
            book_list.append(book_obj)

        context = {
            'books': book_list
        }
    

    else:
        status_choices = UserBook.STATUS_CHOICES
        choices = [choice[0] for choice in status_choices]
        if not book_status:
            user_books = UserBook.objects.filter(
            user=active_user).order_by('-added_at')
            book_status = "All Books"
        else:
            user_books = UserBook.objects.filter(
                user=active_user,
                status=book_status).order_by('-added_at')
        
        for item in user_books:
            book_obj = item.book
            book_obj.favourite = item.favourite
            book_list.append(book_obj)
        

        context = {
            'books': book_list,
            'status': book_status,
            'status_choices' : choices,
        }
    

    # return render(request, 'library/book_filter.html',context)
    return render(request, 'library/user_accountbook_list.html',context)



