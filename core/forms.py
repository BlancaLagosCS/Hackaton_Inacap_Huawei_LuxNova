import re

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils import timezone

from .models import CARRERAS_CHOICES, Club, ComentarioForo, Evento, PublicacionForo, Sede, Usuario


# Recibe una imagen validada por Pillow y un máximo en MB; devuelve la imagen o un error por tamaño/formato real no permitido.
def validar_imagen_subida(imagen, max_mb):
    if imagen and hasattr(imagen, 'content_type'):
        if imagen.size > max_mb * 1024 * 1024:
            raise forms.ValidationError(f'La imagen no debe superar {max_mb} MB.')
        if getattr(getattr(imagen, 'image', None), 'format', None) not in ('PNG', 'JPEG', 'WEBP'):
            raise forms.ValidationError('Solo se permiten imágenes PNG, JPG o WebP.')
    return imagen


# Recibe un RUT con formato libre; valida su dígito Módulo 11 y devuelve cuerpo-DV o un error de formulario.
def validar_rut_chileno(rut_raw):
    limpio = re.sub(r'[.\s]', '', str(rut_raw)).upper()
    coincidencia = re.fullmatch(r'([0-9]{1,8})-?([0-9K])', limpio)
    error = 'El RUT ingresado no es válido (dígito verificador incorrecto).'
    if not coincidencia:
        raise forms.ValidationError(error)
    cuerpo, digito = coincidencia.groups()
    cuerpo = str(int(cuerpo))
    if cuerpo == '0':
        raise forms.ValidationError(error)
    suma = sum(int(numero) * (2 + indice % 6) for indice, numero in enumerate(reversed(cuerpo)))
    resultado = 11 - suma % 11
    esperado = '0' if resultado == 11 else 'K' if resultado == 10 else str(resultado)
    if digito != esperado:
        raise forms.ValidationError(error)
    return f'{cuerpo}-{esperado}'


# Recibe nickname y PK opcional del propietario; devuelve un identificador sin espacios, no reservado y único sin distinguir mayúsculas.
def validar_nickname_unico(valor, usuario_pk=None):
    if any(caracter.isspace() for caracter in valor):
        raise forms.ValidationError('El nickname no puede contener espacios.')
    if valor.lower() == 'sistema':
        raise forms.ValidationError('Este nombre está reservado para el canal oficial.')
    if Usuario.objects.exclude(pk=usuario_pk).filter(username__iexact=valor).exists():
        raise forms.ValidationError('Este nickname ya está en uso por otro usuario.')
    return valor


# Recibe correo y PK opcional del dueño; devuelve correo institucional normalizado y único o un error legible.
def validar_correo_unico(valor, usuario_pk=None):
    correo = valor.strip().lower()
    if correo.rsplit('@', 1)[-1] not in ('inacapmail.cl', 'inacap.cl'):
        raise forms.ValidationError('El correo debe ser institucional (@inacapmail.cl o @inacap.cl).')
    if Usuario.objects.exclude(pk=usuario_pk).filter(corr_usu__iexact=correo).exists():
        raise forms.ValidationError('Este correo institucional ya está registrado.')
    return correo


# Construye opciones legibles; recibe una sede y devuelve su nombre institucional.
class SelectorSede(forms.ModelChoiceField):
    # Recibe una sede consultada y devuelve la etiqueta del selector.
    def label_from_instance(self, obj):
        return obj.nom_sede


# Valida el alta estudiantil; recibe datos y produce un usuario con contraseña cifrada.
class RegistroForm(UserCreationForm):
    sede_usu = SelectorSede(queryset=Sede.objects.order_by('nom_sede'), label='Sede', empty_label='Selecciona tu sede')
    carr_usu = forms.ChoiceField(choices=[('', 'Selecciona tu carrera')] + CARRERAS_CHOICES, label='Carrera')

    # Declara los campos editables; recibe metadatos y configura el formulario de registro.
    class Meta:
        model = Usuario
        fields = ('username', 'nom_usu', 'rut_usu', 'corr_usu', 'tel_usu', 'sede_usu', 'carr_usu', 'anio_usu')
        labels = {'nom_usu': 'Nombre completo', 'rut_usu': 'RUT', 'corr_usu': 'Correo institucional', 'tel_usu': 'Teléfono', 'carr_usu': 'Carrera', 'anio_usu': 'Año de ingreso'}

    # Recibe datos y opciones del formulario; devuelve campos obligatorios con estilos Bootstrap.
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.required = True
            field.widget.attrs['class'] = 'form-select' if name in ('sede_usu', 'carr_usu') else 'form-control'
        self.fields['anio_usu'].min_value = 1900
        self.fields['anio_usu'].max_value = timezone.localdate().year
        self.fields['anio_usu'].widget.attrs.update(min=1900, max=timezone.localdate().year)

    # Recibe el correo validado sintácticamente; devuelve su forma normalizada o un error por duplicado.
    def clean_corr_usu(self):
        return validar_correo_unico(self.cleaned_data['corr_usu'])

    # Recibe el nombre de cuenta; reserva sistema sin distinguir mayúsculas y devuelve un identificador permitido.
    def clean_username(self):
        return validar_nickname_unico(super().clean_username())

    # Recibe el RUT enviado; devuelve su forma validada y normalizada o un error claro de duplicación.
    def clean_rut_usu(self):
        rut = validar_rut_chileno(self.cleaned_data['rut_usu'])
        if Usuario.objects.filter(rut_usu__iexact=rut).exists():
            raise forms.ValidationError('Este RUT ya se encuentra registrado en el sistema.')
        return rut

    # Recibe el año de ingreso; devuelve un año válido o un error de rango.
    def clean_anio_usu(self):
        anio = self.cleaned_data['anio_usu']
        if not 1900 <= anio <= timezone.localdate().year:
            raise forms.ValidationError('Ingresa un año de ingreso válido.')
        return anio

    # Recibe la opción de persistir; devuelve un usuario cuyo rol inicial siempre es ESTUDIANTE.
    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.rol_usu = 'ESTUDIANTE'
        if commit:
            usuario.save()
        return usuario


# Conserva compatibilidad con v2; recibe los mismos datos y devuelve el formulario de registro validado.
class RegistroUsuarioForm(RegistroForm):
    pass


# Recibe foto y biografía del propietario; devuelve exclusivamente esos campos editables y validados.
class EditarPerfilForm(forms.ModelForm):
    # Recibe metadatos de Usuario y configura los únicos campos permitidos en la edición del perfil.
    class Meta:
        model = Usuario
        fields = ('foto_usu', 'bio_usu')
        labels = {'foto_usu': 'Foto de perfil', 'bio_usu': 'Biografía'}
        help_texts = {'foto_usu': 'Tamaño recomendado: 400 × 400 px (formato cuadrado 1:1, JPG o PNG, máx. 2 MB). Se ajustará automáticamente en círculo.'}
        widgets = {'foto_usu': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/png, image/jpeg, image/webp'}),
                   'bio_usu': forms.Textarea(attrs={'class': 'form-control', 'rows': 3})}

    # Recibe foto nueva, existente o marca de borrado; devuelve el valor validado con máximo de 2 MB para subidas nuevas.
    def clean_foto_usu(self):
        return validar_imagen_subida(self.cleaned_data.get('foto_usu'), 2)


# Recibe datos del propietario autenticado; valida foto/bio, nickname, correo y cambio opcional de contraseña sin editar roles ni identidad institucional.
class ConfiguracionCuentaForm(EditarPerfilForm):
    username = forms.CharField(label='Nickname', max_length=150, strip=False, widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'username'}))
    nueva_password = forms.CharField(label='Nueva contraseña (opcional)', min_length=6, required=False, strip=False, widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}), help_text='Mínimo 6 caracteres. Deja ambos campos vacíos para conservar tu contraseña.')
    confirmar_password = forms.CharField(label='Confirmar nueva contraseña', required=False, strip=False, widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}))

    # Recibe metadatos de perfil y define los únicos cuatro campos persistentes permitidos, junto a las contraseñas auxiliares.
    class Meta(EditarPerfilForm.Meta):
        fields = ('foto_usu', 'bio_usu', 'username', 'corr_usu')
        labels = {**EditarPerfilForm.Meta.labels, 'corr_usu': 'Correo institucional'}
        help_texts = {'foto_usu': '400 × 400 px recomendado. JPG, PNG o WebP, máx. 2 MB.'}
        widgets = {**EditarPerfilForm.Meta.widgets, 'corr_usu': forms.EmailInput(attrs={'class': 'form-control', 'autocomplete': 'email'})}

    # Recibe el nickname editado; devuelve el valor validado excluyendo al propietario en la consulta de unicidad.
    def clean_username(self):
        return validar_nickname_unico(self.cleaned_data['username'], self.instance.pk)

    # Recibe correo editado; devuelve el correo institucional normalizado y único, excluyendo al propio usuario.
    def clean_corr_usu(self):
        return validar_correo_unico(self.cleaned_data['corr_usu'], self.instance.pk)

    # Recibe campos limpios y devuelve datos o errores cuando las dos contraseñas opcionales no coinciden.
    def clean(self):
        datos = super().clean()
        nueva, confirmar = datos.get('nueva_password', ''), datos.get('confirmar_password', '')
        if (nueva or confirmar) and nueva != confirmar:
            self.add_error('confirmar_password', 'Las contraseñas no coinciden.')
        return datos

    # Recibe opción de persistir; devuelve al dueño con los campos permitidos y contraseña cifrada solo si se solicitó cambiarla.
    def save(self, commit=True):
        usuario = super().save(commit=False)
        if self.cleaned_data.get('nueva_password'):
            usuario.set_password(self.cleaned_data['nueva_password'])
        if commit:
            usuario.save()
        return usuario


ROLES_INSTITUCIONALES = [(rol, rol) for rol in ('DAE', 'JEFATURA', 'DELEGADO', 'LIDER_ESTUDIANTIL', 'ADMIN')]


# Recibe un alta institucional autorizada por la vista; devuelve una cuenta con RUT/correo/nickname válidos y contraseña cifrada.
class CrearCuentaInstitucionalForm(forms.ModelForm):
    username = forms.CharField(label='Nickname', max_length=150, strip=False, widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'off'}))
    sede_usu = SelectorSede(queryset=Sede.objects.order_by('nom_sede'), label='Sede', required=True)
    rol_usu = forms.ChoiceField(label='Rol institucional', choices=ROLES_INSTITUCIONALES)
    password = forms.CharField(label='Contraseña inicial', min_length=6, strip=False, widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}))

    # Recibe metadatos de Usuario y limita el alta a datos institucionales, sin flags Django ni campos de privilegio adicionales.
    class Meta:
        model = Usuario
        fields = ('nom_usu', 'username', 'rut_usu', 'corr_usu', 'tel_usu', 'sede_usu', 'carr_usu', 'rol_usu')
        labels = {'nom_usu': 'Nombre completo', 'rut_usu': 'RUT', 'corr_usu': 'Correo institucional', 'tel_usu': 'Teléfono', 'carr_usu': 'Carrera'}

    # Recibe datos y opciones de ModelForm; aplica Bootstrap y obliga todos los datos de alta, sin devolver valor.
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nombre, campo in self.fields.items():
            campo.required = True
            campo.widget.attrs['class'] = 'form-select' if nombre in ('sede_usu', 'carr_usu', 'rol_usu') else 'form-control'

    # Recibe nickname del alta; devuelve un identificador único sin espacios ni suplantación del sistema.
    def clean_username(self):
        return validar_nickname_unico(self.cleaned_data['username'])

    # Recibe correo del alta; devuelve un correo institucional único y normalizado.
    def clean_corr_usu(self):
        return validar_correo_unico(self.cleaned_data['corr_usu'])

    # Recibe RUT del alta; devuelve su forma Módulo 11 normalizada y única o un error de validación.
    def clean_rut_usu(self):
        rut = validar_rut_chileno(self.cleaned_data['rut_usu'])
        if Usuario.objects.filter(rut_usu__iexact=rut).exists():
            raise forms.ValidationError('Este RUT ya se encuentra registrado en el sistema.')
        return rut

    # Recibe opción de persistencia; devuelve la cuenta nueva con contraseña cifrada, sin otorgar flags de superusuario/staff.
    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.set_password(self.cleaned_data['password'])
        if commit:
            usuario.save()
        return usuario


# Autentica por nombre o correo; recibe credenciales y devuelve un formulario con usuario autenticado.
class LoginForm(AuthenticationForm):
    username = forms.CharField(label='Usuario o correo institucional', widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'username'}))
    password = forms.CharField(label='Contraseña', strip=False, widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'current-password'}))

    # Recibe las credenciales del formulario; devuelve datos limpios o un error genérico de acceso.
    def clean(self):
        identificador = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        if identificador and password:
            # Prioriza un username exacto y resuelve correos solo cuando no existe ese username.
            usuario = Usuario.objects.filter(username=identificador).first()
            if usuario is None:
                usuario = Usuario.objects.filter(corr_usu__iexact=identificador).first()
            self.user_cache = authenticate(self.request, username=usuario.username if usuario else identificador, password=password)
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data


# Valida una publicación; recibe texto, etiqueta e imagen opcional y devuelve datos para guardar sin autor ni sede editables.
class PublicacionForoForm(forms.ModelForm):
    # Recibe metadatos del modelo y define exclusivamente los campos públicos editables del muro.
    class Meta:
        model = PublicacionForo
        fields = ('etiq_publ', 'tit_publ', 'cont_publ', 'img_publ')
        labels = {'etiq_publ': 'Etiqueta', 'tit_publ': 'Título (opcional)', 'cont_publ': '¿Qué está pasando en tu sede?', 'img_publ': 'Foto (opcional)'}
        help_texts = {'img_publ': 'Tamaño recomendado: 1080 × 720 px (horizontal o cuadrada, JPG o PNG, máx. 3 MB).'}
        widgets = {
            'etiq_publ': forms.Select(attrs={'class': 'form-select'}),
            'tit_publ': forms.TextInput(attrs={'class': 'form-control'}),
            'cont_publ': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'img_publ': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/png, image/jpeg, image/webp', 'data-preview-input': 'vista-previa-foro'}),
        }

    # Recibe imagen opcional del muro y devuelve el archivo validado con máximo de 3 MB.
    def clean_img_publ(self):
        return validar_imagen_subida(self.cleaned_data.get('img_publ'), 3)


# Valida un comentario; recibe texto y devuelve contenido limpio sin permitir elegir autor ni publicación.
class ComentarioForoForm(forms.ModelForm):
    # Recibe metadatos del modelo y devuelve la configuración del campo de comentario Bootstrap.
    class Meta:
        model = ComentarioForo
        fields = ('cont_come',)
        labels = {'cont_come': 'Tu comentario'}
        widgets = {'cont_come': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Suma tu comentario…', 'aria-label': 'Tu comentario'})}


# Recibe una sede y un usuario para el selector; devuelve nombres completos legibles para los pares avalistas.
class SelectorAvalistas(forms.ModelMultipleChoiceField):
    # Recibe un usuario del queryset autorizado y devuelve su nombre junto al identificador de cuenta.
    def label_from_instance(self, obj):
        return f'{obj.nom_usu or obj.username} (@{obj.username})'


# Recibe datos de club y usuario actual; valida exactamente cuatro estudiantes de su sede y devuelve una postulación sin guardar.
class PostularClubForm(forms.ModelForm):
    avales = SelectorAvalistas(queryset=Usuario.objects.none(), required=False, label='Selecciona exactamente 4 compañeros', widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 6, 'data-avales-picker': 'true'}))

    # Recibe metadatos y define los campos editables del club, sin sede, líder ni estado manipulables.
    class Meta:
        model = Club
        fields = ('nom_club', 'cat_club', 'desc_club')
        labels = {'nom_club': 'Nombre del club', 'cat_club': 'Categoría', 'desc_club': 'Descripción'}
        widgets = {'nom_club': forms.TextInput(attrs={'class': 'form-control'}), 'cat_club': forms.Select(attrs={'class': 'form-select'}), 'desc_club': forms.Textarea(attrs={'class': 'form-control', 'rows': 3})}

    # Recibe usuario y argumentos de ModelForm; devuelve selector limitado a estudiantes de su sede, excluyéndolo.
    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        if user.sede_usu_id:
            self.fields['avales'].queryset = Usuario.objects.filter(sede_usu_id=user.sede_usu_id, rol_usu='ESTUDIANTE', is_active=True).exclude(pk=user.pk).order_by('nom_usu', 'username')

    # Recibe la selección validada por queryset y devuelve cuatro pares o un error por cantidad incorrecta.
    def clean_avales(self):
        avales = self.cleaned_data['avales']
        if len(avales) != 4:
            raise forms.ValidationError('Debes seleccionar exactamente 4 compañeros de tu sede para avalar el club.')
        return avales


ESPACIOS_CHOICES = [(nombre, nombre) for nombre in ('Auditorio Principal', 'Sala Multiuso 101', 'Laboratorio Computación 3', 'Patio Central / Ágora', 'Cancha Deportiva')]


# Recibe datos de evento y banner opcional; devuelve una solicitud validada sin permitir elegir creador, sede o aprobación.
class SolicitarEventoForm(forms.ModelForm):
    esp_even = forms.ChoiceField(choices=ESPACIOS_CHOICES, label='Espacio institucional', widget=forms.Select(attrs={'class': 'form-select'}))
    ffin_even = forms.DateTimeField(label='Fecha y hora de término', required=True, widget=forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local', 'class': 'form-control'}))

    # Recibe metadatos de Evento y configura sus campos públicos y fecha local HTML5.
    class Meta:
        model = Evento
        fields = ('tit_even', 'desc_even', 'ban_even', 'cat_even', 'alc_even', 'esp_even', 'fech_even', 'ffin_even')
        labels = {'tit_even': 'Título', 'desc_even': 'Descripción', 'ban_even': 'Banner (opcional)', 'cat_even': 'Categoría', 'alc_even': 'Alcance', 'fech_even': 'Fecha y hora de inicio'}
        help_texts = {'ban_even': 'Tamaño recomendado: 1200 × 400 px (formato banner horizontal 3:1, JPG o PNG, máx. 3 MB).'}
        widgets = {'tit_even': forms.TextInput(attrs={'class': 'form-control'}), 'desc_even': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}), 'ban_even': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/png, image/jpeg, image/webp'}), 'cat_even': forms.Select(attrs={'class': 'form-select'}), 'alc_even': forms.Select(attrs={'class': 'form-select'}), 'fech_even': forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local', 'class': 'form-control'})}

    # Recibe banner opcional del evento y devuelve el archivo validado con máximo de 3 MB.
    def clean_ban_even(self):
        return validar_imagen_subida(self.cleaned_data.get('ban_even'), 3)

    # Recibe fecha interpretada en la zona local; devuelve una fecha futura o un error de formulario.
    def clean_fech_even(self):
        fecha = self.cleaned_data['fech_even']
        if fecha <= timezone.now():
            raise forms.ValidationError('La fecha del evento debe estar en el futuro.')
        return fecha

    # Recibe los campos ya interpretados en hora local; devuelve datos limpios o un error si el término no supera el inicio.
    def clean(self):
        datos = super().clean()
        inicio, termino = datos.get('fech_even'), datos.get('ffin_even')
        if inicio and termino and termino <= inicio:
            raise forms.ValidationError('La fecha y hora de término debe ser posterior a la de inicio.')
        return datos
