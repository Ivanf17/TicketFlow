from django.db import models


class Area(models.Model):
    """Organizational area/department that users belong to.

    Minimal schema only: this block does not implement administration
    functionality (management screens, permissions, etc.), just the data
    structure needed to support the users.User.area relationship.
    """

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Area"
        verbose_name_plural = "Areas"
        ordering = ["name"]

    def __str__(self):
        return self.name
