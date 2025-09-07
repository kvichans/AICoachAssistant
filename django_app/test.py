from django.conf import settings
from django.core.files.storage import default_storage
print("MEDIA_ROOT =", settings.MEDIA_ROOT)
print("MEDIA_URL  =", settings.MEDIA_URL)
print("exists?", default_storage.exists("audio/1._Закомство.mp3"))
print(default_storage.listdir("audio"))