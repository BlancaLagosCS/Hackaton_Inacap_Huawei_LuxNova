from django.contrib.auth.views import LoginView
from django.urls import path

from . import views
from .forms import LoginForm

app_name = 'core'
urlpatterns = [
    path('api/buscar-usuarios/', views.buscar_usuarios_api, name='buscar_usuarios_api'),
    path('api/dm/conversaciones/', views.dm_conversaciones, name='dm_conversaciones'),
    path('api/dm/<int:usuario_id>/', views.dm_hilo, name='dm_hilo'),
    path('api/dm/<int:usuario_id>/enviar/', views.dm_enviar, name='dm_enviar'),
    path('api/dm/<int:usuario_id>/leer/', views.dm_leer, name='dm_leer'),
    path('', views.home, name='home'),
    path('registro/', views.registro, name='registro'),
    path('login/', LoginView.as_view(template_name='login.html', authentication_form=LoginForm, redirect_authenticated_user=True), name='login'),
    path('logout/', views.cerrar_sesion, name='logout'),
    path('eventos/<int:evento_id>/preinscripcion/', views.preinscripcion, name='preinscripcion'),
    path('ahora-mismo/', views.ahora_mismo, name='ahora_mismo'),
    path('foro/', views.foro_ahora_mismo, name='foro'),
    path('foro/<int:publ_id>/comentar/', views.comentar_publicacion, name='comentar_publicacion'),
    path('inbox/', views.buzon_inbox, name='inbox'),
    path('inbox/aval/<int:aval_id>/', views.responder_aval, name='responder_aval'),
    path('perfil/', views.mi_perfil, name='perfil'),
    path('perfil/configuracion/', views.configuracion_perfil, name='configuracion_perfil'),
    path('perfil/gestion/', views.gestion_perfil, name='gestion_perfil'),
    path('perfil/organizacion/', views.organizacion_perfil, name='organizacion_perfil'),
    path('mensajes/', views.mensajes, name='mensajes'),
    path('perfil/<int:usuario_id>/', views.ver_perfil, name='ver_perfil'),
    path('panel-admin/crear-cuenta/', views.crear_cuenta_institucional, name='crear_cuenta_institucional'),
    path('club/postular/', views.postular_club, name='postular_club'),
    path('evento/solicitar/', views.solicitar_evento, name='solicitar_evento'),
    path('panel/club/<int:club_id>/<str:accion>/', views.aprobar_rechazar_club, name='resolver_club'),
    path('panel/evento/<int:evento_id>/<str:accion>/', views.aprobar_rechazar_evento, name='resolver_evento'),
    path('panel/usuario/<int:usuario_id>/rol/', views.cambiar_rol_usuario, name='cambiar_rol'),
]
