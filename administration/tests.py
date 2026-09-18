from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.test import TestCase

from .models import Area, Category


class CategoryAreaRelationTests(TestCase):
    def setUp(self):
        self.area = Area.objects.create(name="TI")

    def test_category_requires_area(self):
        category = Category(name="Hardware")
        with self.assertRaises(ValidationError):
            category.full_clean()

    def test_category_belongs_to_exactly_one_area(self):
        category = Category.objects.create(name="Hardware", area=self.area)
        self.assertEqual(category.area, self.area)
        self.assertIn(category, self.area.categories.all())

    def test_area_with_categories_cannot_be_deleted(self):
        Category.objects.create(name="Hardware", area=self.area)
        with self.assertRaises(ProtectedError):
            self.area.delete()

    def test_area_without_categories_can_be_deleted(self):
        empty_area = Area.objects.create(name="Vacía")
        empty_area.delete()
        self.assertFalse(Area.objects.filter(pk=empty_area.pk).exists())
