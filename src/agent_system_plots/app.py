import requests
import streamlit as st
import os
import pandas as pd
import plotly.io as pio

st.set_page_config(
    page_title="AI agent for data analysis",
    page_icon="🤖", 
    layout="wide")

st.title('AI agent for data analysis')
st.write('Введите запрос для анализа данных (можно загрузить свои данные):')

with st.sidebar:
    st.header("Загрузка данных")
    uploaded_file = st.file_uploader("Выберите файл таблицы:", type=["csv", "xlsx", "xls"])
    
    st.markdown("---")
    if uploaded_file is not None:
        st.success("Файл успешно загружен")
        try:
            if uploaded_file.name.endswith('.csv'):
                df_preview = pd.read_csv(uploaded_file)
            else:
                df_preview = pd.read_excel(uploaded_file)
                
            st.write(f"Файл '{uploaded_file.name}' подключен. Размер: {df_preview.shape[0]} строк, {df_preview.shape[1]} колонок.")
            with st.expander("Посмотреть данные таблицы"):
                st.dataframe(df_preview.head(20), use_container_width=True)
        except Exception as e:
            st.error(f"Ошибка чтения файла: {e}")

user_input = st.text_input(
    label="Введите запрос:",
    placeholder="'Построй график затухающего колебания' или 'Построй гистограмму возраста клиентов по файлу'"
)
    
BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
backend_url = f"http://{BACKEND_HOST}:8000/generate"

if st.button('Сгенерировать график', type = "primary"):
    if not user_input.strip():
        st.warning("Пожалуйста, введите текст запроса")
    else:
        with st.spinner("Агент отправляет запрос к модели и выполняет код..."):
            try:
                data = {'prompt': user_input}
                files = None

                if uploaded_file is not None:
                    uploaded_file.seek(0)
                    files = {'file': (uploaded_file.name, uploaded_file.read(), uploaded_file.type)}
                
                response = requests.post(backend_url, files = files, json=data)
                
                if response.status_code == 200:
                    res_json = response.json()
                    plotly_json = res_json.get('plot')
                    trajectory = res_json.get("trajectory")
                    attempts = res_json.get("attempts")
                    st.success(f"Готово. Затрачено попыток: {attempts}")

                    if isinstance(plotly_json, dict):
                        fig = pio.from_json(json.dumps(plotly_json))
                    else:
                        fig = pio.from_json(str(plotly_json))

                    st.plotly_chart(fig, use_container_width=True)
                    
                    with st.expander("Просмотр логов"):
                        st.markdown(trajectory)

                else:
                    error_detail = response.json().get('detail', {})
                    if isinstance(error_detail, dict):
                        st.error(f"Ошибка: {error_detail.get('message')}")
                        with st.expander("Посмотреть лог ошибок"):
                            st.markdown(error_detail.get('trajectory'))
                    else:
                        st.error(f"Ошибка: {error_detail}")
            except requests.exceptions.ConnectionError:
                    st.error('Ошибка подключения')
            except Exception as e:
                    st.error(f'Ошибка: {e}')
