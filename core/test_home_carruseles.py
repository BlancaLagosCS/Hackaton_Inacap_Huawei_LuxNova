from datetime import timedelta
import re
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Evento, PublicacionForo, Sede, Usuario


# Recibe una BD aislada; verifica clasificación temporal, privacidad y navegación de los tres carruseles sin cambios de modelos.
class HomeCarruselesTests(TestCase):
    # Crea sedes, usuario y eventos/iniciativas sintéticos; no recibe datos externos ni devuelve valor.
    def setUp(self):
        self.sede = Sede.objects.create(nom_sede='Sede carruseles ficticia', dir_sede='Demo')
        self.otra = Sede.objects.create(nom_sede='Otra sede carruseles', dir_sede='Demo')
        self.usuario = Usuario.objects.create_user(username='carrusel_est', nom_usu='Persona ficticia carruseles', rut_usu='CARRUSEL-EST', corr_usu='carrusel_est@inacap.cl', sede_usu=self.sede, carr_usu='Ing. Informática')
        self.ahora = timezone.now()
        self.proximo = self.evento('Próximo local', 3, 4)
        self.intersede = self.evento('Próximo intersede', 5, 6, sede_even=self.otra, alc_even='INTERSEDE')
        self.pasado = self.evento('Pasado local', -4, -3)
        self.pasado.asis_even.add(self.usuario)
        self.iniciativa = PublicacionForo.objects.create(aut_publ=self.usuario, sede_publ=self.sede, etiq_publ='INICIATIVA', tit_publ='Iniciativa carrusel', cont_publ='Texto de iniciativa ficticia')
        self.client.force_login(self.usuario)

    # Recibe título, días relativos y campos opcionales; devuelve un evento aprobado de prueba.
    def evento(self, titulo, inicio, fin, **campos):
        return Evento.objects.create(**{'tit_even': titulo, 'desc_even': f'Descripción íntegra de {titulo}', 'cat_even': 'TODO_PUBLICO', 'sede_even': self.sede, 'esp_even': 'Auditorio Principal', 'crea_even': self.usuario,
            'fech_even': self.ahora + timedelta(days=inicio), 'ffin_even': self.ahora + timedelta(days=fin) if fin is not None else None, 'est_even': 'APROBADO', **campos})

    # Crea eventos nulos, vigentes y ajenos; verifica listas ordenadas, privacidad por sede y contexto heredado conservado.
    def test_clasificacion_y_visibilidad(self):
        vigente = self.evento('Actividad en curso', -1, 1)
        sin_fin = self.evento('Próximo sin fin', 2, None)
        pasado_sin_fin = self.evento('Pasado sin fin', -2, None)
        for titulo, campos in [('Ajeno privado', {'sede_even': self.otra}), ('Pendiente privado', {'est_even': 'PENDIENTE_DAE'}), ('Rechazado privado', {'est_even': 'RECHAZADO'})]:
            self.evento(titulo, 2, 3, **campos)
        respuesta = self.client.get('/')
        self.assertQuerySetEqual(respuesta.context['eventos_proximos'], [vigente, sin_fin, self.proximo, self.intersede], transform=None)
        self.assertQuerySetEqual(respuesta.context['eventos_pasados'], [pasado_sin_fin, self.pasado], transform=None)
        self.assertIn('eventos_sede', respuesta.context)
        self.assertIn('eventos_intersede', respuesta.context)
        self.assertIn('clubes_activos', respuesta.context)
        for titulo in ('Ajeno privado', 'Pendiente privado', 'Rechazado privado'):
            self.assertNotContains(respuesta, titulo)

    # Congela ahora en los extremos exactos; término o inicio nulo igual a ahora queda solo en próximos.
    def test_limite_temporal_exacto(self):
        termina_ahora = self.evento('Termina exactamente ahora', -1, 0)
        empieza_ahora = self.evento('Empieza exactamente ahora', 0, None)
        with patch('core.views.timezone.now', return_value=self.ahora):
            respuesta = self.client.get('/')
        proximos = list(respuesta.context['eventos_proximos'])
        pasados = list(respuesta.context['eventos_pasados'])
        self.assertIn(termina_ahora, proximos)
        self.assertIn(empieza_ahora, proximos)
        self.assertNotIn(termina_ahora, pasados)
        self.assertNotIn(empieza_ahora, pasados)

    # Recorre iniciativa desde Home al foro y comenta; verifica ancla canónica, compatibilidad antigua y filtro de sede/etiqueta.
    def test_iniciativa_hasta_comentarios(self):
        otra = PublicacionForo.objects.create(aut_publ=self.usuario, sede_publ=self.otra, etiq_publ='INICIATIVA', tit_publ='Idea ajena oculta', cont_publ='Demo')
        noticia = PublicacionForo.objects.create(aut_publ=self.usuario, sede_publ=self.sede, etiq_publ='NOTICIA', tit_publ='Noticia fuera del carrusel', cont_publ='Demo')
        respuesta = self.client.get('/')
        self.assertQuerySetEqual(respuesta.context['iniciativas_carrusel'], [self.iniciativa], transform=None)
        self.assertContains(respuesta, f'href="/foro/#pub-{self.iniciativa.pk}"')
        self.assertNotContains(respuesta, otra.tit_publ)
        self.assertNotContains(respuesta, noticia.tit_publ)
        foro = self.client.get('/foro/')
        self.assertContains(foro, f'id="pub-{self.iniciativa.pk}"')
        self.assertContains(foro, f'id="publicacion-{self.iniciativa.pk}"')
        self.client.post(reverse('core:comentar_publicacion', args=[self.iniciativa.pk]), {'cont_come': 'Comentario ficticio desde iniciativa'})
        self.assertContains(self.client.get('/foro/'), 'Comentario ficticio desde iniciativa')

    # Consulta inscripción y modal pasado; solo próximos admiten POST y el detalle finalizado conserva texto, responsable y conteo real.
    def test_preinscripcion_y_detalle_pasado(self):
        respuesta = self.client.get('/')
        self.assertContains(respuesta, f'action="{reverse("core:preinscripcion", args=[self.proximo.pk])}"')
        self.assertNotContains(respuesta, f'action="{reverse("core:preinscripcion", args=[self.pasado.pk])}"')
        self.assertContains(respuesta, f'id="detallePasado-{self.pasado.pk}"')
        self.assertContains(respuesta, self.pasado.desc_even)
        self.assertContains(respuesta, '1 persona preinscrita')
        self.assertRedirects(self.client.post(reverse('core:preinscripcion', args=[self.proximo.pk])), '/')
        self.assertContains(self.client.get('/'), 'Cancelar pre-inscripción')
        self.assertEqual(self.client.post(reverse('core:preinscripcion', args=[self.pasado.pk])).status_code, 404)

    # Añade varios registros por carrusel; verifica IDs únicos y controles asociados exclusivamente a su propio bloque.
    def test_controles_independientes_y_ids_unicos(self):
        self.evento('Segundo pasado', -2, -1)
        PublicacionForo.objects.create(aut_publ=self.usuario, sede_publ=self.sede, etiq_publ='INICIATIVA', cont_publ='Sin título')
        respuesta = self.client.get('/')
        html = respuesta.content.decode()
        ids = re.findall(r'\bid="([^"]+)"', html)
        self.assertEqual(len(ids), len(set(ids)))
        for nombre in ('carruselProximos', 'carruselIniciativas', 'carruselPasados'):
            self.assertEqual(html.count(f'id="{nombre}"'), 1)
            self.assertEqual(html.count(f'data-bs-target="#{nombre}"'), 2)
        self.assertContains(respuesta, 'Iniciativa de Persona ficticia carruseles')

    # Consulta con DAE y sin datos; conserva gráficos/RUT enmascarado y muestra una tarjeta vacía por categoría sin controles inútiles.
    def test_dae_y_categorias_vacias(self):
        self.proximo.asis_even.add(self.usuario)
        Usuario.objects.filter(pk=self.usuario.pk).update(rol_usu='DAE')
        respuesta = self.client.get('/')
        self.assertContains(respuesta, 'Inscritos por carrera')
        self.assertContains(respuesta, 'Consultar RUTs')
        self.assertNotContains(respuesta, 'Pre-inscribirme')
        Evento.objects.all().delete()
        PublicacionForo.objects.all().delete()
        html = self.client.get('/').content.decode()
        self.assertEqual(html.count('class="carousel-item active"'), 3)
        self.assertNotIn('data-bs-slide="next"', html)
