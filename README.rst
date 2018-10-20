JSONField with fallback for Django
==================================

.. image:: https://img.shields.io/pypi/v/django-jsonfallback.svg
   :target: https://pypi.python.org/pypi/django-jsonfallback

.. image:: https://travis-ci.com/raphaelm/django-jsonfallback.svg?branch=master
   :target: https://travis-ci.com/raphaelm/django-jsonfallback

.. image:: https://codecov.io/gh/raphaelm/django-jsonfallback/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/raphaelm/django-jsonfallback

This is an extension to ``django.contrib.postgres.fields.JSONField``, that works on other
databases than PostgreSQL.

* On **MySQL** and **MariaDB**, it uses the native JSON data type and supports most features.
* On **SQLite** and all other databases, it just stores JSON strings in a text field and does not support querying.

This is tested against:

* Python 3.4 to 3.6
* Django 2.0 to 2.1
* MySQL 5.7
* MariaDB 10.3
* PostgreSQL 9.4
* SQLite (no querying funcationality)

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
