import threading
import time

from DjangoProject.stats import SystemStatystyk
from DjangoProject.system_grup import SystemGrup
from DjangoProject.system_kampani import SystemKampanii
from DjangoProject.system_predykcji import SystemPredykcji


class System:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.system_grup = SystemGrup()
            self.system_kampanii = SystemKampanii()
            self.system_predykcji = SystemPredykcji()
            self.system_statystyk = SystemStatystyk()
            self._stop_event = threading.Event()
            self._thread = threading.Thread(target=self._background_updater, daemon=True)
            self._thread.start()
            self._initialized = True

    def _background_updater(self):

        while not self._stop_event.is_set():
            try:
                print("Aktualizuję dane w systemach...")
                self.system_grup.update_data()
                self.system_kampanii.odswiez_cache()
                self.system_statystyk.update_data()
                self.system_predykcji.update_data()
                print("Aktualizacja zakończona.")
            except Exception as e:
                print(f"Błąd podczas aktualizacji danych: {e}")
            time.sleep(180)

    def stop_updater(self):

        self._stop_event.set()
        self._thread.join()
