from app import db  # Importação absoluta

from datetime import datetime

class Usuario(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    celular = db.Column(db.String(20), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    cep = db.Column(db.String(10), nullable=False)
    logradouro = db.Column(db.String(255), nullable=False)
    numero = db.Column(db.String(20), nullable=False)
    complemento = db.Column(db.String(100))
    bairro = db.Column(db.String(100), nullable=False)
    cidade = db.Column(db.String(100), nullable=False)
    estado = db.Column(db.String(2), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)  # Campo obrigatório
    data_registro = db.Column(db.DateTime, default=datetime.utcnow)  # Data de registro
    ultimo_pedido = db.Column(db.DateTime)  # Data do último pedido
    itens_pedidos = db.Column(db.String(255))  # Itens pedidos (pode ser ajustado para um relacionamento com outra tabela)
   
    def definir_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def verificar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    preco = db.Column(db.Float, nullable=False)
    estoque = db.Column(db.Integer, nullable=False)
    data_atualizacao = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)
    foto = db.Column(db.String(255), nullable=True)  # Adicione esta linha

class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    total = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Recebido')

class ItemPedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    preco_unitario = db.Column(db.Float, nullable=False)