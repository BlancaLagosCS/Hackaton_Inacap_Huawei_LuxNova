from datetime import timedelta
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from .forms import EditarPerfilForm, PublicacionForoForm, SolicitarEventoForm
from .models import Usuario


# Recibe una base aislada; verifica formularios de imágenes, rutas multimedia y estructura del navbar de v7.
class GaleriaV7Tests(TestCase):
    # Recibe formato y tamaño opcional en bytes; devuelve una imagen sintética válida para probar los límites de subida.
    def imagen(self, formato='PNG', tamano=None):
        buffer = BytesIO()
        Image.new('RGB', (2, 2), color='red').save(buffer, format=formato)
        contenido = buffer.getvalue()
        if tamano:
            contenido += b'\0' * max(0, tamano - len(contenido))
        extension = formato.lower()
        return SimpleUploadedFile(f'demo.{extension}', contenido, content_type=f'image/{extension}')

    # Recibe nombre del flujo y archivo; devuelve el formulario con los demás campos obligatorios válidos.
    def formulario(self, tipo, archivo):
        if tipo == 'perfil':
            return EditarPerfilForm({'bio_usu': 'Biografía ficticia'}, {'foto_usu': archivo})
        if tipo == 'foro':
            return PublicacionForoForm({'etiq_publ': 'AHORA_MISMO', 'cont_publ': 'Demo'}, {'img_publ': archivo})
        return SolicitarEventoForm({'orga_even': 'PERSONAL', 'tit_even': 'Evento ficticio', 'desc_even': 'Demo', 'cat_even': 'TODO_PUBLICO', 'alc_even': 'SEDE', 'esp_even': 'Auditorio Principal', 'fech_even': timezone.localtime(timezone.now() + timedelta(days=5)).strftime('%Y-%m-%dT%H:%M'), 'ffin_even': timezone.localtime(timezone.now() + timedelta(days=5, hours=2)).strftime('%Y-%m-%dT%H:%M')}, {'ban_even': archivo})

    # Recibe archivos de tamaño exacto y excedido; comprueba límites 2/3 MB y aceptación de PNG/JPEG.
    def test_limites_imagen(self):
        for tipo, campo, max_mb in [('perfil', 'foto_usu', 2), ('foro', 'img_publ', 3), ('evento', 'ban_even', 3)]:
            form = self.formulario(tipo, self.imagen(tamano=max_mb * 1024 * 1024))
            self.assertTrue(form.is_valid(), form.errors)
            form = self.formulario(tipo, self.imagen(tamano=max_mb * 1024 * 1024 + 1))
            self.assertFalse(form.is_valid())
            self.assertIn(f'{max_mb} MB', str(form.errors[campo]))
            form = self.formulario(tipo, self.imagen('JPEG'))
            self.assertTrue(form.is_valid(), form.errors)

    # Recibe formularios de cada flujo; verifica ayudas exactas, selector de formatos y rechazo de GIF aunque sea una imagen real.
    def test_ayudas_y_formato(self):
        for tipo, campo, dimensiones in [('perfil', 'foto_usu', '400 × 400'), ('foro', 'img_publ', '1080 × 720'), ('evento', 'ban_even', '1200 × 400')]:
            form = self.formulario(tipo, self.imagen('GIF'))
            self.assertIn(dimensiones, form.fields[campo].help_text)
            self.assertEqual(form.fields[campo].widget.attrs['accept'], 'image/png, image/jpeg, image/webp')
            self.assertFalse(form.is_valid())
            self.assertIn('PNG, JPG o WebP', str(form.errors[campo]))

    # Recibe una foto sintética y almacenamiento temporal; verifica guardado en perfiles/ y conservación de la URL /media/.
    def test_guardado_y_rutas(self):
        self.assertEqual(settings.MEDIA_ROOT, settings.BASE_DIR / 'Galeria')
        self.assertIn(settings.BASE_DIR / 'Galeria', settings.STATICFILES_DIRS)
        usuario = Usuario.objects.create_user(username='imagen_demo', rut_usu='DEMO-IMAGEN', corr_usu='imagen@inacapmail.cl')
        with TemporaryDirectory() as carpeta, override_settings(MEDIA_ROOT=carpeta):
            form = EditarPerfilForm({'bio_usu': 'Demo'}, {'foto_usu': self.imagen()}, instance=usuario)
            self.assertTrue(form.is_valid(), form.errors)
            perfil = form.save()
            self.assertTrue(Path(perfil.foto_usu.path).is_relative_to(Path(carpeta)))
            self.assertTrue(Path(perfil.foto_usu.path).is_file())
            self.assertTrue(perfil.foto_usu.url.startswith('/media/perfiles/'))
            form = EditarPerfilForm({'bio_usu': 'Nueva bio'}, instance=perfil)
            self.assertTrue(form.is_valid(), form.errors)

    # Recibe vistas públicas y autenticadas; verifica ausencia de buscador, navegación plegable y título fuera del header.
    def test_navbar_y_titulo(self):
        respuesta = self.client.get('/')
        html = respuesta.content.decode()
        header = html.split('<header class="header-institucional"')[1].split('</header>')[0]
        self.assertNotIn('type="search"', header)
        self.assertNotIn('header-view-title', header)
        self.assertIn('navbar-toggler', header)
        self.assertIn('href="/#actividades"', header)
        self.assertIn('Iniciar sesión', header)
        self.assertIn('view-title', html.split('<main')[1])
        usuario = Usuario.objects.create_user(username='nav_demo', rut_usu='DEMO-NAV', corr_usu='nav@inacapmail.cl')
        self.client.force_login(usuario)
        respuesta = self.client.get('/perfil/')
        self.assertContains(respuesta, 'Mis publicaciones')
        self.assertContains(respuesta, 'Log Out')
        self.assertContains(self.client.get('/perfil/configuracion/'), '400 × 400 px')
