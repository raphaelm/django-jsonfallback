from datetime import date

import pytest

from .testapp.models import Book


@pytest.mark.django_db
def test_save_cycle():
    Book.objects.create(data={'title': 'The Lord of the Rings', 'author': 'Tolkien'})
    b = Book.objects.first()
    b.clean()
    assert b.data['title'] == 'The Lord of the Rings'


@pytest.mark.django_db
def test_custom_encoder():
    Book.objects.create(data={'title': 'The Lord of the Rings', 'date': date(1954, 7, 29)})
    b = Book.objects.first()
    b.clean()
    assert b.data['date'] == '1954-07-29'


@pytest.mark.django_db
def test_default():
    Book.objects.create()
    b = Book.objects.first()
    b.clean()
    assert b.data['foo'] == 'bar'


@pytest.mark.django_db
def test_nullable():
    Book.objects.create(data=None)
    b = Book.objects.first()
    b.clean()
    assert b.data is None
