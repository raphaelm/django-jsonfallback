import pytest

from .testapp.models import Book


@pytest.mark.django_db
def test_save_cycle():
    Book.objects.create(data={'title': 'The Lord of the Rings', 'author': 'Tolkien'})
    b = Book.objects.first()
    b.clean()
    assert b.data['title'] == 'The Lord of the Rings'
