from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)

# Banco de dados
def conectar():
    return sqlite3.connect('banco.db', timeout=10)

# Criar as tabelas necessárias
def criar_tabelas():
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                preco REAL NOT NULL,
                estoque INTEGER NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vendas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                produto_id INTEGER,
                quantidade INTEGER,
                total REAL,
                data TEXT,
                FOREIGN KEY (produto_id) REFERENCES produtos(id)
            )
        ''')

# Inicializar
criar_tabelas()

@app.route('/')
def dashboard():
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM produtos")
        total_produtos = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM vendas")
        total_vendas = cursor.fetchone()[0]
    return render_template('dashboard.html', produtos=total_produtos, vendas=total_vendas)

@app.route('/produtos')
def produtos():
    with conectar() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM produtos")
        produtos = c.fetchall()
    return render_template('produtos.html', produtos=produtos)

@app.route('/adicionar_produto', methods=['POST'])
def adicionar_produto():
    nome = request.form['nome']
    preco = float(request.form['preco'])
    estoque = request.form['estoque']
    estoque = -1 if estoque.strip() == "" or estoque == "-1" else int(estoque)

    with conectar() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO produtos (nome, preco, estoque) VALUES (?, ?, ?)", (nome, preco, estoque))
        conn.commit()
    return redirect(url_for('produtos'))

@app.route('/vendas', methods=['GET', 'POST'])
def vendas():
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, preco, estoque FROM produtos")
        produtos = cursor.fetchall()
        if request.method == 'POST':
            produto_id = int(request.form['produto_id'])
            quantidade = int(request.form['quantidade'])
            cursor.execute("SELECT estoque, preco FROM produtos WHERE id = ?", (produto_id,))
            resultado = cursor.fetchone()

            if resultado:
                estoque_atual, preco_unitario = resultado
                if estoque_atual >= quantidade:
                    novo_estoque = estoque_atual - quantidade
                    total = quantidade * preco_unitario
                    data = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    cursor.execute("INSERT INTO vendas (produto_id, quantidade, total, data) VALUES (?, ?, ?, ?)",
                                   (produto_id, quantidade, total, data))
                    cursor.execute("UPDATE produtos SET estoque = ? WHERE id = ?", (novo_estoque, produto_id))
                    conn.commit()
                else:
                    return "Estoque insuficiente!"
            else:
                return "Produto não encontrado!"

        cursor.execute('''
            SELECT vendas.id, produtos.nome, vendas.quantidade, vendas.total
            FROM vendas
            JOIN produtos ON vendas.produto_id = produtos.id
        ''')
        vendas = cursor.fetchall()

    return render_template('vendas.html', produtos=produtos, vendas=vendas)

@app.route('/excluir_venda/<int:id>')
def excluir_venda(id):
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT produto_id, quantidade FROM vendas WHERE id = ?", (id,))
        venda = cursor.fetchone()
        if venda:
            produto_id, quantidade = venda
            cursor.execute("UPDATE produtos SET estoque = estoque + ? WHERE id = ?", (quantidade, produto_id))
        cursor.execute("DELETE FROM vendas WHERE id = ?", (id,))
        conn.commit()
    return redirect(url_for('vendas'))

@app.route('/relatorios')
def relatorios():
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT produtos.nome, SUM(vendas.quantidade) as total_vendido
            FROM vendas
            JOIN produtos ON vendas.produto_id = produtos.id
            GROUP BY produtos.id
            ORDER BY total_vendido DESC
            LIMIT 5
        ''')
        mais_vendidos = cursor.fetchall()
    return render_template('relatorios.html', mais_vendidos=mais_vendidos)

@app.route('/sair')
def sair():
    return redirect("https://www.google.com")

# 🚨 NOVA ROTA PARA EXCLUIR PRODUTO
@app.route('/excluir_produto/<int:id>')
def excluir_produto(id):
    try:
        with conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM produtos WHERE id = ?", (id,))
            conn.commit()
    except sqlite3.OperationalError as e:
        return f"Erro ao excluir produto: {e}"
    return redirect(url_for('produtos'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
