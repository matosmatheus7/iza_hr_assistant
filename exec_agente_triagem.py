import os
import json
import time
import re
import random
import nltk
from nltk.tokenize import sent_tokenize
from flask import Flask
from openai import OpenAI
from db.database import db, Job, Applicant, Prospect, MatchResult

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, "data", "appdata.db")
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

output_json_path = os.path.join(basedir, "match_results.json")
results_json = []

def truncate_text_smartly(text, max_length=1500):
    if len(text) <= max_length:
        return text
    
    sentences = sent_tokenize(text)
    
    if len(sentences) <= 1:
        return text[:max_length]
    

    start_portion = int(max_length * 0.7)  # 70% para o início
    end_portion = max_length - start_portion  # 30% para o fim
    
    current_length = 0
    start_sentences = []
    
    for sentence in sentences:
        if current_length + len(sentence) <= start_portion:
            start_sentences.append(sentence)
            current_length += len(sentence)
        else:
            break
    
    end_sentences = []
    remaining_length = max_length - current_length
    
    for sentence in reversed(sentences):
        if len(sentence) <= remaining_length:
            end_sentences.insert(0, sentence)
            remaining_length -= len(sentence)
        else:
            break
    
    if start_sentences and end_sentences and start_sentences[-1] != end_sentences[0]:
        result = "".join(start_sentences) + "\n[...]\n" + "".join(end_sentences)
    else:
        result = "".join(start_sentences)
        if len(result) < max_length and sentences[len(start_sentences):]:
            result += "\n[...]\n"
    
    return result

def extract_key_fields(obj, field_priorities):
    """
    Extrai campos específicos de um objeto com base em prioridades.
    
    Args:
        obj: Objeto com os dados (Job ou Applicant)
        field_priorities (list): Lista de tuplas (campo, prioridade, max_chars)
        
    Returns:
        str: Texto formatado com os campos extraídos
    """
    result = []
    
    for field, priority, max_chars in field_priorities:
        value = getattr(obj, field, None)
        if value:
            if max_chars > 0 and len(str(value)) > max_chars:
                value = truncate_text_smartly(str(value), max_chars)
            
            field_name = field.replace('_', ' ').title()
            result.append(f"{field_name}: {value}")
    
    return "\n".join(result)

def build_prompt(job, applicant):
    job_priorities = [
        ('titulo', 1, 100),
        ('cliente', 1, 100),
        ('objetivo_vaga', 1, 200),
        ('tipo_contratacao', 2, 100),
        ('nivel_profissional', 2, 100),
        ('nivel_academico', 2, 100),
        ('nivel_ingles', 3, 50),
        ('nivel_espanhol', 3, 50),
        ('atividades', 1, 400),
        ('competencias', 1, 400),
        ('cidade', 3, 50),
        ('estado', 3, 50),
        ('pais', 3, 50)
    ]
    
    job_description = extract_key_fields(job, job_priorities)
    
    if len(job_description) > 1500:
        job_description = truncate_text_smartly(job_description, 1500)
    
    applicant_priorities = [
        ('titulo_profissional', 1, 100),
        ('area_atuacao', 1, 100),
        ('nivel_academico', 2, 100),
        ('nivel_ingles', 2, 50),
        ('nivel_espanhol', 2, 50),
        ('conhecimentos_tecnicos', 1, 300),
        ('certificacoes', 2, 200),
        ('cv_pt', 1, 600)
    ]
    
    applicant_text = extract_key_fields(applicant, applicant_priorities)
    
    if len(applicant_text) > 1500:
        applicant_text = truncate_text_smartly(applicant_text, 1500)

    return f"""
Você é um analista de recrutamento senior, especializado em fazer triagem de curriculos e deve fazer uma triagem de currículos para saber se o candidato deve passar para a próxima fase do processo seletivo.

ID da vaga: {job.id}
ID do candidato: {applicant.id}

Com base na vaga abaixo:
{job_description}

E nas informações deste candidato:
{applicant_text}

Identifique o match do candidato com a vaga com base nessas informações, assim como traga as palavras-chave do currículo.

Sua resposta deve ser exclusivamente um JSON seguindo o seguinte exemplo:
{{
    "jobid": "{job.id}",
    "aplicantid": "{applicant.id}",
    "score": "87.5",
    "keywords": "Python, SQL, Teamwork, Ingles Fluente"
}}

SUA RESPOSTA DEVE CONTER APENAS O JSON NESTE FORMATO E NADA MAIS.
O CAMPO SCORE DEVE SER UM NÚMERO ENTRE 0 E 100 INDICANDO O MATCH ENTRE VAGA E CURRÍCULO.
O CAMPO KEYWORDS DEVE CONTER ALGUMAS PALAVRAS-CHAVE IDENTIFICADAS NO CURRÍCULO DO CANDIDATO.
"""

def try_parse_json(content):
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        try:
            fixed = re.sub(r"'", '"', content)
            return json.loads(fixed)
        except Exception:
            return None

with app.app_context():
    db.create_all()
    MatchResult.query.delete()

    preferred_job_ids = [
        100, 401, 728, 971, 972, 1123, 1426, 1813, 1530, 2417, 2420, 857,
        3124, 3345, 3840, 5984, 7142, 3175, 4153, 4735, 9265, 10148, 12328,
        12329, 12351, 2106, 7164, 9967, 9807, 7039
    ]

    subquery = (
        db.session.query(Prospect.job_id)
        .filter(Prospect.situacao.in_([
            "Contratado como Hunting",
            "Contratado pela Decision"
        ])).distinct()
    )
    vagas_abertas_query = Job.query.filter(~Job.id.in_(subquery))

    preferred_jobs = vagas_abertas_query.filter(Job.id.in_(preferred_job_ids)).all()
    preferred_job_ids_valid = [job.id for job in preferred_jobs]

    all_other_jobs = vagas_abertas_query.filter(~Job.id.in_(preferred_job_ids_valid)).all()
    other_jobs = random.sample(all_other_jobs, min(30, len(all_other_jobs)))

    vagas_abertas = preferred_jobs + other_jobs
    print(f"Usando {len(preferred_jobs)} vagas da lista fornecida e {len(other_jobs)} aleatórias.")

    total = 0

    for job in vagas_abertas:
        prospects = Prospect.query.filter_by(job_id=job.id).limit(5).all()
        print(f"🔍 Processando vaga {job.id} com {len(prospects)} candidatos...")

        for p in prospects:
            applicant = db.session.get(Applicant, p.applicant_id)
            if not applicant:
                continue

            prompt = build_prompt(job, applicant)
            try:
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=300
                )

                content = response.choices[0].message.content.strip()
                print("GPT:", content)

                json_data = try_parse_json(content)
                if not json_data:
                    print(f"Erro ao fazer parsing do JSON:\n{content}")
                    continue

                score_str = str(json_data["score"]).replace(",", ".")
                score = float(score_str)

                match = MatchResult(
                    job_id=int(json_data["jobid"]),
                    applicant_id=int(json_data["aplicantid"]),
                    score=score,
                    keywords=json_data["keywords"]
                )
                db.session.add(match)

                # Salva no JSON de saída
                results_json.append({
                    "job_id": match.job_id,
                    "applicant_id": match.applicant_id,
                    "score": match.score,
                    "keywords": match.keywords
                })

                # Salva incrementalmente em arquivo
                with open(output_json_path, "w", encoding="utf-8") as f:
                    json.dump(results_json, f, indent=2, ensure_ascii=False)

                total += 1

            except Exception as e:
                print(f"Erro com job {job.id}, applicant {applicant.id}: {str(e)}")
                continue

            time.sleep(1.2)  # respeita o rate limit da OpenAI

    db.session.commit()
    print(f"✅ {total} resultados salvos com sucesso.")
