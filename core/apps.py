from django.apps import AppConfig


# Configura core; recibe ajustes Django y produce los metadatos de la aplicacion.
class CoreConfig(AppConfig):
    name = 'core'

    # Recibe el registro de apps cargado; conecta las señales de cuenta oficial y avisos, sin devolver valor.
    def ready(self):
        from . import signals  # noqa: F401
