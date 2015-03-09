from datetime import datetime

from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from rango.models import Category, Page, UserProfile, User
from rango.forms import CategoryForm, PageForm, UserProfileForm

from rango.bing_search import run_query

def index(request):

    category_list = Category.objects.order_by('-likes')[:5]
    page_list = Page.objects.order_by('views')[:5]
    
    context_dict = {'categories': category_list, 'pages': page_list}

    visits = request.session.get('visits')
    if not visits:
        visits = 1
    reset_last_visit_time = False

    last_visit = request.session.get('last_visit')
    if last_visit:
        last_visit_time = datetime.strptime(last_visit[:-7], "%Y-%m-%d %H:%M:%S")

        if (datetime.now() - last_visit_time).seconds > 0:
            # ...reassign the value of the cookie to +1 of what it was before...
            visits = visits + 1
            # ...and update the last visit cookie, too.
            reset_last_visit_time = True
    else:
        # Cookie last_visit doesn't exist, so create it to the current date/time.
        reset_last_visit_time = True

    if reset_last_visit_time:
        request.session['last_visit'] = str(datetime.now())
        request.session['visits'] = visits
    context_dict['visits'] = visits

    response = render(request, 'rango/index.html', context_dict)

    return response

def about(request):
    # If the visits sessions variable exists, take it and use it.
    # It it doesn't, we haven't visited the site so set the count to zero.
    if request.session.get('visits'):
        count = request.session.get('visits')
    else:
        count = 0

    return render(request, 'rango/about.html', {'visits': count})

def category(request, category_name_slug):
    # Create a context dictionary which we can pass to the template rendering engine.
    context_dict = {}
    context_dict['result_list'] = None
    context_dict['query'] = None

    if request.method == 'POST':
        query = request.POST.get('query', '').strip()

        # Run our Bing function to get the results list!
        result_list = run_query(query)

        context_dict['result_list'] = result_list
        context_dict['query'] = query

    try:
        # Can we find a category name slug with the given name?
        # If we can't, the .get() method raises a DoesNotExist exception.
        # So the .get() method returns one model instance or raises an exception.
        category = Category.objects.get(slug=category_name_slug)
        context_dict['category_name'] = category.name

        # Retreive all of the associated pages.
        # Note that filter returns >= 1 model instance.
        pages = Page.objects.filter(category=category).order_by('-views')

        # Adss our results list to the template context under name pages.
        context_dict['pages'] = pages
        # We also add the category object from the database to the context dictionary.
        # We'll use this in the template to verify that the category exists.
        context_dict['category'] = category
        context_dict['category_name_slug'] = category.slug
    
        if not context_dict['query']:
            context_dict['query'] = category.name

    except Category.DoesNotExist:
        # We get here if we didn't finf the specified category.
        # Don't do anything - the template displays the "no category" message for us.
        pass

    # Go render the response and return it to the client.
    return render(request, 'rango/category.html', context_dict)

def track_url(request):
    page_id = None
    url = '/rango/'

    if request.method == 'GET':
        if 'page_id' in request.GET:
            page_id = request.GET['page_id']
            try:
                page = Page.objects.get(id=page_id)
                page.views = page.views + 1
                page.save()
                url = page.url
            except:
                pass

    return redirect(url)

@login_required
def register_profile(request):
    # Check if user has a profile
    try:
        profile = UserProfile.objects.get(user=request.user)
        return redirect('profile')
    except UserProfile.DoesNotExist:
        pass

    # If it's a HTTP POST, we're interested in processing form data.
    if request.method == 'POST':
        # Attempt to grab information from the raw form information.
        # Note that we make use of UserProfileForm.
        form = UserProfileForm(data=request.POST)

        # If the form is valid...
        if form.is_valid():
            # Now sort out the UserProfile instance.
            # Since we need to set the user attribute ourselves, we set commit=False.
            # This delays saving the model until we're ready to avoid integrity problems.
            profile = form.save(commit=False)
            profile.user = request.user
            
            # Did the user provide a profile picture?
            # If so, we need to get it from the input form and put it in the UserProfile model.
            if 'picture' in request.FILES:
                profile.picture = request.FILES['picture']

            # Now we save the UserProfile model instance.
            profile.save()

            return redirect('profile')

        # Invalid form - mistakes or something else?
        # Print problems to the terminal.
        # They'll also be shown to the user.
        else:
            print form.errors
    
    # Not a HTTP POST, so we render our form using the ModelForm instance.
    # This form will be blank, ready for user input.
    else:
        form = UserProfileForm()

    # Render the template depending on the context.
    return render(request, 'registration/profile_registration.html', {'form': form})

@login_required
def profile(request):
    # Check if user has a profile
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        return redirect('add_profile')

    context_dict = {}

    # If it's a HTTP POST, we're interested in processing form data.
    if request.method == 'POST':
        # Attempt to grab information from the raw form information.
        # Note that we make use of UserProfileForm.
        form = UserProfileForm(data=request.POST)

        # If the form is valid...
        if form.is_valid():
            # Now sort out the UserProfile instance.
            # Since we need to set the user attribute ourselves, we set commit=False.
            # This delays saving the model until we're ready to avoid integrity problems.
            profile_new = form.save(commit=False)
            profile_new.user = request.user

            # Did the user provide a profile picture?
            # If so, we need to get it from the input form and put it in the UserProfile model.
            if 'picture' in request.FILES:
                profile_new.picture = request.FILES['picture']
            elif profile.picture:
                profile_new.picture = profile.picture

            # Now we save the UserProfile model instance.
            try:
                profile_new.save()
            except IntegrityError:
                profile.delete()
                profile_new.save()

        # Invalid form - mistakes or something else?
        # Print problems to the terminal.
        # They'll also be shown to the user.
        else:
            print form.errors

        return redirect('profile')

    # Not a HTTP POST, so we render our form using the ModelForm instance.
    # This form will be blank, ready for user input.
    else:
        form = UserProfileForm()

    context_dict['form'] = form
    context_dict['website'] = profile.website
    context_dict['picture'] = profile.picture

    # Render the template depending on the context.
    return render(request, 'rango/profile.html', context_dict)

@login_required
def users(request):
    # List all users
    users = User.objects.all()
    return render(request, 'rango/users.html', {'users': users})

@login_required
def otherprofile(request, username):
    # Check if it's the logged in user
    if username == request.user.username:
        return redirect('profile')

    # Check if user exists
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return redirect('index')

    # Check if user has a profile
    profile = None
    try:
        profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        return HttpResponse('There is no profile registered for this user.')

    # Display the user's profile
    return render(request, 'rango/otherprofile.html', {
        'username': username,
        'email': user.email,
        'website': profile.website,
        'picture': profile.picture
    })

@login_required
def add_category(request):
    # A HTTP POST?
    if request.method == 'POST':
        form = CategoryForm(request.POST)

        # Have we been provided with a valid form?
        if form.is_valid():
            # Save the new category to the database.
            form.save(commit=True)

            # Now call the index() view.
            # The user will be shown the homepage.
            return index(request)
        else:
            # The supplied form contained errors - just print them to the terminal.
            print form.errors
    else:
        # If the request was not a POST, display the form to enter details.
        form = CategoryForm()

    # Bad form (or form details), no form supplied...
    # Render the form with error messages (if any).
    return render(request, 'rango/add_category.html', {'form': form})

@login_required
def add_page(request, category_name_slug):

    try:
        cat = Category.objects.get(slug=category_name_slug)
    except Category.DoesNotExist:
        cat = None

    if request.method == 'POST':
        form = PageForm(request.POST)
        if form.is_valid():
            if cat:
                page = form.save(commit=False)
                page.category = cat
                page.views = 0
                page.save()
                # probably better to use a redirect here.
                return category(request, category_name_slug)
        else:
            print form.errors
    else:
        form = PageForm()

    context_dict = {'form': form, 'category': cat}

    return render(request, 'rango/add_page.html', context_dict)

@login_required
def restricted(request):
    return render(request, 'rango/restricted.html', {})

@login_required
def like_category(request):
    
    if request.method == 'GET':
        cat_id = request.GET.get('category_id', None)

    if cat_id:
        try:
            cat = Category.objects.get(id=int(cat_id))
        except Category.DoesNotExist:
            return HttpResponse('')

        cat.likes = cat.likes + 1
        cat.save()

    return HttpResponse(cat.likes)