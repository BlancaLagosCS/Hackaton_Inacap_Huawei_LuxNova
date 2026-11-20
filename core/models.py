from django.contrib.auth.models import AbstractUser
from django.db import models

CARRERAS_CHOICES = [(nombre, nombre) for nombre in (
    'Ing. Informática', 'Ing. Diseño', 'Ing. Mecánica',
    'Técnico Analista Programador', 'Técnico Enfermería', 'Técnico Mecánica',
    'Técnico Diseño', 'Técnico Gastronomía',
)]


# Representa Sede; recibe sus campos y relaciones y produce registros persistentes.
class Sede(models.Model):
    nom_sede = models.CharField(max_length=255, unique=True)
    dir_sede = models.CharField(max_length=255)

# Representa Usuario; recibe sus campos y relaciones y produce registros persistentes.
class Usuario(AbstractUser):
    nom_usu = models.CharField(max_length=255)
    rut_usu = models.CharField(max_length=255, unique=True)
    corr_usu = models.EmailField(unique=True)
    tel_usu = models.CharField(max_length=255)
    sede_usu = models.ForeignKey(Sede, on_delete=models.SET_NULL, null=True, blank=True)
    carr_usu = models.CharField(max_length=255, choices=CARRERAS_CHOICES)
    rol_usu = models.CharField(max_length=255, choices=[('ESTUDIANTE', 'ESTUDIANTE'), ('DELEGADO', 'DELEGADO'), ('LIDER_ESTUDIANTIL', 'LIDER_ESTUDIANTIL'), ('JEFATURA', 'JEFATURA'), ('DAE', 'DAE'), ('ADMIN', 'ADMIN')], default='ESTUDIANTE')
    foto_usu = models.ImageField(null=True, blank=True, upload_to='perfiles/')
    bio_usu = models.TextField(blank=True)

# Representa Club; recibe sus campos y relaciones y produce registros persistentes.
class Club(models.Model):
    nom_club = models.CharField(max_length=255)
    cat_club = models.CharField(max_length=255, choices=[('VIDA_ESTUDIANTIL', 'VIDA_ESTUDIANTIL'), ('DESARROLLO_ACADEMICO', 'DESARROLLO_ACADEMICO'), ('OTRO', 'OTRO')])
    desc_club = models.TextField()
    sede_club = models.ForeignKey(Sede, on_delete=models.PROTECT)
    lid_club = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    est_club = models.CharField(max_length=255, choices=[('PENDIENTE_AVALES', 'PENDIENTE_AVALES'), ('PENDIENTE_DAE', 'PENDIENTE_DAE'), ('APROBADO', 'APROBADO'), ('RECHAZADO', 'RECHAZADO')], default='PENDIENTE_AVALES')
    fech_club = models.DateTimeField(auto_now_add=True)
    miem_club = models.ManyToManyField(Usuario, through='MembresiaClub', related_name='clubes_miembro', blank=True)


# Recibe club y usuario; conserva su membresía única y su baja para mantener el historial de eventos accesible.
class MembresiaClub(models.Model):
    club_memb = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='membresias')
    usu_memb = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='membresias_club')
    acti_memb = models.BooleanField(default=True)
    fech_memb = models.DateTimeField(auto_now_add=True)
    baja_memb = models.DateTimeField(null=True, blank=True)

    # Recibe metadatos de membresía; impide duplicar la relación entre el mismo club y usuario.
    class Meta:
        constraints = [models.UniqueConstraint(fields=['club_memb', 'usu_memb'], name='club_usuario_membresia_unica')]

# Representa AvalClub; recibe sus campos y relaciones y produce registros persistentes.
class AvalClub(models.Model):
    club_aval = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='avales')
    estu_aval = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    est_aval = models.CharField(max_length=255, choices=[('PENDIENTE', 'PENDIENTE'), ('ACEPTADO', 'ACEPTADO'), ('RECHAZADO', 'RECHAZADO')], default='PENDIENTE')
    fech_aval = models.DateTimeField(null=True, blank=True)

# Representa Evento; recibe sus campos y relaciones y produce registros persistentes.
class Evento(models.Model):
    tit_even = models.CharField(max_length=255)
    desc_even = models.TextField()
    ban_even = models.ImageField(null=True, blank=True, upload_to='eventos/')
    cat_even = models.CharField(max_length=255, choices=[('TODO_PUBLICO', 'TODO_PUBLICO'), ('CARRERAS_AFINES', 'CARRERAS_AFINES')])
    alc_even = models.CharField(max_length=255, choices=[('SEDE', 'SEDE'), ('INTERSEDE', 'INTERSEDE')], default='SEDE')
    sede_even = models.ForeignKey(Sede, on_delete=models.PROTECT)
    esp_even = models.CharField(max_length=255)
    fech_even = models.DateTimeField()
    ffin_even = models.DateTimeField(null=True, blank=True)
    crea_even = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    orga_even = models.CharField(max_length=16, choices=[('PERSONAL', 'A título personal'), ('CLUB', 'En nombre de un club estudiantil')], default='PERSONAL')
    club_even = models.ForeignKey(Club, on_delete=models.PROTECT, null=True, blank=True, related_name='eventos_club')
    est_even = models.CharField(max_length=255, choices=[('PENDIENTE_DAE', 'PENDIENTE_DAE'), ('APROBADO', 'APROBADO'), ('RECHAZADO', 'RECHAZADO')], default='PENDIENTE_DAE')
    asis_even = models.ManyToManyField(Usuario, blank=True, related_name='eventos_asistidos')

    # Recibe metadatos del evento; exige coherencia entre la representación personal o del club y su vínculo persistente.
    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(orga_even='PERSONAL', club_even__isnull=True) | models.Q(orga_even='CLUB', club_even__isnull=False), name='evento_organizador_coherente')]

# Representa PublicacionForo; recibe sus campos y relaciones y produce registros persistentes.
class PublicacionForo(models.Model):
    aut_publ = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    sede_publ = models.ForeignKey(Sede, on_delete=models.PROTECT)
    etiq_publ = models.CharField(max_length=255, choices=[('AHORA_MISMO', 'AHORA_MISMO'), ('NOTICIA', 'NOTICIA'), ('INICIATIVA', 'INICIATIVA')], default='AHORA_MISMO')
    tit_publ = models.CharField(max_length=255, blank=True)
    cont_publ = models.TextField()
    img_publ = models.ImageField(null=True, blank=True, upload_to='foro/')
    fech_publ = models.DateTimeField(auto_now_add=True)

# Representa ComentarioForo; recibe sus campos y relaciones y produce registros persistentes.
class ComentarioForo(models.Model):
    publ_come = models.ForeignKey(PublicacionForo, on_delete=models.CASCADE, related_name='comentarios')
    aut_come = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    cont_come = models.TextField()
    fech_come = models.DateTimeField(auto_now_add=True)

# Representa MensajeInbox; recibe sus campos y relaciones y produce registros persistentes.
class MensajeInbox(models.Model):
    dest_inbo = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='mensajes_recibidos')
    remi_inbo = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='mensajes_enviados')
    tipo_inbo = models.CharField(max_length=255, choices=[('SISTEMA', 'SISTEMA'), ('SOLICITUD_AVAL', 'SOLICITUD_AVAL'), ('INICIATIVA_BUZON', 'INICIATIVA_BUZON')])
    asun_inbo = models.CharField(max_length=255)
    cuer_inbo = models.TextField()
    club_inbo = models.ForeignKey(Club, on_delete=models.SET_NULL, null=True, blank=True)
    publ_inbo = models.ForeignKey(PublicacionForo, on_delete=models.SET_NULL, null=True, blank=True)
    leid_inbo = models.BooleanField(default=False)
    fech_inbo = models.DateTimeField(auto_now_add=True)

# Representa RegistroAuditoria; recibe sus campos y relaciones y produce registros persistentes.
class RegistroAuditoria(models.Model):
    dae_audi = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    acc_audi = models.CharField(max_length=255)
    det_audi = models.TextField()
    fech_audi = models.DateTimeField(auto_now_add=True)


# Recibe emisor, receptor y texto; conserva mensajes privados y su estado de lectura como registros persistentes.
class MensajeDirecto(models.Model):
    emi_mens = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='dms_enviados')
    rec_mens = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='dms_recibidos')
    cont_mens = models.TextField()
    leid_mens = models.BooleanField(default=False)
    fech_mens = models.DateTimeField(auto_now_add=True)
    aval_mens = models.OneToOneField(AvalClub, on_delete=models.SET_NULL, null=True, blank=True, related_name='mensaje_dm')
