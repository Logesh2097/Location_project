
from django.shortcuts import render
import requests
import json

# Create your views here.
def index(request):
    ip = requests.get('https://api.ipify.org?format=json')
    ip_data = json.loads(ip.text)
    res = requests.get('http://ip-api.com/json/115.97.97.54')
    location_app_data_one = res.text
    location_app_data = json.loads(location_app_data_one)
    return render(request, 'index.html', {'data': location_app_data})