import json
from flask import Flask
from db.database import db, Job, Applicant, Prospect
import os

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, "data", "appdata.db")

app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()

    # Carrega os arquivos
    with open("json_files/vagas.json", encoding="utf-8") as f:
        vagas_json = json.load(f)

    with open("json_files/applicants.json", encoding="utf-8") as f:
        applicants_json = json.load(f)

    with open("json_files/prospects.json", encoding="utf-8") as f:
        prospects_json = json.load(f)

    # Importa Jobs
    for job_id, vaga in vagas_json.items():
        info = vaga.get("informacoes_basicas", {})
        perfil = vaga.get("perfil_vaga", {})
        beneficios = vaga.get("beneficios", {})

        job = Job(
            id=job_id,
            titulo=info.get("titulo_vaga", ""),
            modalidade=vaga.get("modalidade", ""),
            cliente=info.get("cliente", ""),
            requisitante=info.get("requisitante", ""),
            analista_responsavel=info.get("analista_responsavel", ""),
            tipo_contratacao=info.get("tipo_contratacao", ""),
            prazo_contratacao=info.get("prazo_contratacao", ""),
            objetivo_vaga=info.get("objetivo_vaga", ""),
            prioridade_vaga=info.get("prioridade_vaga", ""),
            origem_vaga=info.get("origem_vaga", ""),
            pais=perfil.get("pais", ""),
            estado=perfil.get("estado", ""),
            cidade=perfil.get("cidade", ""),
            nivel_profissional=perfil.get("nivel profissional", ""),
            nivel_academico=perfil.get("nivel_academico", ""),
            nivel_ingles=perfil.get("nivel_ingles", ""),
            nivel_espanhol=perfil.get("nivel_espanhol", ""),
            atividades=perfil.get("principais_atividades", ""),
            competencias=perfil.get("competencia_tecnicas_e_comportamentais", ""),
            valor_venda=beneficios.get("valor_venda", ""),
            valor_compra_1=beneficios.get("valor_compra_1", ""),
            valor_compra_2=beneficios.get("valor_compra_2", "")
        )
        db.session.merge(job)

    # Importa Applicants com mais campos
    for applicant_id, dados in applicants_json.items():
        info_basicas = dados.get("infos_basicas", {})
        info_pessoais = dados.get("informacoes_pessoais", {})
        info_profissionais = dados.get("informacoes_profissionais", {})
        formacao = dados.get("formacao_e_idiomas", {})

        a = Applicant(
            id=applicant_id,
            nome=info_pessoais.get("nome", ""),
            email=info_pessoais.get("email", ""),
            telefone=info_pessoais.get("telefone_celular", ""),
            titulo_profissional=info_profissionais.get("titulo_profissional", ""),
            area_atuacao=info_profissionais.get("area_atuacao", ""),
            conhecimentos_tecnicos=info_profissionais.get("conhecimentos_tecnicos", ""),
            certificacoes=info_profissionais.get("certificacoes", ""),
            nivel_ingles=formacao.get("nivel_ingles", ""),
            nivel_espanhol=formacao.get("nivel_espanhol", ""),
            nivel_academico=formacao.get("nivel_academico", ""),
            cv_pt=dados.get("cv_pt", "")
        )
        db.session.merge(a)


    # Importa Prospects com mais campos
    for job_id, vaga in prospects_json.items():
        for p in vaga.get("prospects", []):
            prospect = Prospect(
                job_id=job_id,
                applicant_id=p["codigo"],
                nome=p.get("nome", ""),
                situacao=p.get("situacao_candidado", ""),
                comentario=p.get("comentario", ""),
                data_candidatura=p.get("data_candidatura", ""),
                ultima_atualizacao=p.get("ultima_atualizacao", ""),
                recrutador=p.get("recrutador", "")
            )
            db.session.add(prospect)

    db.session.commit()
    print("✅ Dados importados com sucesso!")
