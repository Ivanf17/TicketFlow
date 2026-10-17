"""Spanish UI labels for values whose model-level labels are English.

Display-only: the stored values and the model ``choices`` are not
changed (that would generate a migration). Used by the ``ui`` template
library and by the admin forms' role selects.
"""

ROLE_LABELS = {
    "employee": "Empleado",
    "area_manager": "Encargado de área",
    "admin": "Administrador",
    "management": "Gerencia",
}

# Default (English) form labels derived from model field names.
FIELD_LABELS = {
    "Title": "Título",
    "Description": "Descripción",
    "Category": "Categoría",
    "Content": "Comentario",
    "Name": "Nombre",
    "Is active": "Activo",
    "Role": "Rol",
    "Area": "Área",
}


def spanish_role_choices(field):
    """Relabel a role ChoiceField's options in Spanish, keeping values."""
    field.choices = [
        (value, ROLE_LABELS.get(value, label)) for value, label in field.choices
    ]
