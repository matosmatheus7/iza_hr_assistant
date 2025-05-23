from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Job(db.Model):
    __tablename__ = 'jobs'
    id = db.Column(db.String, primary_key=True)
    titulo = db.Column(db.String)
    modalidade = db.Column(db.String)

    # Informações básicas
    cliente = db.Column(db.String)
    requisitante = db.Column(db.String)
    analista_responsavel = db.Column(db.String)
    tipo_contratacao = db.Column(db.String)
    prazo_contratacao = db.Column(db.String)
    objetivo_vaga = db.Column(db.String)
    prioridade_vaga = db.Column(db.String)
    origem_vaga = db.Column(db.String)

    # Perfil da vaga
    pais = db.Column(db.String)
    estado = db.Column(db.String)
    cidade = db.Column(db.String)
    nivel_profissional = db.Column(db.String)
    nivel_academico = db.Column(db.String)
    nivel_ingles = db.Column(db.String)
    nivel_espanhol = db.Column(db.String)
    atividades = db.Column(db.Text)
    competencias = db.Column(db.Text)

    # Benefícios
    valor_venda = db.Column(db.String)
    valor_compra_1 = db.Column(db.String)
    valor_compra_2 = db.Column(db.String)


class Applicant(db.Model):
    __tablename__ = 'applicants'
    id = db.Column(db.String, primary_key=True)
    nome = db.Column(db.String)
    email = db.Column(db.String)
    telefone = db.Column(db.String)

    # Informações adicionais
    titulo_profissional = db.Column(db.String)
    area_atuacao = db.Column(db.String)
    conhecimentos_tecnicos = db.Column(db.Text)
    certificacoes = db.Column(db.Text)
    nivel_ingles = db.Column(db.String)
    nivel_espanhol = db.Column(db.String)
    nivel_academico = db.Column(db.String)

    cv_pt = db.Column(db.Text)


class Prospect(db.Model):
    __tablename__ = 'prospects'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    job_id = db.Column(db.String, db.ForeignKey('jobs.id'))
    applicant_id = db.Column(db.String, db.ForeignKey('applicants.id'))
    nome = db.Column(db.String)
    situacao = db.Column(db.String)
    comentario = db.Column(db.Text)
    data_candidatura = db.Column(db.String)
    ultima_atualizacao = db.Column(db.String)
    recrutador = db.Column(db.String)


class MatchResult(db.Model):
    __tablename__ = 'match_results'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    job_id = db.Column(db.String, db.ForeignKey('jobs.id'))
    applicant_id = db.Column(db.String, db.ForeignKey('applicants.id'))
    score = db.Column(db.Float)
    keywords = db.Column(db.Text)


class InterviewRecord(db.Model):
    __tablename__ = 'interviewrecord'
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(20))
    applicant_id = db.Column(db.String(20))
    questions = db.Column(db.Text)
    answers = db.Column(db.Text)
    summary = db.Column(db.Text)
    score = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class HRInterview(db.Model):
    __tablename__ = 'HRInterview'
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(20))
    applicant_id = db.Column(db.String(20))
    notes = db.Column(db.Text)
    status = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class TryItUser(db.Model):
    __tablename__ = "tryit_users"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String)
    job_id = db.Column(db.String, db.ForeignKey("jobs.id"))
    score = db.Column(db.Float)
    keywords = db.Column(db.Text)
    resumo = db.Column(db.Text)
    nota = db.Column(db.Integer)
    data = db.Column(db.DateTime, default=datetime.utcnow)
