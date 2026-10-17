"""Presentation-only template helpers for the TicketFlow UI.

Nothing here touches business rules: these filters only decide how
already-computed values (form fields, roles, statuses, query strings)
are rendered. Registered in settings.TEMPLATES["OPTIONS"]["libraries"]
as ``ui`` so templates use ``{% load ui %}``.
"""
from django import forms, template
from django.utils.timesince import timesince

from users.presentation import FIELD_LABELS, ROLE_LABELS

register = template.Library()


@register.filter
def role_label(role):
    return ROLE_LABELS.get(role, role)


@register.filter
def es_label(label):
    """Spanish label for a form field whose default label is English."""
    return FIELD_LABELS.get(str(label), label)


@register.filter
def age(value):
    """Compact elapsed time with only the largest unit ("2 semanas")."""
    if not value:
        return ""
    return timesince(value, depth=1)


@register.filter
def initials(user):
    """Two-letter avatar initials from the full name, or the username."""
    full_name = (user.get_full_name() or "").strip()
    if full_name:
        parts = full_name.split()
        return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()
    return user.get_username()[:2].upper()


@register.filter
def display_name(user):
    return (user.get_full_name() or "").strip() or user.get_username()


@register.filter
def ui_field(bound_field, extra_classes=""):
    """Render a form field's widget with the design-system classes.

    Picks ``form-select`` / ``form-check-input`` / ``form-control`` from
    the widget type, keeps whatever classes the form already declared,
    and adds ``is-invalid`` (plus aria-invalid/aria-describedby) when
    the field has errors so the server-side validation is visible.
    """
    widget = bound_field.field.widget
    if isinstance(widget, (forms.CheckboxInput, forms.RadioSelect, forms.CheckboxSelectMultiple)):
        base = "form-check-input"
    elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
        base = "form-select"
    else:
        base = "form-control"

    classes = widget.attrs.get("class", "").split()
    for css_class in [base, *extra_classes.split()]:
        if css_class not in classes:
            classes.append(css_class)
    attrs = {"class": " ".join(classes)}
    if bound_field.errors:
        attrs["class"] += " is-invalid"
        attrs["aria-invalid"] = "true"
        attrs["aria-describedby"] = f"{bound_field.auto_id}_errors"
    elif bound_field.help_text:
        attrs["aria-describedby"] = f"{bound_field.auto_id}_help"
    return bound_field.as_widget(attrs=attrs)


@register.filter
def is_checkbox(bound_field):
    return isinstance(bound_field.field.widget, forms.CheckboxInput)


@register.simple_tag(takes_context=True)
def query_replace(context, **kwargs):
    """Current query string with ``kwargs`` replaced (empty value drops
    the key). Lets pagination links keep the active filters."""
    query = context["request"].GET.copy()
    for key, value in kwargs.items():
        if value in (None, ""):
            query.pop(key, None)
        else:
            query[key] = value
    encoded = query.urlencode()
    return f"?{encoded}" if encoded else "?"
