import math
import streamlit as st
import pandas as pd
import time
import urllib.parse
from geopy.geocoders import Nominatim

# Inicializar o geolocalizador
geolocator = Nominatim(user_agent="aplicacao", timeout=5)

def obterCoordenadas(endereco):
    """Obtém as coordenadas de um endereço."""
    try:
        if pd.notnull(endereco):
            location = geolocator.geocode(endereco, exactly_one=True)
            time.sleep(2)  # Evita bloqueios da API
            if location:
                return location.address, location.latitude, location.longitude
            return "Endereço não encontrado", None, None
        return "Endereço inválido", None, None
    except Exception as e:
        return f"Erro: {e}", None, None

def calcularDistancia(lat1, lon1, lat2, lon2):
    """Calcula a distância euclidiana entre dois pontos."""
    return math.sqrt((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2)

def organizar_pontos_vizinho_mais_proximo(pontos):
    """Ordena os pontos com coordenadas válidas usando o algoritmo do vizinho mais próximo (KNN manual)."""
    if len(pontos) < 2:
        return pontos  # Se há 1 ou 0 pontos, retorna sem alterar

    percurso = [pontos.pop(0)]  # Começa pelo primeiro ponto
    while pontos:
        ultimo_ponto = percurso[-1]
        distancias = [(p, calcularDistancia(ultimo_ponto[0], ultimo_ponto[1], p[0], p[1])) for p in pontos]
        mais_proximo = min(distancias, key=lambda x: x[1])
        percurso.append(mais_proximo[0])
        pontos.remove(mais_proximo[0])

    return percurso

def salvarArquivoCoordenadas(percurso, nome_arquivo="pontos_rota.txt"):
    """Salva os endereços e coordenadas em um arquivo, organizando os que têm coordenadas pelo KNN manual."""
    pontos_com_coord = [p for p in percurso if pd.notna(p[0]) and pd.notna(p[1]) and p[0] != 0 and p[1] != 0]
    pontos_sem_coord = [p for p in percurso if p[0] == 0 or p[1] == 0 or pd.isna(p[0]) or pd.isna(p[1])]

    percurso_organizado = organizar_pontos_vizinho_mais_proximo(pontos_com_coord)

    with open(nome_arquivo, "w", encoding="utf-8") as f:
        # f.write("Pontos com Coordenadas (Organizados pelo Vizinho Mais Próximo):\n")
        for _, _, endereco in percurso_organizado:
            f.write(f"{endereco}\n")

        # f.write("\nPontos sem Coordenadas:\n")
        for _, _, endereco in pontos_sem_coord:
            f.write(f"{endereco}\n")

    print(f"Arquivo {nome_arquivo} gerado com sucesso!")

def gerarLinkRotaGoogleMaps(nome_arquivo="pontos_rota.txt"):
    """
    Lê o arquivo e gera um link do Google Maps com os dados contidos nele.
    Utiliza quote_plus para formatar os endereços e gera a URL com a rota.
    """
    pontos = []
    with open(nome_arquivo, "r", encoding="utf-8") as f:
        linhas = f.readlines()
    
    # Processa cada linha removendo espaços extras
    for linha in linhas:
        linha = linha.strip()
        if linha and "Pontos" not in linha:  # Ignora cabeçalhos, se existirem
            pontos.append(linha)
    
    # Se houver menos de dois pontos, não é possível gerar a rota
    if len(pontos) < 2:
        return None
    
    # Utiliza quote_plus para tratar espaços e caracteres especiais
    pontos_formatados = [urllib.parse.quote_plus(endereco) for endereco in pontos]
    
    # A rota é construída com o primeiro endereço como origem e os demais como destinos (waypoints)
    link_google_maps = "https://www.google.com/maps/dir/" + "/".join(pontos_formatados)
    return link_google_maps

def main():
    st.title("Rotas Vendedores - FIEP")

    uploaded_file = st.file_uploader("Envie o arquivo Excel", type=["xlsx"])
    
    if uploaded_file is not None:
        df_data = pd.read_excel(uploaded_file)

        if "Proprietário" not in df_data.columns or "Endereço" not in df_data.columns:
            st.error("O arquivo precisa conter as colunas 'Proprietário' e 'Endereço'.")
            return

        proprietarios = df_data["Proprietário"].unique().tolist()
        selected_proprietario = st.selectbox("Selecione um Proprietário:", proprietarios)

        if selected_proprietario:
            df_filtrado = df_data[df_data["Proprietário"] == selected_proprietario].copy()

            # Obter coordenadas para cada endereço
            coordenadas = df_filtrado["Endereço"].apply(lambda x: obterCoordenadas(x))
            
            # Separar os valores retornados
            df_filtrado["Endereço Completo"] = coordenadas.apply(lambda x: x[0])
            df_filtrado["Latitude"] = coordenadas.apply(lambda x: x[1])
            df_filtrado["Longitude"] = coordenadas.apply(lambda x: x[2])

            # Converter coordenadas para float
            df_filtrado["Latitude"] = pd.to_numeric(df_filtrado["Latitude"], errors='coerce')
            df_filtrado["Longitude"] = pd.to_numeric(df_filtrado["Longitude"], errors='coerce')

            # Caso a latitude ou longitude sejam NaN, manter o endereço no dataset
            df_filtrado["Latitude"].fillna(0, inplace=True)
            df_filtrado["Longitude"].fillna(0, inplace=True)

            if df_filtrado.empty:
                st.error("Nenhuma localidade válida encontrada.")
                return

            # Exibir os dados carregados
            st.dataframe(df_filtrado[["Proprietário", "Endereço", "Latitude", "Longitude"]])

            # Salvar os dados organizados no arquivo
            percurso = df_filtrado[["Latitude", "Longitude", "Endereço"]].values.tolist()
            salvarArquivoCoordenadas(percurso)

            # Gerar o link do Google Maps com base no arquivo
            link_rota = gerarLinkRotaGoogleMaps()

            if link_rota:
                st.markdown(f"[🗺️ Clique aqui para abrir no Google Maps]({link_rota})", unsafe_allow_html=True)
            else:
                st.warning("Não foi possível gerar a rota. Verifique se há pelo menos dois endereços válidos.")

if __name__ == "__main__":
    main()
