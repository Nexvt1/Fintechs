import subprocess
import sys

# Lista de pacotes necessários para a aplicação
REQUERIMENTOS = [
    'Flask',
    'Flask-SQLAlchemy',
    'python-dotenv',
    'requests',
    'psycopg2-binary',
    'Werkzeug'
]

def instalar_dependencias():
    """Verifica e instala automaticamente dependências ausentes antes de iniciar."""
    for pacote in REQUERIMENTOS:
        try:
            nome_modulo = pacote.lower().replace('-', '_')
            if nome_modulo == 'flask_sqlalchemy':
                import flask_sqlalchemy
            elif nome_modulo == 'python_dotenv':
                import dotenv
            elif nome_modulo == 'psycopg2_binary':
                import psycopg2
            else:
                __import__(nome_modulo)
        except ImportError:
            print(f"-> Instalando biblioteca ausente: {pacote}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pacote])

# Executa a verificação/instalação
instalar_dependencias()

# --- IMPORTS DO PROJETO ---
import os
import uuid
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

app = Flask(__name__)

# --- CONFIGURAÇÃO DA CHAVE SECRETA E SESSÃO PERMANENTE ---
app.secret_key = os.getenv('SECRET_KEY', 'chave_padrao_caso_nao_encontre')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# --- CONFIGURAÇÃO DO BANCO DE DADOS (SUPABASE / POSTGRESQL) ---
db_url = os.getenv('DATABASE_URL')
if db_url and db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Desativar cache do navegador durante o desenvolvimento
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response

# --- CONFIGURAÇÃO DE UPLOAD DE ARQUIVOS ---
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # Limite de 50MB

# --- INICIALIZAÇÃO DAS TABELAS NO SUPABASE ---
def init_db():
    with app.app_context():
        # Tabela de relatos
        db.session.execute(text('''
            CREATE TABLE IF NOT EXISTS relatos (
                id SERIAL PRIMARY KEY,
                protocolo TEXT UNIQUE NOT NULL,
                mensagem TEXT NOT NULL,
                categoria TEXT DEFAULT 'Geral',
                status TEXT DEFAULT 'Em análise',
                empregado TEXT,
                empresa_fato TEXT,
                diretoria TEXT,
                filial TEXT,
                cidade TEXT,
                area_setor TEXT,
                evidencias TEXT,
                chefia_ciente TEXT,
                chefia_envolvida TEXT,
                tentativa_ocultar TEXT,
                testemunhas TEXT,
                valor_financeiro TEXT,
                sugestao_solucao TEXT,
                anexos TEXT,
                identificacao TEXT,
                relator_nome TEXT,
                relator_email TEXT,
                relator_celular TEXT,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        '''))
        
        # Tabela de Usuários atualizada para coincidir com o Supabase
        db.session.execute(text('''
            CREATE TABLE IF NOT EXISTS "Usuarios" (
                id SERIAL PRIMARY KEY,
                nome TEXT,
                email TEXT UNIQUE NOT NULL,
                senha_hash TEXT,
                tipo TEXT DEFAULT 'usuario',
                modo_anonimo_padrao BOOLEAN DEFAULT FALSE,
                notificar_status BOOLEAN DEFAULT TRUE,
                tema TEXT DEFAULT 'claro',
                saldo NUMERIC DEFAULT 1500.00,
                investimentos NUMERIC DEFAULT 3200.00
            )
        '''))

        # Garante que as colunas saldo e investimentos existem
        try:
            db.session.execute(text('ALTER TABLE "Usuarios" ADD COLUMN IF NOT EXISTS saldo NUMERIC DEFAULT 1500.00'))
            db.session.execute(text('ALTER TABLE "Usuarios" ADD COLUMN IF NOT EXISTS investimentos NUMERIC DEFAULT 3200.00'))
            db.session.execute(text('UPDATE "Usuarios" SET saldo = 1500.00 WHERE saldo IS NULL'))
            db.session.execute(text('UPDATE "Usuarios" SET investimentos = 3200.00 WHERE investimentos IS NULL'))
            db.session.commit()
        except Exception:
            db.session.rollback()

        # Garante usuário administrador padrão (admin@fistu.com / admin123)
        try:
            admin_check = db.session.execute(text("SELECT id FROM \"Usuarios\" WHERE tipo = 'admin'")).fetchone()
            if not admin_check:
                db.session.execute(text('''
                    INSERT INTO "Usuarios" (nome, email, senha_hash, tipo, saldo, investimentos)
                    VALUES ('Administrador', 'admin@fistu.com', :senha, 'admin', 50000.00, 120000.00)
                '''), {'senha': generate_password_hash('admin123')})
                db.session.commit()
        except Exception:
            db.session.rollback()

        db.session.execute(text('''
            CREATE TABLE IF NOT EXISTS mensagens_chat (
                id SERIAL PRIMARY KEY,
                usuario_email TEXT NOT NULL,
                usuario_nome TEXT,
                mensagem TEXT NOT NULL,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        '''))
        
        db.session.commit()

init_db()

# --- ROTAS DE CONFIGURAÇÕES DE USUÁRIO ---
@app.route('/configuracoes')
def configuracoes_aluno():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    usuario = db.session.execute(
        text('SELECT modo_anonimo_padrao, notificar_status, tema FROM "Usuarios" WHERE id = :id'),
        {'id': user_id}
    ).mappings().fetchone()

    return render_template('configuracoes_aluno.html', usuario=usuario)

@app.route('/salvar-configuracoes-aluno', methods=['POST'])
def salvar_configuracoes_aluno():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    anonimo = True if request.form.get('modo_anonimo_padrao') else False
    notificar = True if request.form.get('notificar_status') else False
    tema = request.form.get('tema', 'claro')

    db.session.execute(
        text('''
            UPDATE "Usuarios" 
            SET modo_anonimo_padrao = :anonimo, notificar_status = :notificar, tema = :tema
            WHERE id = :id
        '''),
        {'anonimo': anonimo, 'notificar': notificar, 'tema': tema, 'id': user_id}
    )
    db.session.commit()

    return redirect(url_for('configuracoes_aluno'))

# --- ROTAS DE INTERFACE (WEB) ---

@app.route('/card/bibliotecas')
def card_bibliotecas():
    return render_template('cards_templates/bibliotecas_conhecimento.html')

@app.route('/card/sobre')
def card_sobre():
    return render_template('cards_templates/sobre_nós.html')
 
@app.route('/')
def root():
    # Se o utilizador não estiver autenticado na sessão, vai para o login
    if 'usuario_email' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('home'))

@app.route('/home')
def home():
    if 'usuario_email' not in session:
        return redirect(url_for('login'))
        
    usuario_db = db.session.execute(
        text('SELECT id, nome, email, tipo, saldo, investimentos FROM "Usuarios" WHERE id = :id'),
        {'id': session.get('user_id')}
    ).mappings().fetchone()
    
    if not usuario_db:
        usuario_db = db.session.execute(
            text('SELECT id, nome, email, tipo, saldo, investimentos FROM "Usuarios" WHERE email = :email'),
            {'email': session.get('usuario_email')}
        ).mappings().fetchone()
        
    if not usuario_db:
        session.clear()
        return redirect(url_for('login'))
        
    session['user_id'] = usuario_db['id']
    session['usuario_nome'] = usuario_db['nome']
    session['usuario_tipo'] = usuario_db['tipo'] or 'usuario'
    
    return render_template('home.html', usuario=usuario_db)

# --- ROTAS DE ACESSO ADMINISTRATIVO ---
@app.route('/admin')
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'usuario_email' not in session:
        return redirect(url_for('admin_login'))
    if session.get('usuario_tipo') != 'admin':
        flash('Acesso restrito a administradores credenciados.')
        return redirect(url_for('home'))
        
    # Busca usuários cadastrados no banco
    usuarios = db.session.execute(
        text('SELECT id, nome, email, tipo, saldo, investimentos FROM "Usuarios" ORDER BY id ASC')
    ).mappings().fetchall()
    
    total_usuarios = len(usuarios)
    total_saldo = sum([float(u['saldo'] or 0) for u in usuarios])
    total_investimentos = sum([float(u['investimentos'] or 0) for u in usuarios])
    
    admin_info = {
        'nome': session.get('usuario_nome', 'Administrador'),
        'email': session.get('usuario_email', 'admin@fistu.com'),
        'total_usuarios': total_usuarios,
        'total_saldo': total_saldo,
        'total_investimentos': total_investimentos
    }
    
    return render_template('admin_dashboard.html', admin=admin_info, usuarios=usuarios)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'GET':
        if 'usuario_email' in session and session.get('usuario_tipo') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return render_template('admin_login.html')
        
    data = request.get_json(silent=True) or request.form
    login_val = (data.get('email') or data.get('login') or '').strip()
    senha = data.get('senha') or ''
    
    if not login_val or not senha:
        if request.is_json:
            return jsonify({'erro': 'E-mail/usuário e senha são obrigatórios.'}), 400
        flash('E-mail/usuário e senha são obrigatórios.')
        return redirect(url_for('admin_login'))
        
    usuario = db.session.execute(
        text('SELECT * FROM "Usuarios" WHERE email = :val OR nome = :val'),
        {'val': login_val}
    ).mappings().fetchone()
    
    if usuario and usuario['senha_hash'] and (check_password_hash(usuario['senha_hash'], senha) or usuario['senha_hash'] == senha):
        if usuario['tipo'] != 'admin':
            if request.is_json:
                return jsonify({'erro': 'Esta conta não possui privilégios de Administrador.'}), 403
            flash('Esta conta não possui privilégios de Administrador.')
            return redirect(url_for('admin_login'))
            
        session.permanent = True
        session['user_id'] = usuario['id']
        session['usuario_email'] = usuario['email']
        session['usuario_nome'] = usuario['nome']
        session['usuario_tipo'] = 'admin'
        
        if request.is_json:
            return jsonify({
                'mensagem': 'Acesso administrativo autorizado!',
                'redirect': url_for('admin_dashboard'),
                'user': {
                    'id': usuario['id'],
                    'nome': usuario['nome'],
                    'email': usuario['email'],
                    'tipo': 'admin'
                }
            }), 200
            
        flash('Acesso administrativo autorizado!')
        return redirect(url_for('admin_dashboard'))
    else:
        if request.is_json:
            return jsonify({'erro': 'Credenciais de administrador incorretas.'}), 401
        flash('Credenciais de administrador incorretas.')
        return redirect(url_for('admin_login'))

# --- APIS ADMINISTRATIVAS ---
@app.route('/api/admin/usuario/<int:uid>/tipo', methods=['POST'])
def api_admin_alterar_tipo(uid):
    if session.get('usuario_tipo') != 'admin':
        return jsonify({'erro': 'Não autorizado.'}), 403
    data = request.get_json(silent=True) or request.form
    novo_tipo = data.get('tipo', 'usuario')
    if novo_tipo not in ['admin', 'usuario']:
        return jsonify({'erro': 'Tipo inválido.'}), 400
    db.session.execute(
        text('UPDATE "Usuarios" SET tipo = :tipo WHERE id = :id'),
        {'tipo': novo_tipo, 'id': uid}
    )
    db.session.commit()
    return jsonify({'sucesso': True, 'mensagem': f'Tipo de usuário alterado para {novo_tipo}!'})

@app.route('/api/admin/usuario/<int:uid>/saldo', methods=['POST'])
def api_admin_alterar_saldo(uid):
    if session.get('usuario_tipo') != 'admin':
        return jsonify({'erro': 'Não autorizado.'}), 403
    data = request.get_json(silent=True) or request.form
    try:
        saldo = float(data.get('saldo', 0))
        investimentos = float(data.get('investimentos', 0))
    except (ValueError, TypeError):
        return jsonify({'erro': 'Valores numéricos inválidos.'}), 400
        
    db.session.execute(
        text('UPDATE "Usuarios" SET saldo = :saldo, investimentos = :inv WHERE id = :id'),
        {'saldo': saldo, 'inv': investimentos, 'id': uid}
    )
    db.session.commit()
    return jsonify({'sucesso': True, 'mensagem': 'Saldos atualizados com sucesso!'})

# --- APIS FINANCEIRAS DO USUÁRIO (SALDO E INVESTIMENTOS) ---
@app.route('/api/usuario/investir', methods=['POST'])
def api_usuario_investir():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'erro': 'Usuário não autenticado.'}), 401
        
    data = request.get_json(silent=True) or request.form
    try:
        valor = float(data.get('valor', 0))
    except (ValueError, TypeError):
        return jsonify({'erro': 'Valor inválido.'}), 400
        
    produto = data.get('produto', 'Super Caixinha CDI')
    
    if valor <= 0:
        return jsonify({'erro': 'O valor deve ser maior que zero.'}), 400
        
    usuario = db.session.execute(
        text('SELECT id, saldo, investimentos FROM "Usuarios" WHERE id = :id'),
        {'id': user_id}
    ).mappings().fetchone()
    
    if not usuario:
        return jsonify({'erro': 'Usuário não encontrado.'}), 404
        
    saldo_atual = float(usuario['saldo'] or 0)
    if saldo_atual < valor:
        return jsonify({'erro': f'Saldo insuficiente. Seu saldo é R$ {saldo_atual:.2f}'}), 400
        
    novo_saldo = saldo_atual - valor
    novos_investimentos = float(usuario['investimentos'] or 0) + valor
    
    db.session.execute(
        text('UPDATE "Usuarios" SET saldo = :saldo, investimentos = :inv WHERE id = :id'),
        {'saldo': novo_saldo, 'inv': novos_investimentos, 'id': user_id}
    )
    db.session.commit()
    
    return jsonify({
        'sucesso': True,
        'mensagem': f'Aporte de R$ {valor:.2f} realizado com sucesso em {produto}!',
        'saldo': novo_saldo,
        'investimentos': novos_investimentos
    }), 200

@app.route('/api/usuario/resgatar', methods=['POST'])
def api_usuario_resgatar():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'erro': 'Usuário não autenticado.'}), 401
        
    data = request.get_json(silent=True) or request.form
    try:
        valor = float(data.get('valor', 0))
    except (ValueError, TypeError):
        return jsonify({'erro': 'Valor inválido.'}), 400
        
    if valor <= 0:
        return jsonify({'erro': 'O valor deve ser maior que zero.'}), 400
        
    usuario = db.session.execute(
        text('SELECT id, saldo, investimentos FROM "Usuarios" WHERE id = :id'),
        {'id': user_id}
    ).mappings().fetchone()
    
    if not usuario:
        return jsonify({'erro': 'Usuário não encontrado.'}), 404
        
    inv_atual = float(usuario['investimentos'] or 0)
    if inv_atual < valor:
        return jsonify({'erro': f'Saldo em investimentos insuficiente. Total investido: R$ {inv_atual:.2f}'}), 400
        
    novos_investimentos = inv_atual - valor
    novo_saldo = float(usuario['saldo'] or 0) + valor
    
    db.session.execute(
        text('UPDATE "Usuarios" SET saldo = :saldo, investimentos = :inv WHERE id = :id'),
        {'saldo': novo_saldo, 'inv': novos_investimentos, 'id': user_id}
    )
    db.session.commit()
    
    return jsonify({
        'sucesso': True,
        'mensagem': f'Resgate de R$ {valor:.2f} efetuado para o seu saldo!',
        'saldo': novo_saldo,
        'investimentos': novos_investimentos
    }), 200

@app.route('/api/usuario/deposito', methods=['POST'])
def api_usuario_deposito():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'erro': 'Usuário não autenticado.'}), 401
        
    data = request.get_json(silent=True) or request.form
    try:
        valor = float(data.get('valor', 0))
    except (ValueError, TypeError):
        return jsonify({'erro': 'Valor inválido.'}), 400
        
    if valor <= 0:
        return jsonify({'erro': 'O valor de depósito deve ser maior que zero.'}), 400
        
    usuario = db.session.execute(
        text('SELECT id, saldo FROM "Usuarios" WHERE id = :id'),
        {'id': user_id}
    ).mappings().fetchone()
    
    if not usuario:
        return jsonify({'erro': 'Usuário não encontrado.'}), 404
        
    novo_saldo = float(usuario['saldo'] or 0) + valor
    db.session.execute(
        text('UPDATE "Usuarios" SET saldo = :saldo WHERE id = :id'),
        {'saldo': novo_saldo, 'id': user_id}
    )
    db.session.commit()
    
    return jsonify({
        'sucesso': True,
        'mensagem': f'Depósito de R$ {valor:.2f} creditado com sucesso!',
        'saldo': novo_saldo
    }), 200

@app.route('/api/usuario/pix', methods=['POST'])
def api_usuario_pix():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'erro': 'Usuário não autenticado.'}), 401
        
    data = request.get_json(silent=True) or request.form
    chave = (data.get('chave') or '').strip()
    try:
        valor = float(data.get('valor', 0))
    except (ValueError, TypeError):
        return jsonify({'erro': 'Valor inválido.'}), 400
        
    if not chave:
        return jsonify({'erro': 'Chave Pix é obrigatória.'}), 400
    if valor <= 0:
        return jsonify({'erro': 'O valor deve ser maior que zero.'}), 400
        
    usuario = db.session.execute(
        text('SELECT id, saldo FROM "Usuarios" WHERE id = :id'),
        {'id': user_id}
    ).mappings().fetchone()
    
    if not usuario:
        return jsonify({'erro': 'Usuário não encontrado.'}), 404
        
    saldo_atual = float(usuario['saldo'] or 0)
    if saldo_atual < valor:
        return jsonify({'erro': f'Saldo insuficiente para realizar este Pix. Saldo atual: R$ {saldo_atual:.2f}'}), 400
        
    novo_saldo = saldo_atual - valor
    db.session.execute(
        text('UPDATE "Usuarios" SET saldo = :saldo WHERE id = :id'),
        {'saldo': novo_saldo, 'id': user_id}
    )
    db.session.commit()
    
    return jsonify({
        'sucesso': True,
        'mensagem': f'Pix de R$ {valor:.2f} enviado com sucesso para {chave}!',
        'saldo': novo_saldo
    }), 200

@app.route('/api/usuario/educacao/concluir', methods=['POST'])
def api_usuario_educacao_concluir():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'erro': 'Usuário não autenticado.'}), 401
        
    data = request.get_json(silent=True) or request.form
    stage = data.get('stage', 1)
    level = data.get('level', 'Iniciante')
    bonus_reais = 5.00 # Bônus de aprendizado de R$ 5,00
    
    usuario = db.session.execute(
        text('SELECT id, saldo, investimentos FROM "Usuarios" WHERE id = :id'),
        {'id': user_id}
    ).mappings().fetchone()
    
    if not usuario:
        return jsonify({'erro': 'Usuário não encontrado.'}), 404
        
    novo_saldo = float(usuario['saldo'] or 0) + bonus_reais
    db.session.execute(
        text('UPDATE "Usuarios" SET saldo = :saldo WHERE id = :id'),
        {'saldo': novo_saldo, 'id': user_id}
    )
    db.session.commit()
    
    return jsonify({
        'sucesso': True,
        'mensagem': f'Parabéns! Stage {stage} ({level}) concluído! Bônus de R$ {bonus_reais:.2f} creditado no seu saldo!',
        'saldo': novo_saldo,
        'bonus': bonus_reais
    }), 200

@app.route('/index')
def index():
    return redirect(url_for('root'))

@app.route('/cadastro')
def tela_cadastro():
    return render_template('cadastro.html')

@app.route('/conta')
def conta():
    if 'usuario_email' not in session:
        return redirect(url_for('login'))
    
    total_relatos = db.session.execute(text("SELECT COUNT(*) FROM relatos")).scalar()

    return render_template('minhaconta.html', total_relatos=total_relatos)

@app.route('/relatos')
def relatos():
    if 'usuario_email' not in session:
        return redirect(url_for('login'))
        
    relatos_db = db.session.execute(text("SELECT * FROM relatos ORDER BY id DESC")).mappings().fetchall()
    
    return render_template('Index.html', relatos=relatos_db)

@app.route('/novo-relato')
def novo_relato():
    if 'usuario_email' not in session:
        return redirect(url_for('login'))
    return render_template('novo_relato.html')

@app.route('/tipo-chamado')
def tipo_chamado():
    if 'usuario_email' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('novo_relato', etapa='tipo'))

@app.route('/escolher-empresa')
def escolher_empresa():
    if 'usuario_email' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('novo_relato'))

@app.route('/fazer-relato')
def fazer_relato():
    if 'usuario_email' not in session:
        return redirect(url_for('login'))
    return render_template('tipo_registro.html')

@app.route('/protocolo')
def consultar_protocolo():
    codigo_protocolo = request.args.get('codigo', '').strip()
    relato_encontrado = None

    if codigo_protocolo:
        relato_encontrado = db.session.execute(
            text("""
                SELECT protocolo, criado_em, categoria, status, mensagem, sugestao_solucao
                FROM relatos 
                WHERE protocolo = :codigo
            """),
            {'codigo': codigo_protocolo}
        ).mappings().fetchone()

    return render_template(
        'consultar_protocolo.html',
        protocolo=codigo_protocolo,
        relato=relato_encontrado,
    )

# --- ROTAS DE AUTENTICAÇÃO TRADICIONAL ---
@app.route('/api/cadastro', methods=['POST'])
def cadastro():
    data = request.get_json() if request.is_json else request.form
    nome = data.get('nome', '')
    email = data.get('email')
    senha = data.get('senha')

    if not email or not senha:
        return jsonify({'erro': 'E-mail e senha são obrigatórios'}), 400

    senha_hash = generate_password_hash(senha)

    try:
        db.session.execute(
            text('INSERT INTO "Usuarios" (nome, email, senha_hash) VALUES (:nome, :email, :senha_hash)'),
            {'nome': nome, 'email': email, 'senha_hash': senha_hash}
        )
        db.session.commit()
        return jsonify({'mensagem': 'Usuário cadastrado com sucesso!'}), 201
    except Exception as e:
        db.session.rollback()
        print("Erro no cadastro:", str(e))
        return jsonify({'erro': 'E-mail já cadastrado'}), 400

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        if 'usuario_email' in session:
            return redirect(url_for('home'))
        return render_template('login.html')

    # Trata POST (seja application/json via fetch ou multipart/form-data)
    data = request.get_json(silent=True) or request.form
    login_val = (data.get('email') or data.get('login') or '').strip()
    senha = data.get('senha') or ''

    if not login_val or not senha:
        if request.is_json:
            return jsonify({'erro': 'E-mail/usuário e senha são obrigatórios.'}), 400
        flash('E-mail/usuário e senha são obrigatórios.')
        return redirect(url_for('login'))

    usuario = db.session.execute(
        text('SELECT * FROM "Usuarios" WHERE email = :val OR nome = :val'),
        {'val': login_val}
    ).mappings().fetchone()

    if usuario and usuario['senha_hash'] and (check_password_hash(usuario['senha_hash'], senha) or usuario['senha_hash'] == senha):
        session.permanent = True
        session['user_id'] = usuario['id']
        session['usuario_email'] = usuario['email']
        session['usuario_nome'] = usuario['nome']
        session['usuario_tipo'] = usuario['tipo'] or 'usuario'
        
        target_redirect = url_for('admin_dashboard') if usuario['tipo'] == 'admin' else url_for('home')
        
        if request.is_json:
            return jsonify({
                'mensagem': 'Login realizado com sucesso!',
                'redirect': target_redirect,
                'user': {
                    'id': usuario['id'],
                    'nome': usuario['nome'],
                    'email': usuario['email'],
                    'tipo': usuario['tipo'] or 'usuario'
                }
            }), 200
        
        flash("Login realizado com sucesso!")
        return redirect(target_redirect)
    else:
        if request.is_json:
            return jsonify({'erro': 'E-mail/usuário ou senha incorretos.'}), 401
            
        flash("E-mail/usuário ou senha incorretos.")
        return redirect(url_for('login'))

@app.route('/api/login', methods=['POST'])
def api_login():
    return login()

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- ROTA DE ENVIO DE RELATO ---
@app.route('/enviar', methods=['POST'])
def enviar():
    try:
        dados = request.form if request.form else (request.get_json() or {})

        relato = dados.get('relato') or dados.get('mensagem')
        if not relato:
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'erro': 'O relato não pode estar vazio.'}), 400
            flash('O relato não pode estar vazio.')
            return redirect(url_for('novo_relato'))

        categoria = dados.get('categoria', 'Geral')
        empregado = dados.get('empregado')
        empresa_fato = dados.get('empresa_fato')
        diretoria = dados.get('diretoria')
        filial = dados.get('filial')
        cidade = dados.get('cidade')
        area_setor = dados.get('area_setor')
        evidencias = dados.get('evidencias')
        chefia_ciente = dados.get('chefia_ciente')
        chefia_envolvida = dados.get('chefia_envolvida')
        tentativa_ocultar = dados.get('tentativa_ocultar')
        testemunhas = dados.get('testemunhas')
        sugestao_solucao = dados.get('sugestao_solucao')

        identificacao = dados.get('identificacao', 'nao')
        if identificacao == 'sim':
            relator_nome = dados.get('nome_identificado') or dados.get('nome_relator')
            relator_email = dados.get('email_identificado')
            relator_celular = dados.get('celular_identificado')
        else:
            relator_nome = 'Anônimo'
            relator_email = dados.get('email_relator')
            relator_celular = dados.get('celular_relator')

        arquivos_salvos = []
        if 'anexos' in request.files:
            arquivos = request.files.getlist('anexos')
            for file in arquivos:
                if file and file.filename != '':
                    filename = secure_filename(file.filename)
                    caminho_salvar = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(caminho_salvar)
                    arquivos_salvos.append(filename)

        anexos_str = ",".join(arquivos_salvos) if arquivos_salvos else None

        data_hoje = datetime.now().strftime('%Y%m%d')
        codigo_hash = str(uuid.uuid4())[:4].upper()
        protocolo_gerado = f"NEXO-{data_hoje}-{codigo_hash}"

        db.session.execute(text('''
            INSERT INTO relatos (
                protocolo, mensagem, categoria, empregado, empresa_fato, diretoria, filial, cidade, 
                area_setor, evidencias, chefia_ciente, chefia_envolvida, tentativa_ocultar,
                testemunhas, sugestao_solucao, anexos, identificacao,
                relator_nome, relator_email, relator_celular
            ) VALUES (
                :protocolo, :mensagem, :categoria, :empregado, :empresa_fato, :diretoria, :filial, :cidade, 
                :area_setor, :evidencias, :chefia_ciente, :chefia_envolvida, :tentativa_ocultar,
                :testemunhas, :sugestao_solucao, :anexos, :identificacao,
                :relator_nome, :relator_email, :relator_celular
            )
        '''), {
            'protocolo': protocolo_gerado, 'mensagem': relato, 'categoria': categoria, 
            'empregado': empregado, 'empresa_fato': empresa_fato, 'diretoria': diretoria, 
            'filial': filial, 'cidade': cidade, 'area_setor': area_setor, 'evidencias': evidencias, 
            'chefia_ciente': chefia_ciente, 'chefia_envolvida': chefia_envolvida, 
            'tentativa_ocultar': tentativa_ocultar, 'testemunhas': testemunhas, 
            'sugestao_solucao': sugestao_solucao, 'anexos': anexos_str, 'identificacao': identificacao,
            'relator_nome': relator_nome, 'relator_email': relator_email, 'relator_celular': relator_celular
        })
        db.session.commit()

        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'sucesso': True,
                'protocolo': protocolo_gerado,
                'redirect_url': url_for('consultar_protocolo', codigo=protocolo_gerado)
            }), 200

        return redirect(url_for('consultar_protocolo', codigo=protocolo_gerado))

    except Exception as e:
        db.session.rollback()
        print("Erro ao enviar relato:", str(e))
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'erro': f'Erro no servidor: {str(e)}'}), 500
        return f"Erro no servidor ao gravar o relato: {str(e)}", 500

# --- APIS DE CONSULTA ---
@app.route('/api/consultar_protocolo/<codigo>', methods=['GET'])
def api_consultar_protocolo(codigo):
    relato = db.session.execute(
        text("SELECT protocolo, criado_em, categoria, status FROM relatos WHERE protocolo = :codigo"),
        {'codigo': codigo}
    ).mappings().fetchone()

    if relato:
        return jsonify({
            'encontrado': True,
            'protocolo': relato['protocolo'],
            'data': relato['criado_em'],
            'categoria': relato['categoria'],
            'status': relato['status']
        })
    return jsonify({'encontrado': False, 'mensagem': 'Protocolo não encontrado.'}), 404

@app.route('/api/relato/<int:relato_id>', methods=['GET'])
def obter_detalhes_relato(relato_id):
    if 'usuario_email' not in session:
        return jsonify({'erro': 'Não autorizado'}), 401

    relato = db.session.execute(
        text("SELECT * FROM relatos WHERE id = :id"),
        {'id': relato_id}
    ).mappings().fetchone()

    if relato:
        return jsonify({
            'sucesso': True,
            'relato': dict(relato)
        })
    return jsonify({'sucesso': False, 'mensagem': 'Relato não encontrado'}), 404

# --- ROTAS DO CHAT ---
@app.route('/api/chat/mensagens', methods=['GET'])
def buscar_mensagens_chat():
    if 'usuario_email' not in session:
        return jsonify({'erro': 'Não autorizado'}), 401

    mensagens = db.session.execute(text('''
        SELECT id, usuario_email, usuario_nome, mensagem, 
               TO_CHAR(criado_em, 'DD/MM/YYYY HH24:MI') as data_formatada 
        FROM mensagens_chat 
        ORDER BY id ASC
    ''')).mappings().fetchall()

    return jsonify({'sucesso': True, 'mensagens': [dict(m) for m in mensagens]})

@app.route('/api/chat/enviar', methods=['POST'])
def enviar_mensagem_chat():
    if 'usuario_email' not in session:
        return jsonify({'erro': 'Não autorizado'}), 401

    dados = request.get_json() or {}
    texto = dados.get('mensagem', '').strip()

    if not texto:
        return jsonify({'erro': 'A mensagem não pode estar vazia.'}), 400

    email = session.get('usuario_email')
    nome = session.get('usuario_nome', 'Usuário')

    db.session.execute(
        text('''
            INSERT INTO mensagens_chat (usuario_email, usuario_nome, mensagem)
            VALUES (:email, :nome, :mensagem)
        '''),
        {'email': email, 'nome': nome, 'mensagem': texto}
    )
    db.session.commit()

    return jsonify({'sucesso': True, 'mensagem': 'Mensagem enviada!'}), 201

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)