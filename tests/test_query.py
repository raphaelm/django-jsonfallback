import pytest
from django.conf import settings
from django.db import NotSupportedError

from .testapp.models import Book

xfail = pytest.mark.xfail(
    condition=('postgres' not in settings.DATABASES['default']['ENGINE']),
    reason='Not supported on this database',
    raises=NotSupportedError
)


@pytest.fixture
def books():
    return (
        Book.objects.create(data={'title': 'The Lord of the Rings', 'author': 'Tolkien'}),
        Book.objects.create(data={'title': 'Harry Potter', 'author': 'Rowling'})
    )


@pytest.mark.django_db
@xfail
def test_query_subfield(books):
    assert Book.objects.filter(data__author='Tolkien').count() == 1
    assert Book.objects.filter(data__author='Brett').count() == 0


@pytest.mark.django_db
@xfail
def test_query_contains(books):
    assert Book.objects.filter(data__contains={'author': 'Tolkien'}).count() == 1
    assert Book.objects.filter(data__contains={'author': 'Brett'}).count() == 0


@pytest.mark.django_db
@xfail
def test_query_contained_by(books):
    assert Book.objects.filter(data__contained_by={'title': 'Harry Potter', 'author': 'Rowling'}).count() == 1
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
def test_query_icontains_of_field(books):
    assert Book.objects.filter(data__title__icontains='potter').count() == 1
    assert Book.objects.filter(data__title__icontains='foo').count() == 0


@pytest.mark.django_db
def test_query_equal(books):
    assert Book.objects.filter(data={'title': 'Harry Potter', 'author': 'Rowling'}).count() == 1
    assert Book.objects.filter(data={'author': 'Brett'}).count() == 0
