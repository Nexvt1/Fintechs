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
import json
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env ou env no diretório do projeto
basedir = os.path.dirname(os.path.abspath(__file__))
env_arquivos = [
    os.path.join(basedir, '.env'),
    os.path.join(basedir, 'env'),
    '.env',
    'env'
]

carregado = False
for arquivo in env_arquivos:
    if os.path.isfile(arquivo):
        load_dotenv(arquivo, override=True)
        carregado = True

if not carregado:
    load_dotenv(override=True)

app = Flask(__name__)

# --- CONFIGURAÇÃO DA CHAVE SECRETA E SESSÃO PERMANENTE (LIDAS DO ENV) ---
app.secret_key = os.getenv('SECRET_KEY') or os.getenv('FLASK_SECRET_KEY') or 'chave_padrao_caso_nao_encontre'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# --- CONFIGURAÇÕES DO SUPABASE OBTIDAS DO ENV ---
SUPABASE_URL = os.getenv('SUPABASE_URL') or os.getenv('VITE_SUPABASE_URL')
SUPABASE_ANON_KEY = (
    os.getenv('SUPABASE_ANON_KEY')
    or os.getenv('SUPABASE_KEY')
    or os.getenv('VITE_SUPABASE_ANON_KEY')
)
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

app.config['SUPABASE_URL'] = SUPABASE_URL
app.config['SUPABASE_ANON_KEY'] = SUPABASE_ANON_KEY

# --- CONFIGURAÇÃO DO BANCO DE DADOS (SUPABASE / POSTGRESQL OBTIDO DO ENV) ---
db_url = (
    os.getenv('DATABASE_URL')
    or os.getenv('SUPABASE_DATABASE_URL')
    or os.getenv('SUPABASE_DB_URL')
    or os.getenv('POSTGRES_URL')
)

if not db_url:
    raise RuntimeError(
        "Erro de configuração: DATABASE_URL não foi encontrada no arquivo de ambiente (.env ou env). "
        "Defina DATABASE_URL no seu arquivo env com a string de conexão do Supabase PostgreSQL."
    )

if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+psycopg2://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

db = SQLAlchemy(app)

# Desativar cache do navegador durante o desenvolvimento
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response

# --- INICIALIZAÇÃO DAS TABELAS NO SUPABASE ---
def init_db():
    with app.app_context():
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

        # Garante que as colunas saldo, investimentos e personalização existem
        try:
            db.session.execute(text('ALTER TABLE "Usuarios" ADD COLUMN IF NOT EXISTS saldo NUMERIC DEFAULT 1500.00'))
            db.session.execute(text('ALTER TABLE "Usuarios" ADD COLUMN IF NOT EXISTS investimentos NUMERIC DEFAULT 3200.00'))
            db.session.execute(text('ALTER TABLE "Usuarios" ADD COLUMN IF NOT EXISTS trilha_progresso TEXT'))
            db.session.execute(text('ALTER TABLE "Usuarios" ADD COLUMN IF NOT EXISTS trilha_xp INTEGER DEFAULT 0'))
            db.session.execute(text('ALTER TABLE "Usuarios" ADD COLUMN IF NOT EXISTS trilha_streak INTEGER DEFAULT 1'))
            db.session.execute(text('ALTER TABLE "Usuarios" ADD COLUMN IF NOT EXISTS trilha_coins INTEGER DEFAULT 0'))
            db.session.execute(text('ALTER TABLE "Usuarios" ADD COLUMN IF NOT EXISTS trilha_hearts INTEGER DEFAULT 5'))
            db.session.execute(text('ALTER TABLE "Usuarios" ADD COLUMN IF NOT EXISTS trilha_nivel_atual INTEGER DEFAULT 0'))
            db.session.execute(text('ALTER TABLE "Usuarios" ADD COLUMN IF NOT EXISTS trilha_ultima_missao TEXT'))
            db.session.execute(text('ALTER TABLE "Usuarios" ADD COLUMN IF NOT EXISTS modo_anonimo_padrao BOOLEAN DEFAULT FALSE'))
            db.session.execute(text('ALTER TABLE "Usuarios" ADD COLUMN IF NOT EXISTS notificar_status BOOLEAN DEFAULT TRUE'))
            db.session.execute(text('ALTER TABLE "Usuarios" ADD COLUMN IF NOT EXISTS tema TEXT DEFAULT \'escuro\''))
            db.session.execute(text('ALTER TABLE "Usuarios" ADD COLUMN IF NOT EXISTS foto_perfil TEXT'))
            db.session.execute(text('ALTER TABLE "Usuarios" ADD COLUMN IF NOT EXISTS tom_verde TEXT DEFAULT \'#0b3d2c\''))
            db.session.execute(text('UPDATE "Usuarios" SET saldo = 1500.00 WHERE saldo IS NULL'))
            db.session.execute(text('UPDATE "Usuarios" SET investimentos = 3200.00 WHERE investimentos IS NULL'))
            db.session.commit()
        except Exception:
            db.session.rollback()

        # Garante política permissiva para chave do Supabase Mobile APK
        try:
            db.session.execute(text('DROP POLICY IF EXISTS "Allow anon access" ON "Usuarios"'))
            db.session.execute(text('CREATE POLICY "Allow anon access" ON "Usuarios" FOR ALL TO anon, authenticated USING (true) WITH CHECK (true)'))
            db.session.commit()
        except Exception:
            db.session.rollback()

        # Garante usuário administrador padrão (lido do env com fallback)
        try:
            admin_check = db.session.execute(text("SELECT id FROM \"Usuarios\" WHERE tipo = 'admin'")).fetchone()
            if not admin_check:
                admin_email = os.getenv('ADMIN_EMAIL', 'admin@fistu.com')
                admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
                db.session.execute(text('''
                    INSERT INTO "Usuarios" (nome, email, senha_hash, tipo, saldo, investimentos)
                    VALUES ('Administrador', :email, :senha, 'admin', 50000.00, 120000.00)
                '''), {'email': admin_email, 'senha': generate_password_hash(admin_password)})
                db.session.commit()
        except Exception:
            db.session.rollback()

init_db()

# --- CONTEXT PROCESSOR E ENDPOINTS DE CONFIGURAÇÃO DO SUPABASE ---
@app.context_processor
def inject_supabase_config():
    """Disponibiliza as credenciais públicas do Supabase para todos os templates."""
    return {
        'SUPABASE_URL': app.config.get('SUPABASE_URL'),
        'SUPABASE_ANON_KEY': app.config.get('SUPABASE_ANON_KEY')
    }

@app.route('/api/config/supabase', methods=['GET'])
def api_supabase_config():
    """Retorna as configurações do Supabase (URL e Anon Key) obtidas exclusivamente do arquivo env."""
    return jsonify({
        'supabase_url': app.config.get('SUPABASE_URL'),
        'supabase_anon_key': app.config.get('SUPABASE_ANON_KEY')
    })

# --- ROTAS DE INTERFACE (WEB) ---

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
        
    campos = (
        'id, nome, email, tipo, saldo, investimentos, '
        'trilha_progresso, trilha_xp, trilha_streak, trilha_coins, '
        'trilha_hearts, trilha_nivel_atual, trilha_ultima_missao, '
        'modo_anonimo_padrao, notificar_status, tema, foto_perfil, tom_verde'
    )
    usuario_db = db.session.execute(
        text(f'SELECT {campos} FROM "Usuarios" WHERE id = :id'),
        {'id': session.get('user_id')}
    ).mappings().fetchone()
    
    if not usuario_db:
        usuario_db = db.session.execute(
            text(f'SELECT {campos} FROM "Usuarios" WHERE email = :email'),
            {'email': session.get('usuario_email')}
        ).mappings().fetchone()
        
    if not usuario_db:
        session.clear()
        return redirect(url_for('login'))
        
    session['user_id'] = usuario_db['id']
    session['usuario_nome'] = usuario_db['nome']
    session['usuario_tipo'] = usuario_db['tipo'] or 'usuario'
    
    return render_template('home.html', usuario=usuario_db)

@app.route('/api/usuario/personalizacao', methods=['POST'])
def api_usuario_personalizacao():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'erro': 'Não autorizado'}), 401

    dados = request.get_json() or {}
    nome = dados.get('nome')
    tema = dados.get('tema')
    tom_verde = dados.get('tom_verde')
    foto_perfil = dados.get('foto_perfil')
    notificar_status = dados.get('notificar_status')
    modo_anonimo = dados.get('modo_anonimo')

    try:
        updates = []
        params = {'id': user_id}
        if nome is not None and str(nome).strip():
            updates.append("nome = :nome")
            params['nome'] = str(nome).strip()
            session['usuario_nome'] = str(nome).strip()
        if tema is not None:
            updates.append("tema = :tema")
            params['tema'] = str(tema)
        if tom_verde is not None:
            updates.append("tom_verde = :tom_verde")
            params['tom_verde'] = str(tom_verde)
        if foto_perfil is not None:
            updates.append("foto_perfil = :foto_perfil")
            params['foto_perfil'] = str(foto_perfil)
        if notificar_status is not None:
            updates.append("notificar_status = :notificar")
            params['notificar'] = bool(notificar_status)
        if modo_anonimo is not None:
            updates.append("modo_anonimo_padrao = :anonimo")
            params['anonimo'] = bool(modo_anonimo)

        if updates:
            sql_query = f'UPDATE "Usuarios" SET {", ".join(updates)} WHERE id = :id'
            db.session.execute(text(sql_query), params)
            db.session.commit()

        return jsonify({'sucesso': True, 'mensagem': 'Personalizações salvas no Supabase!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao salvar: {str(e)}'}), 500

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
        text('SELECT id, nome, email, tipo, saldo, investimentos, trilha_progresso, trilha_xp, trilha_streak, trilha_coins, trilha_hearts, trilha_nivel_atual, trilha_ultima_missao FROM "Usuarios" ORDER BY id ASC')
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
    level_index = int(data.get('levelIndex', 0))
    progress_matrix = data.get('progress')
    new_xp = data.get('xp')
    new_streak = data.get('streak')
    new_coins = data.get('coins')
    new_hearts = data.get('hearts')
    bonus_reais = 5.00 # Bônus de aprendizado de R$ 5,00
    
    usuario = db.session.execute(
        text('SELECT id, tipo, saldo, investimentos, trilha_progresso, trilha_xp, trilha_streak, trilha_coins, trilha_hearts, trilha_ultima_missao FROM "Usuarios" WHERE id = :id'),
        {'id': user_id}
    ).mappings().fetchone()
    
    if not usuario:
        return jsonify({'erro': 'Usuário não encontrado.'}), 404
        
    hoje = datetime.now().strftime('%Y-%m-%d')
    novo_saldo = float(usuario['saldo'] or 0) + bonus_reais
    
    progresso_str = json.dumps(progress_matrix) if progress_matrix is not None else usuario['trilha_progresso']
    xp_val = int(new_xp) if new_xp is not None else int(usuario['trilha_xp'] or 0) + 15
    coins_val = int(new_coins) if new_coins is not None else int(usuario['trilha_coins'] or 0) + 20
    streak_val = int(new_streak) if new_streak is not None else int(usuario['trilha_streak'] or 1)
    hearts_val = int(new_hearts) if new_hearts is not None else int(usuario['trilha_hearts'] or 5)

    db.session.execute(
        text('''
            UPDATE "Usuarios" 
            SET saldo = :saldo,
                trilha_progresso = :progresso,
                trilha_xp = :xp,
                trilha_streak = :streak,
                trilha_coins = :coins,
                trilha_hearts = :hearts,
                trilha_nivel_atual = :nivel,
                trilha_ultima_missao = :hoje
            WHERE id = :id
        '''),
        {
            'saldo': novo_saldo,
            'progresso': progresso_str,
            'xp': xp_val,
            'streak': streak_val,
            'coins': coins_val,
            'hearts': hearts_val,
            'nivel': level_index,
            'hoje': hoje,
            'id': user_id
        }
    )
    db.session.commit()
    
    return jsonify({
        'sucesso': True,
        'mensagem': f'Parabéns! Stage {stage} ({level}) concluído! Bônus de R$ {bonus_reais:.2f} creditado no seu saldo!',
        'saldo': novo_saldo,
        'bonus': bonus_reais,
        'xp': xp_val,
        'coins': coins_val,
        'streak': streak_val,
        'hearts': hearts_val
    }), 200

@app.route('/api/usuario/trilha/salvar', methods=['POST'])
def api_usuario_trilha_salvar():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'erro': 'Usuário não autenticado.'}), 401
        
    data = request.get_json(silent=True) or {}
    progress_matrix = data.get('progress')
    xp_val = data.get('xp')
    streak_val = data.get('streak')
    coins_val = data.get('coins')
    hearts_val = data.get('hearts')
    nivel_val = data.get('nivel')
    
    progresso_str = json.dumps(progress_matrix) if progress_matrix is not None else None
    
    db.session.execute(
        text('''
            UPDATE "Usuarios" 
            SET trilha_progresso = COALESCE(:progresso, trilha_progresso),
                trilha_xp = COALESCE(:xp, trilha_xp),
                trilha_streak = COALESCE(:streak, trilha_streak),
                trilha_coins = COALESCE(:coins, trilha_coins),
                trilha_hearts = COALESCE(:hearts, trilha_hearts),
                trilha_nivel_atual = COALESCE(:nivel, trilha_nivel_atual)
            WHERE id = :id
        '''),
        {
            'progresso': progresso_str,
            'xp': int(xp_val) if xp_val is not None else None,
            'streak': int(streak_val) if streak_val is not None else None,
            'coins': int(coins_val) if coins_val is not None else None,
            'hearts': int(hearts_val) if hearts_val is not None else None,
            'nivel': int(nivel_val) if nivel_val is not None else None,
            'id': user_id
        }
    )
    db.session.commit()
    return jsonify({'sucesso': True}), 200

@app.route('/api/admin/usuario/trilha/<int:user_target_id>')
def api_admin_usuario_trilha(user_target_id):
    if session.get('usuario_tipo') != 'admin':
        return jsonify({'erro': 'Acesso negado.'}), 403
    u = db.session.execute(
        text('SELECT id, nome, email, tipo, trilha_progresso, trilha_xp, trilha_streak, trilha_coins, trilha_hearts, trilha_nivel_atual, trilha_ultima_missao FROM "Usuarios" WHERE id = :id'),
        {'id': user_target_id}
    ).mappings().fetchone()
    if not u:
        return jsonify({'erro': 'Usuário não encontrado.'}), 404
    return jsonify(dict(u))

@app.route('/index')
def index():
    return redirect(url_for('root'))

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

if __name__ == '__main__':
    porta = int(os.environ.get('PORT', 5050))
    app.run(host='0.0.0.0', port=porta, debug=True)