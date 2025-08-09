import requests

response = requests.post(
    'http://localhost:11434/api/generate',
    json={
        'model': 'llama3.1',
        'prompt': 'What is the capital of japan?',
        'stream': False
    }
)

for line in response.iter_lines():
    if line:
        print(line.decode('utf-8'))
