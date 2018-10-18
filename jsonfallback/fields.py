import django
import json

from django.contrib.postgres import lookups
from django.contrib.postgres.fields import jsonb, JSONField
from django.core import checks
from django.db import NotSupportedError
from django.db.models import TextField, lookups as builtin_lookups
from django_mysql.checks import mysql_connections
from django_mysql.utils import connection_is_mariadb


class JsonAdapter(jsonb.JsonAdapter):
    """
    Customized psycopg2.extras.Json to allow for a custom encoder.
    """

    def __init__(self, adapted, dumps=None, encoder=None):
        super().__init__(adapted, dumps=dumps, encoder=encoder)

    def dumps(self, obj):
        options = {'cls': self.encoder} if self.encoder else {}
        options['sort_keys'] = True
        return json.dumps(obj, **options)


class FallbackJSONField(jsonb.JSONField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.encode = self.encoder or json.JSONEncoder(allow_nan=False)
        self.decoder = json.JSONDecoder()

    def db_type(self, connection):
        if connection.settings_dict['ENGINE'] == 'django.db.backends.postgresql':
            return super().db_type(connection)
        elif connection.settings_dict['ENGINE'] == 'django.db.backends.mysql':
            return 'json'
        else:
            data = self.db_type_parameters(connection)
            try:
                return connection.data_types["TextField"] % data
            except KeyError:
                return None

    def get_prep_value(self, value):
        if value is not None:
            return JsonAdapter(value, encoder=self.encoder)
        return value

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
        elif connection.settings_dict['ENGINE'] == 'django.db.backends.postgresql':
            if isinstance(value, str):
                return self.decoder.decode(value)
            else:
                return value
        elif value is None:
            return None
        else:
            return json.loads(value)

    def get_transform(self, name):
        transform = super(jsonb.JSONField, self).get_transform(name)
        if transform:
            return transform
        return FallbackKeyTransformFactory(name)

    def check(self, **kwargs):
        errors = super(JSONField, self).check(**kwargs)
        errors.extend(self._check_json_encoder())
        errors.extend(self._check_mysql_version())
        return errors

    def _check_json_encoder(self):
        errors = []
        if self.encoder.allow_nan:
            errors.append(
                checks.Error(
                    'Custom JSON encoder should have allow_nan=False as MySQL '
                    'does not support NaN/Infinity in JSON.',
                    obj=self,
                    id='django_mysql.E018',
                ),
            )
        return errors

    def _check_mysql_version(self):
        errors = []
        any_conn_works = False
        conns = mysql_connections()
        for alias, conn in conns:
            if (
                    hasattr(conn, 'mysql_version') and
                    not connection_is_mariadb(conn) and
                    conn.mysql_version >= (5, 7)
            ):
                any_conn_works = True

        if conns and self.null:
            errors.append(
                checks.Error(
                    'You should not use nullable JSONFields if you have MySQL connectsions.',
                    obj=self,
                    id='jsonfallback.E001',
                ),
            )

        if conns and not any_conn_works:
            errors.append(
                checks.Error(
                    'MySQL 5.7+ is required to use JSONField',
                    hint='At least one of your DB connections should be to '
                         'MySQL 5.7+',
                    obj=self,
                    id='django_mysql.E016',
                ),
            )
        return errors

    def get_lookup(self, lookup_name):
        # Have to 'unregister' some incompatible lookups
        if lookup_name in {
            'range', 'in', 'iexact', 'icontains', 'startswith',
            'istartswith', 'endswith', 'iendswith', 'search', 'regex',
            'iregex',
        }:
            raise NotImplementedError(
                "Lookup '{}' doesn't work with JSONField".format(lookup_name),
            )
        return super().get_lookup(lookup_name)


class PostgresOnlyLookup:
    def as_sql(self, qn, connection):
        if connection.settings_dict['ENGINE'] == 'django.db.backends.postgresql':
            return super().as_sql(qn, connection)
        raise NotSupportedError(
            'Lookups on JSONFields are only supported on PostgreSQL at the moment.'
        )


@FallbackJSONField.register_lookup
class DataContains(PostgresOnlyLookup, lookups.DataContains):
    pass


@FallbackJSONField.register_lookup
class ContainedBy(PostgresOnlyLookup, lookups.ContainedBy):
    pass


@FallbackJSONField.register_lookup
class HasKey(PostgresOnlyLookup, lookups.HasKey):
    pass


@FallbackJSONField.register_lookup
class HasKeys(PostgresOnlyLookup, lookups.HasKeys):
    pass


@FallbackJSONField.register_lookup
class HasAnyKeys(PostgresOnlyLookup, lookups.HasAnyKeys):
    pass


if django.VERSION >= (2, 1):
    @FallbackJSONField.register_lookup
    class JSONExact(lookups.JSONExact):
        pass


class FallbackKeyTransform(jsonb.KeyTransform):
    def as_sql(self, compiler, connection):
        if connection.settings_dict['ENGINE'] == 'django.db.backends.postgresql':
            return super().as_sql(compiler, connection)
        raise NotSupportedError(
            'Transforms on JSONFields are only supported on PostgreSQL at the moment.'
        )


class FallbackKeyTransformFactory:

    def __init__(self, key_name):
        self.key_name = key_name

    def __call__(self, *args, **kwargs):
        return FallbackKeyTransform(self.key_name, *args, **kwargs)


class KeyTextTransform(FallbackKeyTransform):
    operator = '->>'
    nested_operator = '#>>'
    output_field = TextField()


class KeyTransformTextLookupMixin:
    """
    Mixin for combining with a lookup expecting a text lhs from a JSONField
    key lookup. Make use of the ->> operator instead of casting key values to
    text and performing the lookup on the resulting representation.
    """

    def __init__(self, key_transform, *args, **kwargs):
        assert isinstance(key_transform, FallbackKeyTransform)
        key_text_transform = KeyTextTransform(
            key_transform.key_name, *key_transform.source_expressions, **key_transform.extra
        )
        super().__init__(key_text_transform, *args, **kwargs)


@FallbackKeyTransform.register_lookup
class KeyTransformIExact(KeyTransformTextLookupMixin, builtin_lookups.IExact):
    pass


@FallbackKeyTransform.register_lookup
class KeyTransformIContains(KeyTransformTextLookupMixin, builtin_lookups.IContains):
    pass


@FallbackKeyTransform.register_lookup
class KeyTransformStartsWith(KeyTransformTextLookupMixin, builtin_lookups.StartsWith):
    pass


@FallbackKeyTransform.register_lookup
class KeyTransformIStartsWith(KeyTransformTextLookupMixin, builtin_lookups.IStartsWith):
    pass


@FallbackKeyTransform.register_lookup
class KeyTransformEndsWith(KeyTransformTextLookupMixin, builtin_lookups.EndsWith):
    pass


@FallbackKeyTransform.register_lookup
class KeyTransformIEndsWith(KeyTransformTextLookupMixin, builtin_lookups.IEndsWith):
    pass


@FallbackKeyTransform.register_lookup
class KeyTransformRegex(KeyTransformTextLookupMixin, builtin_lookups.Regex):
    pass


@FallbackKeyTransform.register_lookup
class KeyTransformIRegex(KeyTransformTextLookupMixin, builtin_lookups.IRegex):
    pass
