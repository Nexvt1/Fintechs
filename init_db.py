from app import app, db

def inicializar_banco():
    with app.app_context():
        # Cria todas as tabelas mapeadas no seu app.py (PostgreSQL / Supabase)
        db.create_all()
        print("Tabelas criadas com sucesso no Supabase!")

if __name__ == '__main__':
    inicializar_banco()