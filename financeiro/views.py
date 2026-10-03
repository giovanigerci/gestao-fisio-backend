import calendar
from datetime import date, timedelta
from decimal import Decimal
from django.db.models import Case, Count, DecimalField, F, Q, Sum, Value, When
from django.db.models.functions import Coalesce, TruncMonth, TruncYear
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView
from agenda.models import Agendamento

ZERO = Decimal('0.00')
REALIZADO = Agendamento.Status.REALIZADO
AGENDADO = Agendamento.Status.AGENDADO


class ParametroInvalido(Exception):
    def __init__(self, campo, mensagem):
        self.erro = {campo: mensagem}


def data_de_referencia(request):
    valor = request.query_params.get('data')
    if not valor:
        return timezone.localdate()
    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise ParametroInvalido('data', 'Data inválida. Use o formato AAAA-MM-DD.')


def escolha(request, parametro, opcoes, padrao):
    valor = request.query_params.get(parametro, padrao)
    if valor not in opcoes:
        raise ParametroInvalido(parametro, f'Use um destes valores: {", ".join(opcoes)}.')
    return valor


def intervalo(periodo, dia):
    if periodo == 'semana':
        inicio = dia - timedelta(days=(dia.weekday() + 1) % 7)
        return inicio, inicio + timedelta(days=6)
    ultimo_dia = calendar.monthrange(dia.year, dia.month)[1]
    return dia.replace(day=1), dia.replace(day=ultimo_dia)


def intervalo_anterior(periodo, inicio):
    return intervalo(periodo, inicio - timedelta(days=1))


def somar_meses(dia, meses):
    indice = dia.year * 12 + (dia.month - 1) + meses
    return date(indice // 12, indice % 12 + 1, 1)


def dias_entre(inicio, fim):
    return [inicio + timedelta(days=i) for i in range((fim - inicio).days + 1)]


class FinanceiroView(APIView):
    def get(self, request):
        try:
            return Response(self.calcular(request))
        except ParametroInvalido as e:
            return Response(e.erro, status=400)

    def atendimentos(self, request):
        return Agendamento.objects.filter(profissional=request.user.profissional)


class ResumoFinanceiroView(FinanceiroView):
    def calcular(self, request):
        periodo = escolha(request, 'periodo', ('mes', 'semana'), 'mes')
        inicio, fim = intervalo(periodo, data_de_referencia(request))

        resumo = list(
            self.atendimentos(request)
            .filter(status=REALIZADO, eh_experimental=False, data__range=(inicio, fim))
            .values('clinica', 'clinica__nome')
            .annotate(total_atendimentos=Count('id'), receita_total=Coalesce(Sum('valor_cobrado'), ZERO))
            .order_by('clinica__nome')
        )
        return {
            'por_clinica': resumo,
            'total_geral': sum((item['receita_total'] for item in resumo), ZERO),
        }


class EvolucaoReceitaView(FinanceiroView):
    def calcular(self, request):
        periodo = escolha(request, 'periodo', ('mes', 'semana'), 'mes')
        inicio, fim = intervalo(periodo, data_de_referencia(request))
        inicio_anterior, fim_anterior = intervalo_anterior(periodo, inicio)

        preco_previsto = Case(
            When(eh_experimental=True, then=Value(ZERO)),
            default=F('clinica__valor_por_atendimento'),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        )
        por_dia = {
            linha['data']: linha
            for linha in self.atendimentos(request)
            .filter(status__in=[REALIZADO, AGENDADO], data__range=(inicio_anterior, fim))
            .values('data')
            .annotate(
                realizado=Sum('valor_cobrado', filter=Q(status=REALIZADO)),
                previsto=Sum(preco_previsto, filter=Q(status=AGENDADO)),
            )
        }

        dias, acumulado, acumulado_previsto = [], ZERO, ZERO
        for dia in dias_entre(inicio, fim):
            linha = por_dia.get(dia, {})
            realizado = linha.get('realizado') or ZERO
            previsto = linha.get('previsto') or ZERO
            acumulado += realizado
            acumulado_previsto += realizado + previsto
            dias.append({
                'data': dia,
                'realizado': realizado,
                'acumulado': acumulado,
                'previsto': previsto,
                'acumulado_com_previsto': acumulado_previsto,
            })

        dias_anteriores, acumulado_anterior = [], ZERO
        for dia in dias_entre(inicio_anterior, fim_anterior):
            realizado = por_dia.get(dia, {}).get('realizado') or ZERO
            acumulado_anterior += realizado
            dias_anteriores.append({'data': dia, 'realizado': realizado, 'acumulado': acumulado_anterior})

        return {
            'periodo': {'inicio': inicio, 'fim': fim},
            'dias': dias,
            'anterior': {'inicio': inicio_anterior, 'fim': fim_anterior, 'dias': dias_anteriores},
            'totais': {
                'realizado': acumulado,
                'previsto': acumulado_previsto - acumulado,
                'anterior': acumulado_anterior,
            },
        }


class HistoricoReceitaView(FinanceiroView):
    def calcular(self, request):
        agrupar = escolha(request, 'agrupar', ('mes', 'ano'), 'mes')
        referencia = data_de_referencia(request)
        realizados = self.atendimentos(request).filter(status=REALIZADO)

        if agrupar == 'mes':
            primeiro_mes = somar_meses(referencia, -11)
            consulta = realizados.filter(data__gte=somar_meses(primeiro_mes, -12), data__lt=somar_meses(referencia, 1))
            totais = self._totais(consulta, TruncMonth('data'))
            chaves = [somar_meses(primeiro_mes, i) for i in range(12)]
            anterior = lambda chave: somar_meses(chave, -12)
            rotulo = lambda chave: chave.strftime('%Y-%m')
        else:
            totais = self._totais(realizados.filter(data__lt=date(referencia.year + 1, 1, 1)), TruncYear('data'))
            primeiro_ano = min((chave.year for chave in totais), default=referencia.year)
            chaves = [date(ano, 1, 1) for ano in range(primeiro_ano, referencia.year + 1)]
            anterior = lambda chave: date(chave.year - 1, 1, 1)
            rotulo = lambda chave: str(chave.year)

        vazio = {'receita': ZERO, 'atendimentos': 0}
        periodos = [
            {
                'periodo': rotulo(chave),
                'receita': totais.get(chave, vazio)['receita'],
                'atendimentos': totais.get(chave, vazio)['atendimentos'],
                'receita_periodo_anterior': totais.get(anterior(chave), vazio)['receita'],
            }
            for chave in chaves
        ]

        total = sum((p['receita'] for p in periodos), ZERO)
        total_anterior = sum((p['receita_periodo_anterior'] for p in periodos), ZERO)
        melhor = max(periodos, key=lambda p: p['receita'])
        return {
            'agrupar': agrupar,
            'periodos': periodos,
            'resumo': {
                'total': total,
                'media': (total / len(periodos)).quantize(Decimal('0.01')),
                'melhor_periodo': melhor if melhor['receita'] > 0 else None,
                'total_periodo_anterior': total_anterior,
                'variacao_percentual': (
                    ((total - total_anterior) / total_anterior * 100).quantize(Decimal('0.1')) if total_anterior else None
                ),
            },
        }

    @staticmethod
    def _totais(consulta, truncar):
        linhas = (
            consulta.annotate(chave=truncar)
            .values('chave')
            .annotate(receita=Sum('valor_cobrado'), atendimentos=Count('id', filter=Q(eh_experimental=False)))
        )
        return {linha['chave']: {'receita': linha['receita'] or ZERO, 'atendimentos': linha['atendimentos']} for linha in linhas}
