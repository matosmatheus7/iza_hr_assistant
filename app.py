from flask import Flask, render_template, request, jsonify, redirect, flash, url_for
from werkzeug.utils import secure_filename
from datetime import datetime
import json
import os
import subprocess
from models.ai_agents import agente_avaliar_entrevista, agente_entrevistador, agente_triagem_cvs
from utils.tts import speak
from utils.stt import listen
from sqlalchemy.sql import exists

from db.database import db, Job, Applicant, Prospect, InterviewRecord, MatchResult, TryItUser, HRInterview
import fitz 

def extract_text_from_pdf(filepath):
    text = ""
    try:
        with fitz.open(filepath) as doc:
            for page in doc:
                text += page.get_text()
    except Exception as e:
        print(f"Erro ao extrair texto do PDF: {e}")
    return text.strip()

app = Flask(__name__, static_folder="static", template_folder="templates")
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, "data", "appdata.db")
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, "uploads")
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()

#############################################
############### ROTAS FUNÇÕES ###############
#############################################

@app.route("/speak", methods=["POST"])
def speak_text():
    data = request.get_json()
    text = data.get("text", "")
    if text:
        audio_path = speak(text)
        return jsonify({"status": "ok", "audio_url": audio_path})
    return jsonify({"error": "Texto vazio"}), 400

@app.route("/transcribe", methods=["POST"])
def transcribe():
    """
    Endpoint simplificado para transcrição de áudio.
    Recebe áudio WAV diretamente do cliente, sem necessidade de conversão com ffmpeg.
    """
    try:
        # Verificar se o arquivo de áudio foi enviado
        if 'audio' not in request.files:
            return jsonify({"error": "Nenhum arquivo de áudio enviado"}), 400
            
        file = request.files["audio"]
        if file.filename == '':
            return jsonify({"error": "Nome de arquivo vazio"}), 400
            
        # Garantir que os diretórios existam
        os.makedirs("audio", exist_ok=True)
        
        # Definir caminho do arquivo
        audio_path = os.path.join("audio", "user_input.wav")
        
        # Salvar o arquivo de áudio recebido
        try:
            file.save(audio_path)
            print(f"Arquivo de áudio salvo em: {audio_path}")
        except Exception as e:
            print(f"Erro ao salvar arquivo de áudio: {str(e)}")
            return jsonify({"error": "Erro ao salvar arquivo de áudio", "details": str(e)}), 500
        
        # Transcrever o áudio
        try:
            text = listen(audio_path)
            print("Transcrição concluída com sucesso")
            return jsonify({"text": text})
            
        except Exception as e:
            import traceback
            print(f"Erro ao transcrever áudio: {str(e)}")
            print(traceback.format_exc())
            return jsonify({
                "error": "Erro ao transcrever áudio", 
                "details": str(e)
            }), 500
            
    except Exception as e:
        import traceback
        print(f"Erro geral na transcrição: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            "error": "Erro geral na transcrição", 
            "details": str(e)
        }), 500


@app.route("/resumo", methods=["POST"])
def resumo():
    data = request.json
    questions = data.get("questions", [])
    responses = data.get("responses", [])
    job_id = data.get("job_id")
    applicant_id = data.get("applicant_id")

    summary, score = agente_avaliar_entrevista(questions, responses)

    if applicant_id.startswith("tryit-"):
        user_id = int(applicant_id.split("-")[1])
        tryit_user = TryItUser.query.get(user_id)
        tryit_user.resumo = summary
        tryit_user.nota = score
        db.session.commit()

        return jsonify({
            "summary": summary,
            "score": score
        })

    record = InterviewRecord.query.filter_by(job_id=job_id, applicant_id=applicant_id).first()
    if not record:
        record = InterviewRecord(job_id=job_id, applicant_id=applicant_id)

    record.questions = json.dumps(questions, ensure_ascii=False)
    record.answers = json.dumps(responses, ensure_ascii=False)
    record.summary = summary
    record.score = score

    db.session.add(record)
    db.session.commit()

    return jsonify({
        "summary": summary,
        "score": score
    })

#############################################
############### ROTAS API  ###############
#############################################

@app.route("/api/triagem", methods=["GET"])
def api_triagem():
    recrutador = request.args.get("recrutador")

    query = db.session.query(
        MatchResult.job_id,
        MatchResult.applicant_id,
        Job.titulo,
        Applicant.nome,
        MatchResult.score,
        Prospect.recrutador
    ).join(Job, Job.id == MatchResult.job_id)\
     .join(Applicant, Applicant.id == MatchResult.applicant_id)\
     .join(Prospect, db.and_(
         Prospect.applicant_id == MatchResult.applicant_id,
         Prospect.job_id == MatchResult.job_id
     ))\
     .filter(~Job.id.in_(
         db.session.query(Prospect.job_id)
         .filter(Prospect.situacao.in_([
             "Contratado como Hunting",
             "Contratado pela Decision"
         ]))
     ))\
     .filter(~exists().where(
         db.and_(
             InterviewRecord.job_id == MatchResult.job_id,
             InterviewRecord.applicant_id == MatchResult.applicant_id
         )
     ))

    if recrutador:
        query = query.filter(Prospect.recrutador == recrutador)

    results = query.all()

    data = [{
        "job_id": r.job_id,
        "applicant_id": r.applicant_id,
        "titulo": r.titulo,
        "nome": r.nome,
        "score": r.score,
        "recrutador": r.recrutador
    } for r in results]

    return jsonify(data)


@app.route("/api/recrutadores", methods=["GET"])
def api_recrutadores():
    subquery = db.session.query(
        Prospect.recrutador
    ).join(MatchResult, db.and_(
        Prospect.applicant_id == MatchResult.applicant_id,
        Prospect.job_id == MatchResult.job_id
    )).filter(~Prospect.situacao.in_([
        "Contratado como Hunting",
        "Contratado pela Decision"
    ])).distinct()

    recrutadores = [r[0] for r in subquery if r[0]]
    return jsonify(recrutadores)

@app.route("/api/candidatos_por_vaga/<job_id>")
def api_candidatos_por_vaga(job_id):
    """
    Endpoint que retorna todos os candidatos (prospects) inscritos para uma vaga específica.
    Usado para popular o select de candidatos no formulário de entrevista.
    """
    try:
        # Verifica se a vaga existe
        job = Job.query.get(job_id)
        if not job:
            return jsonify({"error": "Vaga não encontrada"}), 404
        
        # Busca os prospects (candidatos) para esta vaga
        prospects = db.session.query(
            Prospect.applicant_id,
            Applicant.nome,
            Applicant.email,
            Applicant.titulo_profissional
        ).join(
            Applicant, Applicant.id == Prospect.applicant_id
        ).filter(
            Prospect.job_id == job_id,
            # Exclui candidatos já contratados ou em situações finais
            ~Prospect.situacao.in_(["Contratado como Hunting", "Contratado pela Decision"])
        ).all()
        
        # Formata os dados para o frontend
        data = [{
            "id": p.applicant_id,
            "nome": p.nome,
            "email": p.email,
            "titulo": p.titulo_profissional or ""
        } for p in prospects]
        
        return jsonify(data)
    except Exception as e:
        app.logger.error(f"Erro ao buscar candidatos por vaga: {str(e)}")
        return jsonify({"error": "Erro ao buscar candidatos"}), 500


@app.route("/api/vagas_fechadas", methods=["GET"])
def api_vagas_fechadas():
    fechamento = ["Contratado como Hunting", "Contratado pela Decision"]
    results = db.session.query(
        Prospect.job_id,
        Prospect.applicant_id,
        Job.titulo,
        Applicant.nome,
        Prospect.recrutador,
        Prospect.situacao
    ).join(Job, Job.id == Prospect.job_id) \
     .join(Applicant, Applicant.id == Prospect.applicant_id) \
     .filter(Prospect.situacao.in_(fechamento)) \
     .limit(100) \
     .all()

    data = [{
        "job_id": r.job_id,
        "applicant_id": r.applicant_id,
        "titulo": r.titulo,
        "nome": r.nome,
        "recrutador": r.recrutador,
        "situacao": r.situacao
    } for r in results]

    return jsonify(data)

@app.route("/api/detalhes/<job_id>/<applicant_id>")
def api_detalhes(job_id, applicant_id):
    job = Job.query.get(job_id)
    applicant = Applicant.query.get(applicant_id)
    match = MatchResult.query.filter_by(job_id=job_id, applicant_id=applicant_id).first()
    interview = InterviewRecord.query.filter_by(job_id=job_id, applicant_id=applicant_id).first()
    hr_interview = HRInterview.query.filter_by(job_id=job_id, applicant_id=applicant_id).first()

    if not job or not applicant:
        return jsonify({"error": "Dados não encontrados"}), 404

    return jsonify({
        "job": {
            "titulo": job.titulo,
            "cliente": job.cliente,
            "cidade": job.cidade,
            "estado": job.estado,
            "pais": job.pais,
            "tipo_contratacao": job.tipo_contratacao,
            "atividades": job.atividades,
            "competencias": job.competencias
        },
        "applicant": {
            "nome": applicant.nome,
            "email": applicant.email,
            "telefone": applicant.telefone,
            "titulo_profissional": applicant.titulo_profissional,
            "area_atuacao": applicant.area_atuacao,
            "cv": applicant.cv_pt
        },
        "match": {
            "score": match.score if match else None,
            "keywords": match.keywords if match else None
        },
        "interview": {
            "score": interview.score if interview else None,
            "summary": interview.summary if interview else None
        },
        "hr_interview": {
            "status": hr_interview.status if hr_interview else None,
            "notes": hr_interview.notes if hr_interview else None,
            "created_at": hr_interview.created_at.strftime("%d/%m/%Y %H:%M") if hr_interview and hr_interview.created_at else None
        }
    })


@app.route("/api/entrevistas_chatbot", methods=["GET"])
def api_entrevistas_chatbot():
    entrevistas = db.session.query(
        InterviewRecord.job_id,
        InterviewRecord.applicant_id,
        InterviewRecord.score,
        InterviewRecord.summary,
        Job.titulo,
        Applicant.nome
    ).join(Job, Job.id == InterviewRecord.job_id) \
     .join(Applicant, Applicant.id == InterviewRecord.applicant_id) \
     .filter(~exists().where(
         db.and_(
             HRInterview.job_id == InterviewRecord.job_id,
             HRInterview.applicant_id == InterviewRecord.applicant_id
         )
     ))

    data = [{
        "job_id": e.job_id,
        "applicant_id": e.applicant_id,
        "titulo": e.titulo,
        "nome": e.nome,
        "score": e.score,
        "summary": e.summary
    } for e in entrevistas]

    return jsonify(data)

@app.route("/api/hr-entrevistas_chatbot", methods=["GET"])
def api_hr_entrevistas_chatbot(): 
    entrevistas = db.session.query(
        HRInterview.job_id,
        HRInterview.applicant_id,
        HRInterview.status,
        HRInterview.notes,
        Job.titulo,
        Applicant.nome,
        MatchResult.score.label("match_score"),
        InterviewRecord.score.label("chatbot_score")
    ).join(Job, Job.id == HRInterview.job_id) \
     .join(Applicant, Applicant.id == HRInterview.applicant_id) \
     .outerjoin(MatchResult, (MatchResult.job_id == HRInterview.job_id) & (MatchResult.applicant_id == HRInterview.applicant_id)) \
     .outerjoin(InterviewRecord, (InterviewRecord.job_id == HRInterview.job_id) & (InterviewRecord.applicant_id == HRInterview.applicant_id)) \
     .all()

    data = [{
        "job_id": e.job_id,
        "applicant_id": e.applicant_id,
        "titulo": e.titulo,
        "nome": e.nome,
        "match_score": e.match_score,
        "chatbot_score": e.chatbot_score,
        "status": e.status,
        "notes": e.notes
    } for e in entrevistas]

    return jsonify(data)


@app.route("/api/next_question", methods=["POST"])
def api_next_question():
    data = request.get_json()

    job_id = data.get("job_id")
    applicant_id = data.get("applicant_id")
    history = data.get("history", [])

    if not job_id or not applicant_id:
        return jsonify({"error": "job_id e applicant_id são obrigatórios"}), 400

    job = Job.query.get(job_id)
    if not job:
        return jsonify({"error": "Vaga não encontrada"}), 404

    if applicant_id.startswith("tryit-"):
        user_id = applicant_id.split("-")[1]
        applicant = TryItUser.query.get(user_id)
    else:
        applicant = Applicant.query.get(applicant_id)

    if not applicant:
        return jsonify({"error": "Candidato não encontrado"}), 404

    job_dict = {
        "informacoes_basicas": {
            "titulo_vaga": job.titulo,
            "cliente": job.cliente,
            "objetivo_vaga": job.objetivo_vaga,
            "tipo_contratacao": job.tipo_contratacao,
        },
        "perfil_vaga": {
            "nivel_profissional": job.nivel_profissional,
            "nivel_academico": job.nivel_academico,
            "nivel_ingles": job.nivel_ingles,
            "nivel_espanhol": job.nivel_espanhol,
            "principais_atividades": job.atividades,
            "competencia_tecnicas_e_comportamentais": job.competencias,
        }
    }

    applicant_dict = {
        "nome": applicant.nome,
        "area_atuacao": getattr(applicant, "area_atuacao", ""),
        "conhecimentos_tecnicos": getattr(applicant, "conhecimentos_tecnicos", ""),
        "certificacoes": getattr(applicant, "certificacoes", ""),
        "nivel_ingles": getattr(applicant, "nivel_ingles", ""),
        "nivel_espanhol": getattr(applicant, "nivel_espanhol", ""),
        "nivel_academico": getattr(applicant, "nivel_academico", ""),
        "cv_pt": getattr(applicant, "cv_pt", getattr(applicant, "keywords", "")) 
    }

    history_pairs = [
        (h["question"], h["answer"])
        for h in history if isinstance(h, dict) and h.get("question") and h.get("answer")
    ]

    try:
        next_question = agente_entrevistador(job_dict, applicant_dict, history_pairs)
        return jsonify({"question": next_question})
    except Exception as e:
        return jsonify({"error": "Erro ao gerar pergunta", "details": str(e)}), 500

@app.route("/api/vagas_abertas")
def api_vagas_abertas():
    vagas = db.session.query(Job).filter(
        ~Job.id.in_(
            db.session.query(Prospect.job_id).filter(
                Prospect.situacao.in_([
                    "Contratado como Hunting", "Contratado pela Decision"
                ])
            )
        )
    ).all()

    data = [{
        "id": v.id,
        "titulo": v.titulo or "",
        "cliente": v.cliente or "",
        "tipo": v.tipo_contratacao or "",
        "local": f"{v.cidade or ''}, {v.estado or ''}, {v.pais or ''}"
    } for v in vagas]

    return jsonify(data)

@app.route("/api/vaga_detalhe/<id>")
def api_vaga_detalhe(id):
    vaga = Job.query.get(id)
    if not vaga:
        return jsonify({"error": "Vaga não encontrada"}), 404

    return jsonify({
        "id": vaga.id,
        "titulo": vaga.titulo,
        "cliente": vaga.cliente,
        "tipo_contratacao": vaga.tipo_contratacao,
        "objetivo_vaga": vaga.objetivo_vaga,
        "atividades": vaga.atividades,
        "competencias": vaga.competencias,
        "cidade": vaga.cidade,
        "estado": vaga.estado,
        "pais": vaga.pais
    })




@app.route("/api/save_rh_feedback", methods=["POST"])
def save_rh_feedback():
    data = request.get_json()
    job_id = data.get("job_id")
    applicant_id = data.get("applicant_id")
    notes = data.get("notes")
    status = data.get("status")

    if not all([job_id, applicant_id, status]):
        return jsonify({"error": "Dados incompletos"}), 400

    feedback = HRInterview(
        job_id=job_id,
        applicant_id=applicant_id,
        notes=notes,
        status=status,
        created_at=datetime.utcnow()
    )
    db.session.add(feedback)
    db.session.commit()

    return jsonify({"message": "Feedback salvo com sucesso"}), 200

#############################################
############### ROTAS PAGINAS  ###############
#############################################

@app.route("/SimulacaoEntrevista", methods=["GET", "POST"])
def interview():
    if request.method == "POST":
        job_id = request.form["job_id"]
        applicant_id = request.form["applicant_id"]

        job = Job.query.get(job_id)
        applicant = Applicant.query.get(applicant_id)

        if not job or not applicant:
            return "Vaga ou candidato não encontrado", 404

        match = MatchResult.query.filter_by(job_id=job_id, applicant_id=applicant_id).first()

        if not match:
            job_dict = {
                "informacoes_basicas": {
                    "titulo_vaga": job.titulo,
                    "cliente": job.cliente,
                    "objetivo_vaga": job.objetivo_vaga,
                    "tipo_contratacao": job.tipo_contratacao
                },
                "perfil_vaga": {
                    "nivel_profissional": job.nivel_profissional,
                    "nivel_academico": job.nivel_academico,
                    "nivel_ingles": job.nivel_ingles,
                    "nivel_espanhol": job.nivel_espanhol,
                    "principais_atividades": job.atividades,
                    "competencia_tecnicas_e_comportamentais": job.competencias
                }
            }

            applicant_cv = applicant.cv_pt or ""
            result_json = agente_triagem_cvs(job_dict, applicant_cv)
            result = json.loads(result_json)

            match = MatchResult(
                job_id=job_id,
                applicant_id=applicant_id,
                score=result.get("score"),
                keywords=result.get("keywords")
            )
            db.session.add(match)
            db.session.commit()

        return render_template("interview.html", job_id=job_id, applicant_id=applicant_id)

    return render_template("interview.html", job_id=None, applicant_id=None)

@app.route("/showdata")
def listar_tryit():
    tryit_users = TryItUser.query.order_by(TryItUser.data.desc()).all()
    return render_template("show.html", usuarios=tryit_users)

@app.route("/Homepage")
def homepage():
    return render_template("dash.html")

@app.route("/Doc")
def doc():
    return render_template("doc.html")

@app.route("/tryit/apply/<job_id>", methods=["GET", "POST"])
def tryit_apply(job_id):
    job = Job.query.get(job_id)
    if not job:
        return "Vaga não encontrada", 404

    if request.method == "POST":
        arquivo = request.files["cv"]

        if not arquivo:
            flash("Currículo é obrigatório para seguir para a próxima etapa.")
            return redirect(request.url)

        filename = secure_filename(arquivo.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        arquivo.save(filepath)

        cv_text = extract_text_from_pdf(filepath)

        job_dict = {
            "informacoes_basicas": {
                "titulo_vaga": job.titulo,
                "cliente": job.cliente,
                "objetivo_vaga": job.objetivo_vaga,
                "tipo_contratacao": job.tipo_contratacao,
            },
            "perfil_vaga": {
                "nivel_profissional": job.nivel_profissional,
                "nivel_academico": job.nivel_academico,
                "nivel_ingles": job.nivel_ingles,
                "nivel_espanhol": job.nivel_espanhol,
                "principais_atividades": job.atividades,
                "competencia_tecnicas_e_comportamentais": job.competencias,
            }
        }

        result = agente_triagem_cvs(job_dict, cv_text)
        parsed = json.loads(result)

        entry = TryItUser(
            nome=parsed.get("nome"),
            job_id=job.id,
            score=parsed.get("score"),
            keywords=parsed.get("keywords"),
        )
        db.session.add(entry)
        db.session.commit()

        return redirect(url_for("tryit_interview", job_id=job.id, user_id=entry.id))

    return render_template("tryit_form.html", job=job)


@app.route("/tryit/interview", methods=["GET"])
def tryit_interview():
    job_id = request.args.get("job_id")
    user_id = request.args.get("user_id")

    job = Job.query.get(job_id)
    tryit_user = TryItUser.query.get(user_id)

    if not job or not tryit_user:
        return "Dados não encontrados", 404

    return render_template("interview.html",
                           job_id=job_id,
                           applicant_id=f"tryit-{user_id}",
                           modo_tryit=True,
                           tryit_score=tryit_user.score,
                           tryit_keywords=tryit_user.keywords,
                           tryit_nome=tryit_user.nome,
                           job_titulo=job.titulo)


@app.route("/tryit/result/<int:user_id>")
def tryit_result(user_id):
    user = TryItUser.query.get(user_id)
    job = Job.query.get(user.job_id) if user else None
    return render_template("tryit_result.html", match=user, job=job)

@app.route("/tryit")
def try_it_yourself():
    return render_template("tryit.html")

if __name__ == "__main__":
    app.run(debug=True)
