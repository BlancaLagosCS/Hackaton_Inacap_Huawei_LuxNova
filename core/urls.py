from django.contrib.auth.views import LoginView
from django.urls import path

from . import views
from .forms import LoginForm

app_name = 'core'
urlpatterns = [
    path('', views.home, name='home'),
    path('registro/', views.registro, name='registro'),
    path('login/', LoginView.as_view(template_name='login.html', authentication_form=LoginForm, redirect_authenticated_user=True), name='login'),
    path('logout/', views.cerrar_sesion, name='logout'),
    path('eventos/<int:evento_id>/preinscripcion/', views.preinscripcion, name='preinscripcion'),
    path('ahora-mismo/', views.ahora_mismo, name='ahora_mismo'),
    path('inbox/', views.inbox, name='inbox'),
    path('perfil/', views.perfil, name='perfil'),
]
