import json

from django.contrib.postgres.fields import JSONField


class FallbackJSONField(JSONField):
    def db_type(self, connection):
        if connection.settings_dict['ENGINE'] == 'django.db.backends.postgresql':
            return super().db_type(connection)
        else:
            data = self.db_type_parameters(connection)
            try:
                return connection.data_types["TextField"] % data
            except KeyError:
                return None

    def get_db_prep_value(self, value, connection, prepared=False):
        value = super().get_db_prep_value(value, connection, prepared)
        if connection.settings_dict['ENGINE'] == 'django.db.backends.postgresql':
            return value
        elif value is None:
            return None
        else:
            return value.dumps(value.adapted)

    def from_db_value(self, value, expression, connection):
        if connection.settings_dict['ENGINE'] == 'django.db.backends.postgresql':
            return value
        elif value is None:
            return None
        else:
            return json.loads(value)
