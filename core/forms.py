from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils import timezone

from .models import ComentarioForo, PublicacionForo, Sede, Usuario


# Construye opciones legibles; recibe una sede y devuelve su nombre institucional.
class SelectorSede(forms.ModelChoiceField):
    # Recibe una sede consultada y devuelve la etiqueta del selector.
    def label_from_instance(self, obj):
        return obj.nom_sede


# Valida el alta estudiantil; recibe datos y produce un usuario con contraseña cifrada.
class RegistroForm(UserCreationForm):
    sede_usu = SelectorSede(queryset=Sede.objects.order_by('nom_sede'), label='Sede', empty_label='Selecciona tu sede')

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
            field.widget.attrs['class'] = 'form-select' if name == 'sede_usu' else 'form-control'
        self.fields['anio_usu'].min_value = 1900
        self.fields['anio_usu'].max_value = timezone.localdate().year
        self.fields['anio_usu'].widget.attrs.update(min=1900, max=timezone.localdate().year)

    # Recibe el correo validado sintácticamente; devuelve su forma normalizada o un error por duplicado.
    def clean_corr_usu(self):
        correo = self.cleaned_data['corr_usu'].strip().lower()
        if Usuario.objects.filter(corr_usu__iexact=correo).exists():
            raise forms.ValidationError('Ya existe una cuenta con este correo.')
        return correo

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
        widgets = {
            'etiq_publ': forms.Select(attrs={'class': 'form-select'}),
            'tit_publ': forms.TextInput(attrs={'class': 'form-control'}),
            'cont_publ': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'img_publ': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*', 'data-preview-input': 'vista-previa-foro'}),
        }


# Valida un comentario; recibe texto y devuelve contenido limpio sin permitir elegir autor ni publicación.
class ComentarioForoForm(forms.ModelForm):
    # Recibe metadatos del modelo y devuelve la configuración del campo de comentario Bootstrap.
    class Meta:
        model = ComentarioForo
        fields = ('cont_come',)
        labels = {'cont_come': 'Tu comentario'}
        widgets = {'cont_come': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Suma tu comentario…', 'aria-label': 'Tu comentario'})}
