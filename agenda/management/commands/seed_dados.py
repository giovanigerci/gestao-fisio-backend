import random
from datetime import date, timedelta, time

from django.core.management.base import BaseCommand

from profissionais.models import Profissional
from clinicas.models import Clinica
from pacientes.models import Paciente
from agenda.models import Agendamento


NOMES = [
    "João Silva", "Maria Souza", "Pedro Oliveira", "Ana Costa", "Lucas Pereira",
    "Juliana Almeida", "Rafael Santos", "Camila Rodrigues", "Bruno Ferreira",
    "Fernanda Lima", "Gustavo Carvalho", "Patrícia Gomes", "Diego Martins",
    "Larissa Barbosa", "Thiago Rocha",
]

HORARIOS = [time(8, 0), time(9, 0), time(10, 0), time(14, 0), time(15, 0), time(16, 0)]

DEFINICOES_CLINICAS = [
    ("Clínica Vida Ativa", "Rua A, 100", 40.00),
    ("Studio Pilates Bem-Estar", "Rua B, 200", 55.00),
]

class Command(BaseCommand):
    help = "Popula o banco com pacientes e agendamentos de teste."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            type=str,
            default=None,
            help="Username do profissional que receberá os dados de teste.",
        )

    def handle(self, *args, **options):
        username = options["username"]

        if username:
            profissional = Profissional.objects.get(usuario__username=username)
        else:
            profissional = Profissional.objects.first()

        if not profissional:
            self.stdout.write(self.style.ERROR("Nenhum profissional encontrado. Registre um primeiro."))
            return

        self.stdout.write(f"Usando profissional: {profissional}")

        # Garante ao menos 2 clínicas para esse profissional
        clinicas = []
        for nome, endereco, valor in DEFINICOES_CLINICAS:
            clinica, _ = Clinica.objects.get_or_create(
                profissional=profissional,
                nome=nome,
                defaults={"endereco": endereco, "valor_por_atendimento": valor, "ativo": True},
            )
            clinicas.append(clinica)
        self.stdout.write(self.style.SUCCESS(f"{len(clinicas)} clínicas criadas."))

        # Cria 15 pacientes (ou reaproveita se já existirem com esse padrão de CPF)
        pacientes = []
        for i, nome in enumerate(NOMES):
            paciente, _ = Paciente.objects.get_or_create(
                profissional=profissional,
                cpf=f"{100 + i}.000.000-{i:02d}",
                defaults={
                    "nome": nome,
                    "telefone": f"1199999{i:04d}",
                },
            )
            pacientes.append(paciente)
        self.stdout.write(self.style.SUCCESS(f"{len(pacientes)} pacientes disponíveis."))

        # Cria 40 agendamentos espalhados em ±14 dias a partir de hoje
        hoje = date.today()
        criados = 0
        for _ in range(40):
            dias_offset = random.randint(-14, 14)
            data_agendamento = hoje + timedelta(days=dias_offset)
            hora_inicio = random.choice(HORARIOS)
            hora_fim = time(hora_inicio.hour + 1, 0)

            eh_experimental = random.random() < 0.2
            eh_gratuito = eh_experimental and random.random() < 0.5

            if dias_offset < 0:
                status = random.choice(["RE", "RE", "CA"])
            else:
                status = "AG"

            Agendamento.objects.create(
                profissional=profissional,
                clinica=random.choice(clinicas),
                paciente=random.choice(pacientes),
                data=data_agendamento,
                hora_inicio=hora_inicio,
                hora_fim=hora_fim,
                status=status,
                eh_experimental=eh_experimental,
                eh_gratuito=eh_gratuito,
            )
            criados += 1

        self.stdout.write(self.style.SUCCESS(f"{criados} agendamentos criados."))