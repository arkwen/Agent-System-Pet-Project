import sys
import io
import os
from openai import OpenAI

#OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", 'http://127.0.0.1:11434/v1')
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

client = OpenAI(
    api_key='ollama',
    base_url='http://docker.internal'
)

SYSTEM_PROMPT = '''
Ты — специализированный AI-модуль, генерирующий исключительно готовый к выполнению Python-код для визуализации данных с помощью библиотеки matplotlib.

ОСНОВНАЯ ЗАДАЧА:
Сгенерируй автономный скрипт на Python, который строит график на основе запроса пользователя и сохраняет его в файл.

СТРОГИЕ ПРАВИЛА ФОРМАТИРОВАНИЯ ВЫВОДА:
1. Твой ответ должен содержать ТОЛЬКО код. Любые текстовые пояснения, приветствия, вводные слова или комментарии вне блока кода КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНЫ.
2. Код должен быть обернут строго в теги [CODE] и [/CODE].
3. Внутри тегов [CODE] не должно быть markdown-разметки (например, ```python). Только чистый текст программы.

ТЕХНИЧЕСКИЕ ТРЕБОВАНИЯ К КОДУ:
1. Автономность: Код должен запускаться без внешних зависимостей (кроме matplotlib и numpy). Если для графика нужны данные, сгенерируй их реалистично с помощью numpy.
2. Импорты: Всегда явно импортируй библиотеки:
   import matplotlib.pyplot as plt
   import numpy as np
3. Локализация: Если в запросе используется русский язык, подписи осей, легенду и заголовок (plt.title) пиши на русском языке.
4. Закрытие ресурсов: Всегда добавляй plt.close() в самом конце скрипта после сохранения.
5. Финальное действие: Скрипт ОБЯЗАТЕЛЬНО должен завершаться сохранением файла строго следующей командой:
   plt.savefig('output.png')

ПРИМЕР ОТВЕТА:
[CODE]
import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(0, 10, 100)
y = np.sin(x)

plt.figure(figsize=(8, 5))
plt.plot(x, y, label='sin(x)')
plt.title("График функции")
plt.xlabel("Ось X")
plt.ylabel("Ось Y")
plt.grid(True)
plt.legend()

plt.savefig('output.png', bbox_inches='tight', dpi=300)
plt.close()
[/CODE]

Любое нарушение формата (наличие текста вне тегов, отсутствие сохранения в 'output.png') приведет к ошибке парсинга системы. Действуй строго по инструкции.
'''

def extract_and_run_code(llm_output:str) -> str:
    start_tag = "[CODE]"
    end_tag = "[/CODE]"
    
    start_idx = llm_output.find(start_tag)
    end_idx = llm_output.find(end_tag)

    if start_idx == -1 or end_idx == -1:
        return "Ошибка: Модель не обернула код в теги [CODE]...[/CODE]"

    code = llm_output[start_idx+6:end_idx].strip()

    old_stdout = sys.stdout
    redirected_stdout = io.StringIO()
    sys.stdout = redirected_stdout

    try:
        local_vars = {}
        exec(code, {}, local_vars)
        return "Код скомпилирован успешно: график сгенерирован и сохранен."
    except Exception as e:
        return f'Ошибка при компиляции Python-кода: {type(e).__name__}: {e}'
    finally:
        sys.stdout = old_stdout

def DA_agent(user_request:str) -> str:
    try:
        response = client.chat.completions.create(
            model="qwen/qwen3.8-27b:free",
            messages=[
                {'role':'system', 'content': SYSTEM_PROMPT},
                {'role':'user', 'content': f'Запрос пользователя: {user_request}'}
            ],
            temperature=0.1
        )
        llm_text = response.choices[0].message.content
        print('Ответ модели:\n', llm_text)
        status = extract_and_run_code(llm_text)
        return status
    except Exception as e:
        return f'Ошибка обращения к модели:  {type(e).__name__}: {e}'
    

