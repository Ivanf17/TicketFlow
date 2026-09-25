from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from administration.models import Area, Category
from assignment.services import auto_assign_ticket
from notifications.services import notify_ticket_comment_added
from tickets.models import Ticket, TicketComment, TicketHistory
from tickets.services import change_ticket_status
from users.models import User

# Support/demo data only, not product functionality (Block 11, point 7.1).
# Every identifier below is a fixed, recognizable "demo_*" name so this
# command's own data is unambiguous to find and never collides with real
# organizational data.
DEMO_PASSWORD = "Demo1234!"
DEMO_USERNAMES = [
    "demo_admin",
    "demo_gerencia",
    "demo_jefe_ti1",
    "demo_jefe_ti2",
    "demo_jefe_mant",
    "demo_jefe_rrhh",
    "demo_empleado_ti1",
    "demo_empleado_ti2",
    "demo_empleado_mant1",
    "demo_empleado_rrhh1",
]


class Command(BaseCommand):
    help = (
        "Carga datos de demostracion (areas, categorias, usuarios de los "
        "cuatro roles y tickets en distintos estados) para probar "
        "TicketFlow o preparar una sustentacion. Ver docs/demostracion.md "
        "para las credenciales generadas. No duplica datos si ya existen: "
        "si detecta una carga anterior, avisa y no hace nada."
    )

    def handle(self, *args, **options):
        if User.objects.filter(username__in=DEMO_USERNAMES).exists():
            self.stdout.write(self.style.WARNING(
                "Ya existen datos de demostracion cargados (usuarios "
                "'demo_*' encontrados). No se modifico nada para evitar "
                "duplicar datos. Si queres recargarlos desde cero, "
                "elimina manualmente los usuarios 'demo_*' (y sus areas: "
                "TI, Mantenimiento, RRHH, si son exclusivas de la demo) "
                "y volve a correr este comando."
            ))
            return

        with transaction.atomic():
            areas = self._create_areas()
            categories = self._create_categories(areas)
            users = self._create_users(areas)
            self._create_tickets(categories, users)

        self.stdout.write(self.style.SUCCESS(
            "Datos de demostracion cargados correctamente. "
            "Credenciales y detalle en docs/demostracion.md."
        ))

    def _create_areas(self):
        names = ["TI", "Mantenimiento", "RRHH"]
        return {name: Area.objects.get_or_create(name=name)[0] for name in names}

    def _create_categories(self, areas):
        by_area = {
            "TI": ["Hardware", "Software", "Redes"],
            "Mantenimiento": ["Electrico", "Plomeria"],
            "RRHH": ["Vacaciones", "Licencias"],
        }
        categories = {}
        for area_name, category_names in by_area.items():
            for category_name in category_names:
                category, _ = Category.objects.get_or_create(
                    name=category_name, area=areas[area_name]
                )
                categories[category_name] = category
        return categories

    def _create_users(self, areas):
        def make(username, role, area=None):
            user = User.objects.create_user(
                username=username, password=DEMO_PASSWORD, role=role, area=area
            )
            return user

        return {
            "admin": make("demo_admin", User.Role.ADMIN),
            "gerencia": make("demo_gerencia", User.Role.MANAGEMENT),
            "jefe_ti1": make("demo_jefe_ti1", User.Role.AREA_MANAGER, areas["TI"]),
            "jefe_ti2": make("demo_jefe_ti2", User.Role.AREA_MANAGER, areas["TI"]),
            "jefe_mant": make(
                "demo_jefe_mant", User.Role.AREA_MANAGER, areas["Mantenimiento"]
            ),
            "jefe_rrhh": make(
                "demo_jefe_rrhh", User.Role.AREA_MANAGER, areas["RRHH"]
            ),
            "empleado_ti1": make(
                "demo_empleado_ti1", User.Role.EMPLOYEE, areas["TI"]
            ),
            "empleado_ti2": make(
                "demo_empleado_ti2", User.Role.EMPLOYEE, areas["TI"]
            ),
            "empleado_mant1": make(
                "demo_empleado_mant1", User.Role.EMPLOYEE, areas["Mantenimiento"]
            ),
            "empleado_rrhh1": make(
                "demo_empleado_rrhh1", User.Role.EMPLOYEE, areas["RRHH"]
            ),
        }

    def _create_tickets(self, categories, users):
        now = timezone.now()

        # (title, description, category, created_by, days_ago, status, hours_to_resolve)
        # hours_to_resolve is only used when status == RESOLVED.
        plan = [
            ("La impresora del piso 2 no enciende", "No prende ni con otro enchufe.",
             "Hardware", "empleado_ti1", 20, Ticket.Status.RESOLVED, 4),
            ("Pantalla parpadea al iniciar", "Se ve intermitente los primeros minutos.",
             "Hardware", "empleado_ti2", 15, Ticket.Status.RESOLVED, 8),
            ("No puedo instalar el software de facturacion", "Falla en el paso final de la instalacion.",
             "Software", "empleado_ti1", 10, Ticket.Status.IN_PROCESS, None),
            ("Error al iniciar sesion en el sistema interno", "Dice contrasena invalida aunque es correcta.",
             "Software", "empleado_ti2", 6, Ticket.Status.RESOLVED, 2),
            ("Wifi de la sala de reuniones no conecta", "Se desconecta cada pocos minutos.",
             "Redes", "empleado_ti1", 3, Ticket.Status.PENDING, None),
            ("VPN no conecta desde casa", "Error de tiempo de espera al conectar.",
             "Redes", "empleado_ti2", 1, Ticket.Status.PENDING, None),
            ("Luces del pasillo parpadean", "Pasillo del segundo piso, ala norte.",
             "Electrico", "empleado_mant1", 18, Ticket.Status.RESOLVED, 24),
            ("Enchufe de la cocina no funciona", "Ningun enchufe de esa pared tiene corriente.",
             "Electrico", "empleado_mant1", 9, Ticket.Status.IN_PROCESS, None),
            ("Perdida de agua en el bano del 3er piso", "Charco creciente cerca del lavamanos.",
             "Plomeria", "empleado_mant1", 5, Ticket.Status.RESOLVED, 6),
            ("Grifo de la cocina gotea", "Gotea incluso cerrado del todo.",
             "Plomeria", "empleado_mant1", 2, Ticket.Status.PENDING, None),
            ("Consulta sobre dias de vacaciones disponibles", "Necesito saber el saldo actual.",
             "Vacaciones", "empleado_rrhh1", 12, Ticket.Status.RESOLVED, 48),
            ("Solicitud de licencia por estudio", "Rinde examen final la semana que viene.",
             "Licencias", "empleado_rrhh1", 7, Ticket.Status.IN_PROCESS, None),
            ("Duda sobre el procedimiento de licencia medica", "No se que certificado adjuntar.",
             "Licencias", "empleado_rrhh1", 4, Ticket.Status.PENDING, None),
            ("Cambio de fechas de vacaciones ya aprobadas", "Necesito moverlas dos semanas.",
             "Vacaciones", "empleado_rrhh1", 1, Ticket.Status.PENDING, None),
        ]

        tickets_by_title = {}
        for (title, description, category_name, employee_key, days_ago,
             status, hours_to_resolve) in plan:
            ticket = Ticket.objects.create_ticket(
                title=title,
                description=description,
                category=categories[category_name],
                created_by=users[employee_key],
            )
            auto_assign_ticket(ticket)
            created_at = now - timedelta(days=days_ago)
            self._backdate_creation(ticket, created_at)
            self._advance_status(ticket, status, hours_to_resolve, created_at)
            tickets_by_title[title] = ticket

        # A couple of comments, for a realistic-looking detail page.
        self._add_comment(
            tickets_by_title["No puedo instalar el software de facturacion"],
            author=users["empleado_ti1"],
            content="¿Alguna novedad? Lo necesito para cerrar el mes.",
        )
        self._add_comment(
            tickets_by_title["Perdida de agua en el bano del 3er piso"],
            author=users["jefe_mant"],
            content="Se corto el suministro de esa columna y ya se reparo.",
        )

    def _backdate_creation(self, ticket, created_at):
        Ticket.objects.filter(pk=ticket.pk).update(created_at=created_at)
        TicketHistory.objects.filter(
            ticket=ticket, previous_status__isnull=True
        ).update(created_at=created_at)
        ticket.refresh_from_db()

    def _advance_status(self, ticket, target_status, hours_to_resolve, created_at):
        if target_status == Ticket.Status.PENDING:
            return
        manager = ticket.assigned_to
        change_ticket_status(ticket, new_status=Ticket.Status.IN_PROCESS, changed_by=manager)
        if target_status == Ticket.Status.IN_PROCESS:
            return
        change_ticket_status(ticket, new_status=Ticket.Status.RESOLVED, changed_by=manager)
        resolved_entry = TicketHistory.objects.get(
            ticket=ticket, status=Ticket.Status.RESOLVED
        )
        TicketHistory.objects.filter(pk=resolved_entry.pk).update(
            created_at=created_at + timedelta(hours=hours_to_resolve)
        )

    def _add_comment(self, ticket, *, author, content):
        TicketComment.objects.create(ticket=ticket, author=author, content=content)
        notify_ticket_comment_added(ticket, author=author)
