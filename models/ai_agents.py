from openai import OpenAI
import os

api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

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
    job_description = f"""
Título: {job['informacoes_basicas'].get('titulo_vaga', '')}
Cliente: {job['informacoes_basicas'].get('cliente', '')}
Objetivo: {job['informacoes_basicas'].get('objetivo_vaga', '')}
Tipo de Contratação: {job['informacoes_basicas'].get('tipo_contratacao', '')}

Nível Profissional: {job['perfil_vaga'].get('nivel_profissional', '')}
Nível Acadêmico: {job['perfil_vaga'].get('nivel_academico', '')}
Inglês: {job['perfil_vaga'].get('nivel_ingles', '')}
Espanhol: {job['perfil_vaga'].get('nivel_espanhol', '')}
Atividades: {job['perfil_vaga'].get('principais_atividades', '')}
Competências: {job['perfil_vaga'].get('competencia_tecnicas_e_comportamentais', '')}
"""[:1000]

    resume_text = f"""
Nome: {applicant.get('nome', '')}
Área de Atuação: {applicant.get('area_atuacao', '')}
Nível Acadêmico: {applicant.get('nivel_academico', '')}
Inglês: {applicant.get('nivel_ingles', '')}
Espanhol: {applicant.get('nivel_espanhol', '')}

Resumo do CV:
{applicant.get('cv_pt', '')}
"""[:1000]

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
    job_description = f"""
Título: {job['informacoes_basicas'].get('titulo_vaga', '')}
Cliente: {job['informacoes_basicas'].get('cliente', '')}
Objetivo: {job['informacoes_basicas'].get('objetivo_vaga', '')}
Tipo de Contratação: {job['informacoes_basicas'].get('tipo_contratacao', '')}
Nível Profissional: {job['perfil_vaga'].get('nivel_profissional', '')}
Nível Acadêmico: {job['perfil_vaga'].get('nivel_academico', '')}
Inglês: {job['perfil_vaga'].get('nivel_ingles', '')}
Espanhol: {job['perfil_vaga'].get('nivel_espanhol', '')}
Atividades: {job['perfil_vaga'].get('principais_atividades', '')}
Competências: {job['perfil_vaga'].get('competencia_tecnicas_e_comportamentais', '')}
"""[:1000]

    resume_text = f"{cv_text}"[:1000]

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
