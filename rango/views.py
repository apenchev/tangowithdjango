from django.shortcuts import render
from django.http import HttpResponse

def index(request):
    return HttpResponse("""Rango says hey there world!
    	<a href=\"./about\">About</a>""")

def about(request):
	return HttpResponse("""Rango says here is the about page.
		Atanas Penchev, 2072742
		<a href=\"./..\">Home</a>""")