import os
from datetime import datetime, timedelta, date

import requests
from database import get_connection


def fahrenheit_to_celcius(temp):
    if temp is not None:
        celcius = (temp - 32) * 5 / 9
        return round(celcius, 2)
    return None


def mph_to_kmph(v_mph):
    if v_mph is not None:
        v_kmph = (v_mph * 1.609)
        return round(v_kmph, 2)
    return None


def validar_nome_cidade(cidade):
    if not cidade or not isinstance(cidade, str):
        return 'O nome da cidade é obrigatório.'

    if len(cidade.strip()) < 2:
        return 'O nome da cidade deve ter pelo menos 2 caracteres'

    return None


def transformar_dados_clima(dados_clima):
    clima_atual = dados_clima.get('currentConditions', {})
    dias = dados_clima.get('days', [])[:7]

    data_atual = datetime.now().strftime('%d/%m/%Y')

    dados_processados = {
        'data': data_atual,
        'hora': clima_atual.get('datetime'),
        'cidade': dados_clima.get('resolvedAddress'),
        'temperatura': fahrenheit_to_celcius(clima_atual.get('temp')),
        'umidade': clima_atual.get('humidity'),
        'vento': mph_to_kmph(clima_atual.get('windspeed')),
        'precipitacao': clima_atual.get('precip'),
        'icon': clima_atual.get('icon'),
        'previsao': []
    }

    for dia in dias:
        dia_processado = {
            'data': datetime.strptime(dia['datetime'], "%Y-%m-%d").strftime('%d/%m/%Y'),
            'temperatura_max': fahrenheit_to_celcius(dia.get('tempmax')),
            'temperatura_min': fahrenheit_to_celcius(dia.get('tempmin')),
            'umidade': dia.get('humidity'),
            'vento': mph_to_kmph(dia.get('windspeed')),
            'precipitacao': dia.get('precip'),
            'icon': dia.get('icon'),
        }

        dados_processados['previsao'].append(dia_processado)

    return dados_processados

def salvar_no_banco(clima):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        print("Tentando salvar:", clima)

        cursor.execute("""
            INSERT INTO historico_clima
            (cidade, data, umidade, vento, precipitacao, temp_min, temp_max)
            VALUES (%s, CURRENT_DATE, %s, %s, %s, %s, %s)
            ON CONFLICT (cidade, data) DO NOTHING
        """, (
            clima["cidade"],
            clima["umidade"],
            clima["vento"],
            clima["precipitacao"],
            clima["previsao"][0]["temperatura_min"],
            clima["previsao"][0]["temperatura_max"]
        ))

        conn.commit()
        print("SALVOU!")

        cursor.close()
        conn.close()

    except Exception as e:
        print("ERRO:", e)


def buscar_clima_por_cidade(cidade):
    msg_erro = validar_nome_cidade(cidade)
    if msg_erro:
        return {
            'error': True,
            'message': msg_erro,
            'status': 400
        }

    base_url = os.getenv('BASE_URL_VISUAL_CROSSING')
    api_key = os.getenv('VISUAL_CROSSING_API_KEY')

    if not base_url or not api_key:
        return {
            'error': True,
            'message': 'Configurações de API ausentes.',
            'status': 500
        }

    data_inicial = datetime.now().strftime('%Y-%m-%d')
    data_final = (datetime.now() + timedelta(days=6)).strftime('%Y-%m-%d')

    url = f"{base_url}{cidade}/{data_inicial}/{data_final}?key={api_key}&unitGroup=us&include=days,current"

    try:
        response = requests.get(url, timeout=10)

        if response.status_code == 404:
            return {
                'error': True,
                'message': f"cidade '{cidade}' não encontrada.",
                'status': 404
            }

        response.raise_for_status()

        dados_response = response.json()
        dados_transformados = transformar_dados_clima(dados_response)

        print(dados_transformados)
        salvar_no_banco(dados_transformados)

        return {
            'error': False,
            'data': dados_transformados,
            'status': 200
        }

    except requests.exceptions.Timeout:
        return {
            'error': True,
            'message': 'Tempo de resposta excedido.',
            'status': 504
        }

    except requests.exceptions.RequestException as ex:
        return {
            'error': True,
            'message': f"Erro de conexão: {str(ex)}",
            'status': 502
        }

    except Exception as ex:
        return {
            'error': True,
            'message': f"Erro inesperado: {str(ex)}",
            'status': 500
        }