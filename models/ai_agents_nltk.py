import re
import nltk
from nltk.tokenize import sent_tokenize
from openai import OpenAI
import os

# Garantir que o NLTK tenha os recursos necessários
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

def truncate_text_smartly(text, max_length=1000):
    """
    Trunca o texto de forma inteligente, preservando sentenças completas e 
    priorizando o início e o fim do texto, que geralmente contêm informações mais relevantes.
    
    Args:
        text (str): Texto a ser truncado
        max_length (int): Tamanho máximo desejado
        
    Returns:
        str: Texto truncado de forma inteligente
    """
    if len(text) <= max_length:
        return text
    
    # Tokeniza o texto em sentenças
    sentences = sent_tokenize(text)
    
    # Se tivermos apenas uma sentença muito longa
    if len(sentences) <= 1:
        return text[:max_length]
    
    # Estratégia: manter início e fim, que geralmente contêm informações mais importantes
    # Dividir o limite entre início e fim
    start_portion = int(max_length * 0.7)  # 70% para o início
    end_portion = max_length - start_portion  # 30% para o fim
    
    # Construir o texto truncado
    current_length = 0
    start_sentences = []
    
    # Adicionar sentenças do início até atingir o limite de start_portion
    for sentence in sentences:
        if current_length + len(sentence) <= start_portion:
            start_sentences.append(sentence)
            current_length += len(sentence)
        else:
            break
    
    # Adicionar sentenças do fim até atingir o limite total
    end_sentences = []
    remaining_length = max_length - current_length
    
    for sentence in reversed(sentences):
        if len(sentence) <= remaining_length:
            end_sentences.insert(0, sentence)
            remaining_length -= len(sentence)
        else:
            break
    
    # Combinar início e fim com indicador de truncamento
    if start_sentences and end_sentences and start_sentences[-1] != end_sentences[0]:
        result = "".join(start_sentences) + "\n[...]\n" + "".join(end_sentences)
    else:
        # Se não conseguimos incluir sentenças do fim, apenas use o início
        result = "".join(start_sentences)
        if len(result) < max_length and sentences[len(start_sentences):]:
            result += "\n[...]\n"
    
    return result

def extract_key_fields(data, field_priorities):
    """
    Extrai campos específicos de um dicionário com base em prioridades.
    
    Args:
        data (dict): Dicionário com os dados
        field_priorities (list): Lista de tuplas (caminho_campo, prioridade, max_chars)
        
    Returns:
        str: Texto formatado com os campos extraídos
    """
    result = []
    
    for field_path, priority, max_chars in field_priorities:
        # Suporta caminhos aninhados como 'perfil_vaga.nivel_profissional'
        parts = field_path.split('.')
        value = data
        
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value.get(part, '')
            else:
                value = ''
                break
        
        if value:
            # Trunca o valor se necessário
            if max_chars > 0 and len(str(value)) > max_chars:
                value = truncate_text_smartly(str(value), max_chars)
            
            # Adiciona o campo ao resultado
            field_name = parts[-1].replace('_', ' ').title()
            result.append(f"{field_name}: {value}")
    
    return "\n".join(result)

def agente_avaliar_entrevista(questions, responses):
    combined = "\n".join(f"Q: {q}\nA: {a}" for q, a in zip(questions, responses))
    prompt = f"""
Você é um avaliador de entrevistas. Com base nas perguntas e respostas abaixo, escreva um relatório resumido e dê uma pontuação de 1 a 5, onde 1 é inadequado e 5 é altamente recomendado.

{combined}
"""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=500
    )

    summary = response.choices[0].message.content
    score = next((int(s) for s in summary if s.isdigit()), 3)
    return summary, score


def agente_entrevistador(job, applicant, history):
    # Definir prioridades para campos da vaga (campo, prioridade, max_chars)
    job_priorities = [
        ('informacoes_basicas.titulo_vaga', 1, 100),
        ('informacoes_basicas.cliente', 1, 100),
        ('informacoes_basicas.objetivo_vaga', 1, 200),
        ('informacoes_basicas.tipo_contratacao', 2, 100),
        ('perfil_vaga.nivel_profissional', 2, 100),
        ('perfil_vaga.nivel_academico', 2, 100),
        ('perfil_vaga.nivel_ingles', 3, 50),
        ('perfil_vaga.nivel_espanhol', 3, 50),
        ('perfil_vaga.principais_atividades', 1, 300),
        ('perfil_vaga.competencia_tecnicas_e_comportamentais', 1, 300),
    ]
    
    # Extrair e formatar campos da vaga com base nas prioridades
    job_description = extract_key_fields(job, job_priorities)
    
    # Se ainda exceder o limite, truncar de forma inteligente
    if len(job_description) > 1000:
        job_description = truncate_text_smartly(job_description, 1000)
    
    # Preparar texto do currículo com priorização de campos
    cv_fields = [
        ('nome', 1, 100),
        ('area_atuacao', 1, 100),
        ('nivel_academico', 2, 100),
        ('nivel_ingles', 3, 50),
        ('nivel_espanhol', 3, 50),
    ]
    
    # Extrair campos básicos do currículo
    basic_resume = extract_key_fields(applicant, cv_fields)
    
    # Adicionar o resumo do CV, garantindo espaço suficiente
    cv_text = applicant.get('cv_pt', '')
    remaining_space = 1000 - len(basic_resume) - 20  # 20 caracteres para o cabeçalho
    
    if remaining_space > 100:  # Só incluir se tivermos espaço razoável
        truncated_cv = truncate_text_smartly(cv_text, remaining_space)
        resume_text = f"{basic_resume}\n\nResumo do CV:\n{truncated_cv}"
    else:
        resume_text = basic_resume
    
    # Histórico de perguntas e respostas
    previous = "\n".join([f"Pergunta: {q}\nResposta: {a}" for q, a in history if q and a])

    prompt = f"""
Você é um especialista em RH, experiente em primeiras entrevistas, você está conduzindo uma entrevista. Com base na vaga e currículo abaixo:

VAGA:
{job_description}

CURRÍCULO:
{resume_text}

Histórico da entrevista:
{previous if previous else "Nenhuma pergunta feita até agora. Como é a primeira pergunta você deve fazer uma breve saudação ao candidato."}

Agora, elabore a próxima pergunta, considerando o historico anterior, e os detalhes enviados do candidado e vaga

**Não inclua o prefixo "Pergunta:" — apenas escreva a pergunta diretamente.**
Não explique, não adicione introduções. Apenas retorne a próxima pergunta de forma clara e objetiva.
"""
    
    print(prompt)

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{ "role": "user", "content": prompt }],
        temperature=0.7,
        max_tokens=150
    )

    return response.choices[0].message.content.strip()


def agente_triagem_cvs(job, cv_text):
    # Definir prioridades para campos da vaga
    job_priorities = [
        ('informacoes_basicas.titulo_vaga', 1, 100),
        ('informacoes_basicas.cliente', 2, 100),
        ('informacoes_basicas.objetivo_vaga', 1, 200),
        ('informacoes_basicas.tipo_contratacao', 2, 100),
        ('perfil_vaga.nivel_profissional', 1, 100),
        ('perfil_vaga.nivel_academico', 1, 100),
        ('perfil_vaga.nivel_ingles', 2, 50),
        ('perfil_vaga.nivel_espanhol', 2, 50),
        ('perfil_vaga.principais_atividades', 1, 300),
        ('perfil_vaga.competencia_tecnicas_e_comportamentais', 1, 300),
    ]
    
    # Extrair e formatar campos da vaga com base nas prioridades
    job_description = extract_key_fields(job, job_priorities)
    
    # Se ainda exceder o limite, truncar de forma inteligente
    if len(job_description) > 1000:
        job_description = truncate_text_smartly(job_description, 1000)
    
    # Truncar o CV de forma inteligente
    resume_text = truncate_text_smartly(cv_text, 1000)

    prompt = f"""
Você é um analista de recrutamento sênior. Analise o currículo a seguir e retorne um JSON com a nota de match da vaga, palavras-chaves do curriculo e nome do candidato.

Vaga:
{job_description}

Currículo:
{resume_text}

Formato de resposta obrigatório:
{{
  "nome": "nome_candidato",
  "score": 85.0,
  "keywords": "Python, SQL, Liderança"
}}

SOMENTE retorne esse JSON, sem texto explicativo.
"""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{ "role": "user", "content": prompt }],
        temperature=0.7,
        max_tokens=200
    )

    return response.choices[0].message.content.strip()
