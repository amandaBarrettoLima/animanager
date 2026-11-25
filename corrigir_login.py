"""Mostra os usuários do banco que o sistema REALMENTE usa e conserta o login do Responsável Esperança.

    python corrigir_login.py

Define: e-mail = esperanca@animanager.com | senha = senha123
"""
import sqlite3

from werkzeug.security import generate_password_hash

from config import Config

NOVO_EMAIL = "esperanca@animanager.com"
NOVA_SENHA = "senha123"

print("Banco usado pelo sistema:", Config.DATABASE_PATH)
con = sqlite3.connect(Config.DATABASE_PATH)
try:
    usuarios = con.execute("SELECT id, email, nome, abrigo_id FROM usuarios ORDER BY id").fetchall()
except sqlite3.OperationalError:
    raise SystemExit("Esse banco ainda não tem tabelas. Rode `python run.py` uma vez para criá-lo e tente de novo.")

print("\nUsuários ANTES:")
for u in usuarios:
    print("  ", u)

alterados = con.execute("UPDATE usuarios SET email = ?, senha_hash = ? WHERE nome = ?",
                        (NOVO_EMAIL, generate_password_hash(NOVA_SENHA), "Responsável Esperança")).rowcount
con.commit()

if alterados == 0:
    print("\nNão encontrei o usuário 'Responsável Esperança'. Veja a lista acima e me diga o nome certo.")
else:
    print("\nUsuários DEPOIS:")
    for u in con.execute("SELECT id, email, nome, abrigo_id FROM usuarios ORDER BY id"):
        print("  ", u)
    print(f"\nPronto! Entre com  {NOVO_EMAIL}  /  {NOVA_SENHA}")
con.close()
