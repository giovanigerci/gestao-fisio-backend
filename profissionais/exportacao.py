"""
Exportação integral dos dados do profissional (portabilidade, LGPD art. 18, V): um ZIP com
planilhas CSV que abrem direto no Excel em português (separador ";", UTF-8 com BOM).
"""
import csv
import io
import zipfile

from django.utils import timezone

from agenda.models import Agendamento
from clinicas.models import Clinica
from pacientes.models import Paciente

INICIOS_DE_FORMULA = ('=', '+', '-', '@', '\t', '\r')

LEIAME = """Gestão Fisio — exportação dos seus dados
Gerada em {gerada_em}

Arquivos (abrem no Excel, LibreOffice ou Google Planilhas):

  perfil.csv         seus dados de cadastro
  clinicas.csv       clínicas e o valor por atendimento de cada uma
  pacientes.csv      pacientes, incluindo o histórico médico
  agendamentos.csv   todas as sessões, com a situação e o valor cobrado

Datas no formato dia/mês/ano e valores em reais, com vírgula.

Importante: a guarda do prontuário pelo prazo exigido pelo seu conselho profissional
(Resolução COFFITO nº 414/2012) é responsabilidade do profissional. Guarde este arquivo
em local seguro: ele contém dados pessoais e de saúde dos seus pacientes.
"""


def texto(valor):
    """
    Texto livre seguro para planilhas: o que começaria como fórmula (=, +, -, @) ganha um apóstrofo
    e é lido como texto. Sem isso, um histórico médico malicioso poderia executar fórmulas no Excel
    de quem abrir o arquivo (CSV injection).
    """
    if valor is None:
        return ''
    valor = str(valor)
    return f"'{valor}" if valor.startswith(INICIOS_DE_FORMULA) else valor


def data(valor):
    return valor.strftime('%d/%m/%Y') if valor else ''


def hora(valor):
    return valor.strftime('%H:%M') if valor else ''


def dinheiro(valor):
    return f'{valor:.2f}'.replace('.', ',') if valor is not None else ''


def sim_ou_nao(valor):
    return 'Sim' if valor else 'Não'


def _csv(cabecalho, linhas):
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=';', lineterminator='\r\n')
    escritor.writerow(cabecalho)
    escritor.writerows(linhas)
    return saida.getvalue().encode('utf-8-sig')  # BOM: o Excel reconhece os acentos


def _perfil(profissional):
    usuario = profissional.usuario
    return _csv(
        ['Nome', 'Usuário', 'E-mail', 'Telefone', 'Especialidade', 'CREFITO'],
        [[
            texto(usuario.get_full_name()), texto(usuario.username), texto(usuario.email),
            texto(profissional.telefone), texto(profissional.especialidade), texto(profissional.crefito),
        ]],
    )


def _clinicas(profissional):
    clinicas = Clinica.objects.filter(profissional=profissional).order_by('nome')
    return _csv(
        ['Nome', 'Endereço', 'Telefone', 'Valor por atendimento', 'Ativa'],
        ([texto(c.nome), texto(c.endereco), texto(c.telefone), dinheiro(c.valor_por_atendimento), sim_ou_nao(c.ativo)]
         for c in clinicas),
    )


def _pacientes(profissional):
    pacientes = Paciente.objects.filter(profissional=profissional).order_by('nome')
    return _csv(
        ['Nome', 'CPF', 'Telefone', 'E-mail', 'Data de nascimento', 'Endereço', 'Histórico médico'],
        ([texto(p.nome), texto(p.cpf), texto(p.telefone), texto(p.email), data(p.data_nascimento),
          texto(p.endereco), texto(p.historico_medico)]
         for p in pacientes),
    )


def _agendamentos(profissional):
    agendamentos = (
        Agendamento.objects.filter(profissional=profissional)
        .select_related('paciente', 'clinica')
        .order_by('data', 'hora_inicio', 'id')
    )
    return _csv(
        ['Data', 'Início', 'Fim', 'Paciente', 'CPF do paciente', 'Clínica', 'Situação', 'Aula experimental', 'Valor cobrado'],
        ([data(a.data), hora(a.hora_inicio), hora(a.hora_fim), texto(a.paciente.nome), texto(a.paciente.cpf),
          texto(a.clinica.nome), a.get_status_display(), sim_ou_nao(a.eh_experimental), dinheiro(a.valor_cobrado)]
         for a in agendamentos),
    )


def exportar_dados(profissional):
    """Bytes do ZIP com todos os dados do profissional. Três consultas (clínicas, pacientes, sessões)."""
    arquivo = io.BytesIO()
    with zipfile.ZipFile(arquivo, 'w', zipfile.ZIP_DEFLATED) as pacote:
        gerada_em = timezone.localtime().strftime('%d/%m/%Y às %H:%M')
        pacote.writestr('LEIAME.txt', LEIAME.format(gerada_em=gerada_em).encode('utf-8-sig'))
        pacote.writestr('perfil.csv', _perfil(profissional))
        pacote.writestr('clinicas.csv', _clinicas(profissional))
        pacote.writestr('pacientes.csv', _pacientes(profissional))
        pacote.writestr('agendamentos.csv', _agendamentos(profissional))
    return arquivo.getvalue()


def contar_dados(profissional):
    return {
        'clinicas': Clinica.objects.filter(profissional=profissional).count(),
        'pacientes': Paciente.objects.filter(profissional=profissional).count(),
        'agendamentos': Agendamento.objects.filter(profissional=profissional).count(),
    }
