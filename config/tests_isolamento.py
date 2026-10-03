"""
Isolamento multi-tenant: cada profissional só enxerga e altera os próprios dados.

O profissional A tenta, por todos os caminhos da API, ver ou mexer nos dados do profissional B.
Acesso a um registro de outro profissional responde 404 (e não 403), para não revelar que ele existe.
"""
from datetime import time, timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from agenda.models import Agendamento
from clinicas.models import Clinica
from pacientes.models import Paciente
from profissionais.models import Profissional


def criar_profissional(sufixo, cpf_paciente):
    user = User.objects.create_user(username=f'dr_{sufixo}', password='x')
    profissional = Profissional.objects.create(usuario=user, telefone='1', especialidade='x', crefito=f'CREF-{sufixo}')
    clinica = Clinica.objects.create(
        profissional=profissional, nome=f'Clínica {sufixo}', endereco='Rua 1', valor_por_atendimento=Decimal('50.00')
    )
    paciente = Paciente.objects.create(
        profissional=profissional, nome=f'Paciente {sufixo}', cpf=cpf_paciente, telefone='1'
    )
    return user, profissional, clinica, paciente


def ids(response):
    """IDs de uma resposta de listagem, paginada ou não."""
    itens = response.data['results'] if isinstance(response.data, dict) else response.data
    return {item['id'] for item in itens}


class IsolamentoEntreProfissionaisTestCase(TestCase):
    def setUp(self):
        self.user_a, self.prof_a, self.clinica_a, self.paciente_a = criar_profissional('a', '111.111.111-11')
        self.user_b, self.prof_b, self.clinica_b, self.paciente_b = criar_profissional('b', '222.222.222-22')

        self.ontem = timezone.localdate() - timedelta(days=1)
        self.agendamento_a = self.agendar(self.prof_a, self.clinica_a, self.paciente_a)
        self.agendamento_b = self.agendar(self.prof_b, self.clinica_b, self.paciente_b)

        self.client = APIClient()
        self.client.force_authenticate(user=self.user_a)

    def agendar(self, profissional, clinica, paciente, status_=Agendamento.Status.AGENDADO):
        return Agendamento.objects.create(
            profissional=profissional, clinica=clinica, paciente=paciente, data=self.ontem,
            hora_inicio=time(9, 0), hora_fim=time(10, 0), status=status_,
        )

    def payload_agendamento(self, **alteracoes):
        return {
            'clinica': self.clinica_a.id, 'paciente': self.paciente_a.id,
            'data': str(timezone.localdate() + timedelta(days=7)), 'hora_inicio': '15:00', 'hora_fim': '16:00',
            **alteracoes,
        }

    # --- Leitura ---

    def test_listagens_mostram_so_os_dados_do_proprio_profissional(self):
        intervalo = {'data_inicio': str(self.ontem), 'data_fim': str(self.ontem)}
        casos = [
            ('/api/clinicas/', {}, self.clinica_a.id),
            ('/api/clinicas/opcoes/', {}, self.clinica_a.id),
            ('/api/pacientes/', {}, self.paciente_a.id),
            ('/api/pacientes/opcoes/', {}, self.paciente_a.id),
            ('/api/agendamentos/', {}, self.agendamento_a.id),
            ('/api/agendamentos/', intervalo, self.agendamento_a.id),
        ]
        for url, params, esperado in casos:
            with self.subTest(url=url, params=params):
                response = self.client.get(url, params)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(ids(response), {esperado})

    def test_busca_nao_encontra_paciente_de_outro_profissional(self):
        response = self.client.get('/api/pacientes/', {'search': 'Paciente b'})

        self.assertEqual(ids(response), set())

    def test_detalhe_de_registro_de_outro_profissional_responde_404(self):
        for url in (
            f'/api/clinicas/{self.clinica_b.id}/',
            f'/api/pacientes/{self.paciente_b.id}/',
            f'/api/agendamentos/{self.agendamento_b.id}/',
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)

    # --- Escrita em registros de outro profissional ---

    def test_nao_altera_nem_exclui_registro_de_outro_profissional(self):
        casos = [
            (f'/api/clinicas/{self.clinica_b.id}/', {'nome': 'Invadida'}),
            (f'/api/pacientes/{self.paciente_b.id}/', {'nome': 'Invadido'}),
            (f'/api/agendamentos/{self.agendamento_b.id}/', {'status': Agendamento.Status.CANCELADO}),
        ]
        for url, alteracao in casos:
            with self.subTest(url=url):
                self.assertEqual(self.client.patch(url, alteracao).status_code, status.HTTP_404_NOT_FOUND)
                self.assertEqual(self.client.delete(url).status_code, status.HTTP_404_NOT_FOUND)

        self.clinica_b.refresh_from_db()
        self.paciente_b.refresh_from_db()
        self.agendamento_b.refresh_from_db()
        self.assertEqual(self.clinica_b.nome, 'Clínica b')
        self.assertEqual(self.paciente_b.nome, 'Paciente b')
        self.assertEqual(self.agendamento_b.status, Agendamento.Status.AGENDADO)

    def test_campo_profissional_enviado_no_corpo_e_ignorado(self):
        response = self.client.post('/api/clinicas/', {
            'nome': 'Nova', 'endereco': 'Rua 2', 'valor_por_atendimento': '60.00', 'profissional': self.prof_b.id,
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Clinica.objects.get(id=response.data['id']).profissional, self.prof_a)

    # --- Referências cruzadas: usar paciente/clínica de outro profissional ---

    def test_nao_agenda_com_paciente_ou_clinica_de_outro_profissional(self):
        for alteracao in ({'paciente': self.paciente_b.id}, {'clinica': self.clinica_b.id}):
            with self.subTest(alteracao=alteracao):
                response = self.client.post('/api/agendamentos/', self.payload_agendamento(**alteracao))
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(Agendamento.objects.filter(profissional=self.prof_a).count(), 1)

    def test_nao_move_agendamento_para_clinica_de_outro_profissional(self):
        url = f'/api/agendamentos/{self.agendamento_a.id}/'

        response = self.client.patch(url, {'clinica': self.clinica_b.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.agendamento_a.refresh_from_db()
        self.assertEqual(self.agendamento_a.clinica, self.clinica_a)

    def test_recorrencia_com_paciente_de_outro_profissional_nao_cria_nada(self):
        response = self.client.post(
            '/api/agendamentos/recorrente/', {**self.payload_agendamento(paciente=self.paciente_b.id), 'repeticoes': 4}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Agendamento.objects.filter(paciente=self.paciente_b, profissional=self.prof_a).exists())

    def test_cpf_de_paciente_de_outro_profissional_nao_e_revelado(self):
        # O CPF é único por profissional: se fosse único no banco inteiro, o erro de duplicidade
        # revelaria para A que esse CPF está cadastrado na base de B
        response = self.client.post('/api/pacientes/', {
            'nome': 'Mesmo CPF do paciente de B', 'cpf': self.paciente_b.cpf, 'telefone': '1',
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # --- Ações em lote e financeiro ---

    def test_confirmar_dia_nao_altera_agendamentos_de_outro_profissional(self):
        response = self.client.patch(f'/api/agendamentos/confirmar-dia/?data={self.ontem}')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_confirmados'], 1)
        self.agendamento_b.refresh_from_db()
        self.assertEqual(self.agendamento_b.status, Agendamento.Status.AGENDADO)

    def test_resumo_financeiro_nao_inclui_receita_de_outro_profissional(self):
        Agendamento.objects.filter(id__in=[self.agendamento_a.id, self.agendamento_b.id]).update(
            status=Agendamento.Status.REALIZADO, valor_cobrado=Agendamento.expressao_valor_a_cobrar()
        )

        response = self.client.get('/api/resumo-financeiro/', {'periodo': 'mes', 'data': str(self.ontem)})

        self.assertEqual([c['clinica'] for c in response.data['por_clinica']], [self.clinica_a.id])
        self.assertEqual(response.data['total_geral'], Decimal('50.00'))
