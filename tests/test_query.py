import django
import pytest
from django.conf import settings
from django.db import NotSupportedError

from .testapp.models import Book

xfail = pytest.mark.xfail(
    condition=(
            'postgres' not in settings.DATABASES['default']['ENGINE']
            and 'mysql' not in settings.DATABASES['default']['ENGINE']
    ),
    reason='Not supported on this database',
    raises=NotSupportedError
)


@pytest.fixture
def books():
    return (
        Book.objects.create(data={'title': 'The Lord of the Rings', 'author': 'Tolkien', 'year': 1954}),
        Book.objects.create(data={'title': 'Harry Potter', 'author': 'Rowling', 'year': 1997})
    )


@pytest.mark.django_db
@xfail
def test_query_subfield(books):
    assert Book.objects.filter(data__author='Tolkien').count() == 1
    assert Book.objects.filter(data__author='Brett').count() == 0
    assert Book.objects.filter(data__year=1997).count() == 1
    assert Book.objects.filter(data__year=1998).count() == 0


@pytest.mark.django_db
@xfail
def test_query_contains(books):
    assert Book.objects.filter(data__contains={'author': 'Tolkien'}).count() == 1
    assert Book.objects.filter(data__contains={'author': 'Brett'}).count() == 0


@pytest.mark.django_db
@xfail
def test_query_contained_by(books):
    assert Book.objects.filter(data__contained_by={'title': 'Harry Potter', 'author': 'Rowling', 'year': 1997}).count() == 1
    assert Book.objects.filter(data__contained_by={'author': 'Brett'}).count() == 0


@pytest.mark.django_db
@xfail
def test_query_has_key(books):
    assert Book.objects.filter(data__has_key='title').count() == 2
    assert Book.objects.filter(data__has_key='foo').count() == 0


@pytest.mark.django_db
@xfail
def test_query_has_keys(books):
    assert Book.objects.filter(data__has_keys=['title']).count() == 2
    assert Book.objects.filter(data__has_keys=['foo']).count() == 0


@pytest.mark.django_db
@xfail
def test_query_has_any_keys(books):
    assert Book.objects.filter(data__has_any_keys=['title', 'foo']).count() == 2
    assert Book.objects.filter(data__has_any_keys=['foo']).count() == 0


@pytest.mark.django_db
@xfail
def test_query_exact_of_field(books):
    assert Book.objects.filter(data__title__exact='Harry Potter').count() == 1
    assert Book.objects.filter(data__title__exact='harry Potter').count() == 0
    assert Book.objects.filter(data__year__exact=1997).count() == 1
    assert Book.objects.filter(data__year__exact=1998).count() == 0


@pytest.mark.django_db
@xfail
def test_query_iexact_of_field(books):
    assert Book.objects.filter(data__title__iexact='harry potter').count() == 1
    assert Book.objects.filter(data__title__iexact='Potter').count() == 0


@pytest.mark.django_db
@xfail
def test_query_startswith_of_field(books):
    assert Book.objects.filter(data__title__startswith='Harry').count() == 1
    assert Book.objects.filter(data__title__startswith='Potter').count() == 0


@pytest.mark.django_db
@xfail
def test_query_istartswith_of_field(books):
    assert Book.objects.filter(data__title__istartswith='harry').count() == 1
    assert Book.objects.filter(data__title__istartswith='potter').count() == 0


@pytest.mark.django_db
@xfail
def test_query_endswith_of_field(books):
    assert Book.objects.filter(data__title__endswith='Potter').count() == 1
    assert Book.objects.filter(data__title__endswith='Harry').count() == 0


@pytest.mark.django_db
@xfail
def test_query_iendswith_of_field(books):
    assert Book.objects.filter(data__title__iendswith='potter').count() == 1
    assert Book.objects.filter(data__title__iendswith='harry').count() == 0


@pytest.mark.django_db
@xfail
def test_query_contains_of_field(books):
    assert Book.objects.filter(data__title__contains='Potter').count() == 1
    assert Book.objects.filter(data__title__contains='foo').count() == 0


@pytest.mark.django_db
@xfail
def test_query_icontains_of_field(books):
    assert Book.objects.filter(data__title__icontains='potter').count() == 1
    assert Book.objects.filter(data__title__icontains='foo').count() == 0


@pytest.mark.django_db
@xfail
@pytest.mark.skipif(django.VERSION < (2, 1), reason="Not supported on Django 2.0")
def test_order_by(books):
    assert list(Book.objects.order_by('data__title').values_list('data__title', flat=True)) == [
        'Harry Potter',
        'The Lord of the Rings'
    ]
    assert Book.objects.filter(data__title__icontains='foo').count() == 0


@pytest.mark.django_db
@pytest.mark.skipif(django.VERSION < (2, 1), reason="Not supported on Django 2.0")
def test_query_equal(books):
    assert Book.objects.filter(data={'author': 'Rowling', 'title': 'Harry Potter', 'year': 1997}).count() == 1
    assert Book.objects.filter(data={'author': 'Brett'}).count() == 0
