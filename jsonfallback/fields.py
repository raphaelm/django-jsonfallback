import collections
import json

import django
from django.contrib.postgres import lookups
from django.contrib.postgres.fields import JSONField, jsonb
from django.core import checks
from django.db import NotSupportedError
from django.db.models import Func, TextField, Value, lookups as builtin_lookups
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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
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
        errors.extend(self._check_mysql_version())
        return errors

    def _check_mysql_version(self):
        errors = []
        any_conn_works = False
        conns = mysql_connections()
        for alias, conn in conns:
            if ((hasattr(conn, 'mysql_version') and conn.mysql_version >= (5, 7))
                    or (connection_is_mariadb(conn) and hasattr(conn, 'mysql_version') and
                        conn.mysql_version >= (10, 2, 7))):
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
                         'MySQL 5.7+ or MariaDB 10.2.7+',
                    obj=self,
                    id='django_mysql.E016',
                ),
            )
        return errors

    def get_lookup(self, lookup_name):
        # Have to 'unregister' some incompatible lookups
        if lookup_name in {
            'range', 'iexact', 'icontains', 'startswith',
            'istartswith', 'endswith', 'iendswith', 'search', 'regex',
            'iregex', 'lemgth'
        }:
            raise NotImplementedError(
                "Lookup '{}' doesn't work with JSONField".format(lookup_name),
            )
        return super().get_lookup(lookup_name)


class FallbackLookup:
    def as_sql(self, qn, connection):
        if connection.settings_dict['ENGINE'] == 'django.db.backends.postgresql':
            return super().as_sql(qn, connection)
        raise NotSupportedError(
            'Lookups on JSONFields are only supported on PostgreSQL and MySQL at the moment.'
        )


@FallbackJSONField.register_lookup
class DataContains(FallbackLookup, lookups.DataContains):

    def as_sql(self, qn, connection):
        if connection.settings_dict['ENGINE'] == 'django.db.backends.postgresql':
            return super().as_sql(qn, connection)
        if connection.settings_dict['ENGINE'] == 'django.db.backends.mysql':
            lhs, lhs_params = self.process_lhs(qn, connection)
            rhs, rhs_params = self.process_rhs(qn, connection)
            for i, p in enumerate(rhs_params):
                rhs_params[i] = p.dumps(p.adapted)  # Convert JSONAdapter to str
            params = lhs_params + rhs_params
            return 'JSON_CONTAINS({}, {})'.format(lhs, rhs), params
        raise NotSupportedError('Lookup not supported for %s' % connection.settings_dict['ENGINE'])


@FallbackJSONField.register_lookup
class ContainedBy(FallbackLookup, lookups.ContainedBy):

    def as_sql(self, qn, connection):
        if connection.settings_dict['ENGINE'] == 'django.db.backends.postgresql':
            return super().as_sql(qn, connection)
        if connection.settings_dict['ENGINE'] == 'django.db.backends.mysql':
            lhs, lhs_params = self.process_lhs(qn, connection)
            rhs, rhs_params = self.process_rhs(qn, connection)
            for i, p in enumerate(rhs_params):
                rhs_params[i] = p.dumps(p.adapted)  # Convert JSONAdapter to str
            params = rhs_params + lhs_params
            return 'JSON_CONTAINS({}, {})'.format(rhs, lhs), params
        raise NotSupportedError('Lookup not supported for %s' % connection.settings_dict['ENGINE'])


@FallbackJSONField.register_lookup
class HasKey(FallbackLookup, lookups.HasKey):

    def get_prep_lookup(self):
        if not isinstance(self.rhs, str):
            raise ValueError(
                "JSONField's 'has_key' lookup only works with {} values".format(str),
            )
        return super().get_prep_lookup()

    def as_sql(self, qn, connection):
        if connection.settings_dict['ENGINE'] == 'django.db.backends.postgresql':
            return super().as_sql(qn, connection)
        if connection.settings_dict['ENGINE'] == 'django.db.backends.mysql':
            lhs, lhs_params = self.process_lhs(qn, connection)
            key_name = self.rhs
            path = '$.{}'.format(json.dumps(key_name))
            params = lhs_params + [path]
            return "JSON_CONTAINS_PATH({}, 'one', %s)".format(lhs), params
        raise NotSupportedError('Lookup not supported for %s' % connection.settings_dict['ENGINE'])


class JSONSequencesMixin(object):
    def get_prep_lookup(self):
        if not isinstance(self.rhs, collections.Sequence):
            raise ValueError(
                "JSONField's '{}' lookup only works with Sequences".format(self.lookup_name),
            )
        return self.rhs


@FallbackJSONField.register_lookup
class HasKeys(FallbackLookup, lookups.HasKeys):

    def as_sql(self, qn, connection):
        if connection.settings_dict['ENGINE'] == 'django.db.backends.postgresql':
            return super().as_sql(qn, connection)
        if connection.settings_dict['ENGINE'] == 'django.db.backends.mysql':
            lhs, lhs_params = self.process_lhs(qn, connection)
            paths = [
                '$.{}'.format(json.dumps(key_name))
                for key_name in self.rhs
            ]
            params = lhs_params + paths

            sql = ['JSON_CONTAINS_PATH(', lhs, ", 'all', "]
            sql.append(', '.join('%s' for _ in paths))
            sql.append(')')
            return ''.join(sql), params
        raise NotSupportedError('Lookup not supported for %s' % connection.settings_dict['ENGINE'])


@FallbackJSONField.register_lookup
class HasAnyKeys(FallbackLookup, lookups.HasAnyKeys):

    def as_sql(self, qn, connection):
        if connection.settings_dict['ENGINE'] == 'django.db.backends.postgresql':
            return super().as_sql(qn, connection)
        if connection.settings_dict['ENGINE'] == 'django.db.backends.mysql':
            lhs, lhs_params = self.process_lhs(qn, connection)
            paths = [
                '$.{}'.format(json.dumps(key_name))
                for key_name in self.rhs
            ]
            params = lhs_params + paths

            sql = ['JSON_CONTAINS_PATH(', lhs, ", 'one', "]
            sql.append(', '.join('%s' for _ in paths))
            sql.append(')')
            return ''.join(sql), params
        raise NotSupportedError('Lookup not supported for %s' % connection.settings_dict['ENGINE'])


class JSONValue(Func):
    function = 'CAST'
    template = '%(function)s(%(expressions)s AS JSON)'

    def __init__(self, expression):
        super(JSONValue, self).__init__(Value(expression))


if django.VERSION >= (2, 1):
    @FallbackJSONField.register_lookup
    class JSONExact(lookups.JSONExact):

        def process_rhs(self, compiler, connection):
            rhs, rhs_params = super().process_rhs(compiler, connection)
            if connection.settings_dict['ENGINE'] == 'django.db.backends.mysql':
                if not connection_is_mariadb(connection):
                    func_params = []
                    new_params = []
                    for i, p in enumerate(rhs_params):
                        if not hasattr(p, '_prepare') and p is not None:
                            func, this_func_param = JSONValue(p).as_sql(compiler, connection)
                            func_params.append(func)
                            new_params += this_func_param
                        else:
                            func_params.append(p)
                    rhs, rhs_params = rhs % tuple(func_params), new_params

            return rhs, rhs_params


class FallbackKeyTransform(jsonb.KeyTransform):
    def as_sql(self, compiler, connection):
        if connection.settings_dict['ENGINE'] == 'django.db.backends.postgresql':
            return super().as_sql(compiler, connection)
        elif connection.settings_dict['ENGINE'] == 'django.db.backends.mysql':
            key_transforms = [self.key_name]
            previous = self.lhs
            while isinstance(previous, FallbackKeyTransform):
                key_transforms.insert(0, previous.key_name)
                previous = previous.lhs

            lhs, params = compiler.compile(previous)
            json_path = self.compile_json_path(key_transforms)
            return 'JSON_EXTRACT({}, %s)'.format(lhs), params + [json_path]

        raise NotSupportedError(
            'Transforms on JSONFields are only supported on PostgreSQL and MySQL at the moment.'
        )

    def compile_json_path(self, key_transforms):
        path = ['$']
        for key_transform in key_transforms:
            try:
                num = int(key_transform)
                path.append('[{}]'.format(num))
            except ValueError:  # non-integer
                path.append('.')
                path.append(key_transform)
        return ''.join(path)


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


class StringKeyTransformTextLookupMixin(KeyTransformTextLookupMixin):
    def process_rhs(self, qn, connection):
        rhs = super().process_rhs(qn, connection)
        if connection.settings_dict['ENGINE'] == 'django.db.backends.mysql':
            params = []
            for p in rhs[1]:
                params.append(json.dumps(p))
            return rhs[0], params
        return rhs


class NonStringKeyTransformTextLookupMixin:
    def process_rhs(self, qn, connection):
        rhs = super().process_rhs(qn, connection)
        if connection.settings_dict['ENGINE'] == 'django.db.backends.mysql':
            params = []
            for p in rhs[1]:
                val = json.loads(p)
                if isinstance(val, (list, dict)):
                    val = json.dumps(val)
                params.append(val)
            return rhs[0], params
        return rhs


class MySQLCaseInsensitiveMixin:
    def process_lhs(self, compiler, connection, lhs=None):
        lhs = super().process_lhs(compiler, connection, lhs=None)
        if connection.settings_dict['ENGINE'] == 'django.db.backends.mysql':
            lhs = 'LOWER(%s)' % lhs[0], lhs[1]
        return lhs

    def process_rhs(self, qn, connection):
        rhs = super().process_rhs(qn, connection)
        if connection.settings_dict['ENGINE'] == 'django.db.backends.mysql':
            rhs = 'LOWER(%s)' % rhs[0], rhs[1]
        return rhs


@FallbackKeyTransform.register_lookup
class KeyTransformExact(builtin_lookups.Exact):
    def process_rhs(self, compiler, connection):
        rhs, rhs_params = super().process_rhs(compiler, connection)
        if connection.settings_dict['ENGINE'] == 'django.db.backends.mysql':
            func_params = []
            new_params = []

            for i, p in enumerate(rhs_params):
                val = json.loads(p)
                if isinstance(val, (list, dict)):
                    if not connection_is_mariadb(connection):
                        func, this_func_param = JSONValue(json.dumps(val)).as_sql(compiler, connection)
                        func_params.append(func)
                        new_params += this_func_param
                    else:
                        func_params.append('%s')
                        new_params.append(json.dumps(val))
                else:
                    func_params.append('%s')
                    new_params.append(val)
                rhs, rhs_params = rhs % tuple(func_params), new_params
        return rhs, rhs_params


@FallbackKeyTransform.register_lookup
class KeyTransformIExact(MySQLCaseInsensitiveMixin, StringKeyTransformTextLookupMixin, builtin_lookups.IExact):
    pass


@FallbackKeyTransform.register_lookup
class KeyTransformIContains(MySQLCaseInsensitiveMixin, StringKeyTransformTextLookupMixin, builtin_lookups.IContains):
    pass


@FallbackKeyTransform.register_lookup
class KeyTransformContains(StringKeyTransformTextLookupMixin, builtin_lookups.Contains):
    pass


@FallbackKeyTransform.register_lookup
class KeyTransformStartsWith(StringKeyTransformTextLookupMixin, builtin_lookups.StartsWith):
    pass


@FallbackKeyTransform.register_lookup
class KeyTransformIStartsWith(MySQLCaseInsensitiveMixin, StringKeyTransformTextLookupMixin, builtin_lookups.IStartsWith):
    pass


@FallbackKeyTransform.register_lookup
class KeyTransformEndsWith(StringKeyTransformTextLookupMixin, builtin_lookups.EndsWith):
    pass


@FallbackKeyTransform.register_lookup
class KeyTransformIEndsWith(MySQLCaseInsensitiveMixin, StringKeyTransformTextLookupMixin, builtin_lookups.IEndsWith):
    pass


@FallbackKeyTransform.register_lookup
class KeyTransformRegex(StringKeyTransformTextLookupMixin, builtin_lookups.Regex):
    pass


@FallbackKeyTransform.register_lookup
class KeyTransformIRegex(StringKeyTransformTextLookupMixin, builtin_lookups.IRegex):
    pass


@FallbackKeyTransform.register_lookup
class KeyTransformLte(NonStringKeyTransformTextLookupMixin, builtin_lookups.LessThanOrEqual):
    pass


@FallbackKeyTransform.register_lookup
class KeyTransformLt(NonStringKeyTransformTextLookupMixin, builtin_lookups.LessThan):
    pass


@FallbackKeyTransform.register_lookup
class KeyTransformGte(NonStringKeyTransformTextLookupMixin, builtin_lookups.GreaterThanOrEqual):
    pass


@FallbackKeyTransform.register_lookup
class KeyTransformGt(NonStringKeyTransformTextLookupMixin, builtin_lookups.GreaterThan):
    pass
