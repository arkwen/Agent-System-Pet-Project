import requests
import streamlit as st
import os

st.set_page_config(page_title="AI agent for data analysis", page_icon="🤖", layout="centered")
st.title('AI agent for data analysis')
st.write('Введите запрос для анализа данных:')

user_input = st.text_input(
    label = 'Запрос:',
    placeholder='Построй график функции log(tan(x))'
)

BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
backend_url = f"http://{BACKEND_HOST}:8000/generate"

if st.button('Сгенерировать график', type = "primary"):
    if not user_input.strip():
        st.warning("Пожалуйста, введите текст запроса")
    else:
        with st.spinner("Агент отправляет запрос к модели и выполняет код..."):
            try:
                payload = {'prompt': user_input}
                response = requests.post(backend_url, json=payload)
                
                if response.status_code == 200:
                    st.image(response.content, caption = 'Сгенерированный график')
                    st.success('Запрос выполнен успешно!')

                else:
                    error_detail = response.json().get('detail', "Ошибка")
                    st.error(f'Ошибка: {error_detail}')
            except requests.exceptions.ConnectionError:
                    st.error('Ошибка подключения')
            except Exception as e:
                    st.error(f'Произошла ошибка: {e}')
