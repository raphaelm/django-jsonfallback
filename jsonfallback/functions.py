import copy
from django.db import NotSupportedError
from django.db.models import Expression

from .fields import mysql_compile_json_path, postgres_compile_json_path, FallbackJSONField


class JSONExtract(Expression):
    def __init__(self, expression, *path, output_field=FallbackJSONField(), **extra):
        super().__init__(output_field=output_field)
        self.path = path
        self.source_expression = self._parse_expressions(expression)[0]
        self.extra = extra

    def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False):
        c = self.copy()
        c.is_summary = summarize
        c.source_expression = c.source_expression.resolve_expression(query, allow_joins, reuse, summarize, for_save)
        return c

    def as_sql(self, compiler, connection, function=None, template=None, arg_joiner=None, **extra_context):
        if connection.settings_dict['ENGINE'] == 'django.db.backends.postgresql':
            params = []
            arg_sql, arg_params = compiler.compile(self.source_expression)
            params.extend(arg_params)
            json_path = postgres_compile_json_path(self.path)
            params.append(json_path)
            template = '{} #> %s'.format(arg_sql)
            return template, params
        elif connection.settings_dict['ENGINE'] == 'django.db.backends.mysql':
            params = []
            arg_sql, arg_params = compiler.compile(self.source_expression)
            params.extend(arg_params)
            json_path = mysql_compile_json_path(self.path)
            params.append(json_path)
            template = 'JSON_EXTRACT({}, %s)'.format(arg_sql)
            return template, params
        else:
            raise NotSupportedError(
                'Functions on JSONFields are only supported on PostgreSQL and MySQL at the moment.'
            )

    def copy(self):
        c = super().copy()
        c.source_expression = copy.copy(self.source_expression)
        c.extra = self.extra.copy()
        return c
