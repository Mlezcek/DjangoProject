# myapp/apps.py
from django.apps import AppConfig

class MyAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'DjangoProject'

    def ready(self):
        from .system import System
        # Tworzymy globalną instancję systemu
        global system_instance
        system_instance = System()
