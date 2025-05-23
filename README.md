# IZA Assistant

## Visão Geral
IZA Assistant é uma aplicação web baseada em Flask que oferece funcionalidades de assistente virtual com recursos de processamento de texto e voz. A aplicação foi projetada para fornecer respostas inteligentes e interativas aos usuários.

## Funcionalidades
- Conversão de texto para voz (Text-to-Speech)
- Transcrição de voz para texto (Speech-to-Text)
- API para geração de perguntas sequenciais
- Interface web interativa

## Tecnologias Utilizadas
- **Backend**: Flask, Flask-SQLAlchemy
- **Banco de Dados**: SQLAlchemy
- **Processamento de Texto**: gTTS (Google Text-to-Speech)
- **Reconhecimento de Voz**: SpeechRecognition
- **Processamento de PDF**: PyMuPDF
- **IA e NLP**: OpenAI API

## Requisitos
- Python 3.12+
- Dependências listadas em `requirements.txt`

## Instalação

### Ambiente Local
1. Clone o repositório
2. Crie um ambiente virtual:
   ```
   python -m venv venv
   source venv/bin/activate  # No Windows: venv\Scripts\activate
   ```
3. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```
4. Configure as variáveis de ambiente no arquivo `.env`
5. Execute a aplicação:
   ```
   flask run
   ```

### Deploy no Azure
A aplicação está configurada para deploy no Azure App Service. Certifique-se de:
- Configurar as variáveis de ambiente no portal do Azure
- Usar o arquivo `.deployment` para excluir arquivos desnecessários
- Verificar a compatibilidade das dependências com o ambiente de produção

## Estrutura do Projeto
```
/
├── app.py              # Arquivo principal da aplicação
├── utils/              # Utilitários e funções auxiliares
│   ├── tts.py          # Módulo de Text-to-Speech
│   └── stt.py          # Módulo de Speech-to-Text
├── static/             # Arquivos estáticos (CSS, JS, imagens)
│   └── audio/          # Arquivos de áudio gerados
├── templates/          # Templates HTML
├── requirements.txt    # Dependências do projeto
└── .deployment         # Configurações de deploy
```

## Pontos de Melhoria
- **Otimização de Processamento de Linguagem Natural**: A versão inicial incluía NLTK, removido por questões de compatibilidade com o ambiente de deploy
- **Aprendizado Adaptativo**: Implementar capacidade de aprendizado contínuo com base em feedback
- **Personalização**: Melhorar a personalização considerando aspectos específicos de diferentes indústrias
- **Integrações**: Desenvolver conectores para plataformas como LinkedIn, Indeed e sistemas ATS
- **Análise Preditiva**: Utilizar machine learning para prever o sucesso potencial de candidatos

## API
- `/speak` - Converte texto em fala
- `/transcribe` - Transcreve áudio em texto
- `/api/next_question` - Gera a próxima pergunta na sequência
