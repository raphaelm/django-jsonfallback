from django.contrib.postgres.fields import JSONField


class FallbackJSONField(JSONField):
    pass
