JSONField with fallback for Django
==================================

.. image:: https://img.shields.io/pypi/v/django-jsonfallback.svg
   :target: https://pypi.python.org/pypi/django-jsonfallback

.. image:: https://travis-ci.com/raphaelm/django-jsonfallback.svg?branch=master
   :target: https://travis-ci.com/raphaelm/django-jsonfallback

.. image:: https://codecov.io/gh/raphaelm/django-jsonfallback/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/raphaelm/django-jsonfallback

This is an extension to ``django.contrib.postgres.fields.JSONField``, that works on other
databases than PostgreSQL. On these databases, it falls back to storing plain JSON content
in a text field. It handles serialization and deserialization transparently for you, but
advanced query features for JSON fields are only available on PostgreSQL.

We'd love to see this extended by using the ``django-mysql`` implementation on MySQL, but
we lack the development capacity to do this. If you'd like to contribute, just get in touch!

Compatible with:

* Python 3.4 to 3.6
* Django 2.0 to 2.1
* SQlite, MySQL, PostgreSQL

Usage
-----

Just use our drop-in replacement for JSONField::

    from django.db import models
    from jsonfallback.fields import FallbackJSONField


    class Book(models.Model):
        data = FallbackJSONField()

        def __str__(self):
            return str(self.data['title'])


License
-------
The code in this repository is published under the terms of the Apache License. 
See the LICENSE file for the complete license text.

This project is maintained by Raphael Michel <mail@raphaelmichel.de>. See the
AUTHORS file for a list of all the awesome folks who contributed to this project.

.. _pretix: https://github.com/pretix/pretix
.. _django: https://www.djangoproject.com/
.. _django-hvad: https://github.com/KristianOellegaard/django-hvad
.. _django-modeltranslation: https://github.com/deschler/django-modeltranslation
.. _django-parler: https://github.com/django-parler/django-parler
.. _nece: https://pypi.python.org/pypi/nece
.. _1NF: https://en.wikipedia.org/wiki/First_normal_form
