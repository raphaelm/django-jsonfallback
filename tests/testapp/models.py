from django.db import models

from jsonfallback.fields import FallbackJSONField


class Book(models.Model):
    data = FallbackJSONField()

    def __str__(self):
        return str(self.data['title'])
