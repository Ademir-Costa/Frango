from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from dotenv import load_dotenv
import os
from sqlalchemy.orm import joinedload 
from flask import jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask import request, jsonify
from sqlalchemy import func
from flask_login import LoginManager
from flask_login import UserMixinpip


# Carregar variáveis de ambiente
load_dotenv()

app = Flask(__name__)

# Configurações do Flask
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configurações do Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

db = SQLAlchemy(app)
mail = Mail(app)

# Configuração do Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Rota para redirecionar usuários não autenticados

# Serializador para gerar tokens
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))



import pytz

@app.context_processor
def inject_datetime():
    cuiaba_tz = pytz.timezone('America/Cuiaba')
    return {
        'datetime': datetime,
        'timedelta': timedelta,
        'now_in_cuiaba': lambda: datetime.now(cuiaba_tz)  # Data atual em Cuiabá
    }

# Modelo de Usuário

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
    # Métodos para gerenciamento de senha
    ultimo_pedido = db.Column(db.DateTime)  # Data do último pedido
    itens_pedidos = db.Column(db.String(255))  # Itens pedidos (pode ser ajustado para um relacionamento com outra tabela)
    
    def definir_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def verificar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)
    
    
@property
def taxa_entrega(self):
        return 10.00 if self.local_retirada == "Entregar no Endereço" else 0.00

@property
def total(self):
        subtotal = sum(item.quantidade * item.preco_unitario for item in self.itens)
        return subtotal + self.taxa_entrega
    
class Pedido(db.Model):
    __tablename__ = 'pedido'  # Nome explícito da tabela
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    data_pedido = db.Column(db.DateTime, default=datetime.utcnow)
    local_retirada = db.Column(db.String(50), nullable=False)
    taxa_entrega = db.Column(db.Float, nullable=False, default=0.0)
    total = db.Column(db.Float, nullable=False)
    data_retirada = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='Recebido')
    
    
    
    # Relacionamento com Usuário
    usuario = db.relationship('Usuario', backref='pedidos')


# Modelo de ItemPedid
class ItemPedido(db.Model):
    __tablename__ = 'item_pedido'  # Nome explícito da tabela
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido.id'), nullable=False) 
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    preco_unitario = db.Column(db.Float, nullable=False)
    
    # Relacionamentos
    pedido = db.relationship('Pedido', backref=db.backref('itens', lazy='joined'))
    produto = db.relationship('Produto', backref='itens_pedido', lazy='joined')
    
    

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    preco = db.Column(db.Float, nullable=False)
    estoque = db.Column(db.Integer, nullable=False)
    data_atualizacao = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)
    foto = db.Column(db.String(255), nullable=True)  # Adicione esta linha

# Rotas da interface web


@app.route('/')
def index():
    # Certifique-se que 'estoque' é um campo numérico e a query está correta
    produtos = Produto.query.filter(Produto.estoque > 0).order_by(Produto.nome).all()
    return render_template('index.html', produtos=produtos)


@app.route('/admin/pedidos')
@login_required
def pedidos():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    # Buscar pedidos e ordenar por data_retirada
    pedidos = Pedido.query.options(
        db.joinedload(Pedido.usuario),
        db.joinedload(Pedido.itens).joinedload(ItemPedido.produto)
    ).filter(Pedido.status.notin_(['Entregue', 'Retirado', 'Cancelado','Recebido'])) \
     .order_by(Pedido.data_retirada.asc()) \
     .all()
    
    return render_template('pedidos.html', pedidos=pedidos)



@app.route('/admin/todos_pedidos', methods=['GET'])
@login_required
def todos_pedidos():
    # Verifica se o usuário é administrador
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    # Obter parâmetros de filtro de data da URL
    data_inicial = request.args.get('data_inicial')
    data_final = request.args.get('data_final')

    # Construir a consulta base
    query = Pedido.query.options(
        db.joinedload(Pedido.usuario),
        db.joinedload(Pedido.itens).joinedload(ItemPedido.produto)
    ).filter(Pedido.status.notin_(['']))\
      

    # Aplicar filtro de datas, se fornecido
    if data_inicial and data_final:
        try:
            # Converter as strings de data para objetos datetime
            data_inicial = datetime.strptime(data_inicial, '%Y-%m-%d')
            data_final = datetime.strptime(data_final, '%Y-%m-%d')

            # Validar que a data inicial não é maior que a data final
            if data_inicial > data_final:
                flash("A data inicial não pode ser maior que a data final.", "danger")
                return redirect(url_for('todos_pedidos'))

            # Filtrar pedidos dentro do intervalo de datas
            query = query.filter(Pedido.data_pedido.between(data_inicial, data_final))
        except ValueError:
            flash("Formato de data inválido. Use YYYY-MM-DD.", "danger")
            return redirect(url_for('todos_pedidos'))

    # Ordenar por data de pedido (mais recente primeiro)
    pedidos = query.order_by(Pedido.data_pedido.desc()).all()

    return render_template('todos_pedidos.html', pedidos=pedidos)
@app.route('/admin/produtos/atualizar/<int:produto_id>', methods=['POST'])
@login_required
def atualizar_produto(produto_id):
    if not current_user.is_admin:  # Verifica se o usuário é administrador
        #flash('Acesso negado. Você não é um administrador.', 'erro')
        return redirect(url_for('index'))

    produto = Produto.query.get_or_404(produto_id)  # Busca o produto pelo ID

    try:
        # Atualiza os campos do produto com base nos dados do formulário
        produto.preco = float(request.form.get('preco'))
        produto.estoque = int(request.form.get('estoque'))
        produto.data_atualizacao = datetime.utcnow()  # Adiciona a data de atualização
        db.session.commit()
        #flash('Produto atualizado com sucesso!', 'sucesso')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar o produto: {str(e)}', 'erro')

    return redirect(url_for('admin_produtos'))


from werkzeug.utils import secure_filename

# Configuração para uploads
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limite de 16MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
@login_required
def index2():
    return render_template('index2.html')


@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    # Verifica se o usuário é administrador
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    # Buscar apenas os pedidos recentes que não estão cancelados
    pedidos_recentes = Pedido.query.options(
        db.joinedload(Pedido.usuario),
        db.joinedload(Pedido.itens).joinedload(ItemPedido.produto)
    ).filter(Pedido.status.notin_(['Entregue', 'Retirado','Recebido','Cancelado']))  \
    .order_by(Pedido.data_pedido.desc()).limit(5000).all()
    
   
    
    # Outros dados do dashboard (usuários, produtos, etc.)
    total_usuarios = Usuario.query.count()
    total_produtos = Produto.query.count()
    total_pedidos = Pedido.query.count()
    
    return render_template('admin_dashboard.html', 
                           pedidos_recentes=pedidos_recentes,
                           total_usuarios=total_usuarios,
                           total_produtos=total_produtos,
                           total_pedidos=total_pedidos)

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        # Verifica se é o primeiro usuário
        is_first_user = Usuario.query.count() == 0
        
        # Recupera os dados do formulário
        celular = request.form.get('celular')
        nome = request.form.get('nome')
        email = request.form.get('email')
        senha = request.form.get('senha')
        cep = request.form.get('cep')
        logradouro = request.form.get('logradouro')
        numero = request.form.get('numero')
        complemento = request.form.get('complemento')
        bairro = request.form.get('bairro')
        cidade = request.form.get('cidade')
        estado = request.form.get('estado')

        # Validação dos campos obrigatórios
        if not celular or not senha or not email or not cep or not logradouro or not numero or not bairro or not cidade or not estado:
            flash('Todos os campos obrigatórios devem ser preenchidos', 'erro')
            return redirect(url_for('cadastro'))

        # Verifica se o celular já está cadastrado
        if Usuario.query.filter_by(celular=celular).first():
            flash('Número de celular já cadastrado', 'erro')
            return redirect(url_for('cadastro'))

        # Verifica se o email já está cadastrado
        if Usuario.query.filter_by(email=email).first():
            flash('E-mail já cadastrado', 'erro')
            return redirect(url_for('cadastro'))

        # Cria o novo usuário
        novo_usuario = Usuario(
            celular=celular,
            nome=nome,
            email=email,
            cep=cep,
            logradouro=logradouro,
            numero=numero,
            complemento=complemento,
            bairro=bairro,
            cidade=cidade,
            estado=estado,
            is_admin=is_first_user  # Define como admin apenas o primeiro usuário
        )

        # Define a senha
        novo_usuario.definir_senha(senha)

        # Salva no banco de dados
        db.session.add(novo_usuario)
        db.session.commit()

        # Mensagem de sucesso
        #flash('Cadastro realizado com sucesso!', 'sucesso')
        return redirect(url_for('login'))

    # Passa o número de usuários cadastrados para o template
    total_usuarios = Usuario.query.count()
    return render_template('cadastro.html', total_usuarios=total_usuarios)

@app.route('/editar_usuario/<int:user_id>', methods=['GET', 'POST'])
@login_required
def editar_usuario(user_id):
    if not current_user.is_admin:
       # flash('Acesso negado. Você não é um administrador.', 'erro')
        return redirect(url_for('index'))

    usuario = Usuario.query.get_or_404(user_id)

    if request.method == 'POST':
        # Atualiza os campos do usuário com base nos dados do formulário
        usuario.nome = request.form.get('nome')
        usuario.email = request.form.get('email')
        usuario.celular = request.form.get('celular')
        usuario.cep = request.form.get('cep')
        usuario.logradouro = request.form.get('logradouro')
        usuario.numero = request.form.get('numero')
        usuario.complemento = request.form.get('complemento')
        usuario.bairro = request.form.get('bairro')
        usuario.cidade = request.form.get('cidade')
        usuario.estado = request.form.get('estado')

        # Salva as alterações no banco de dados
        db.session.commit()
        #flash(f'Dados do usuário {usuario.nome} atualizados com sucesso!', 'sucesso')
        return redirect(url_for('admin_usuarios'))

    return render_template('editar_usuario.html', usuario=usuario)

@app.route('/excluir_usuario/<int:user_id>', methods=['POST'])
@login_required
def excluir_usuario(user_id):
    if not current_user.is_admin:
       # flash('Acesso negado. Você não é um administrador.', 'erro')
        return redirect(url_for('index'))

    usuario = Usuario.query.get_or_404(user_id)

    # Remove o usuário do banco de dados
    db.session.delete(usuario)
    db.session.commit()

  #  flash(f'Usuário {usuario.nome} excluído com sucesso!', 'sucesso')
    return redirect(url_for('admin_usuarios'))

@app.route('/cadastro_admin', methods=['GET', 'POST'])
def cadastro_admin():
    if request.method == 'POST':
        celular = request.form.get('celular')
        nome = request.form.get('nome')
        email = request.form.get('email')
        senha = request.form.get('senha')
        cep = request.form.get('cep')
        logradouro = request.form.get('logradouro')
        numero = request.form.get('numero')
        complemento = request.form.get('complemento')
        bairro = request.form.get('bairro')
        cidade = request.form.get('cidade')
        estado = request.form.get('estado')

        novo_usuario = Usuario(
            celular=celular,
            nome=nome,
            email=email,
            cep=cep,
            logradouro=logradouro,
            numero=numero,
            complemento=complemento,
            bairro=bairro,
            cidade=cidade,
            estado=estado,
            is_admin=True  # Definir como administrador
        )
        novo_usuario.definir_senha(senha)
        db.session.add(novo_usuario)
        db.session.commit()

        flash('Administrador cadastrado com sucesso!', 'sucesso')
        return redirect(url_for('index'))

    return render_template('cadastro_admin.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        celular = request.form.get('celular')
        senha = request.form.get('senha')
        
        usuario = Usuario.query.filter_by(celular=celular).first()
        if not usuario or not usuario.verificar_senha(senha):
            flash('Número de celular ou senha incorretos', 'erro')
            return redirect(url_for('login'))
        login_user(usuario)
        return redirect(url_for('admin_dashboard'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/recuperar_senha', methods=['GET', 'POST'])
def recuperar_senha():
    if request.method == 'POST':
        email = request.form.get('email')

        usuario = Usuario.query.filter_by(email=email).first()

        if usuario:
            token = serializer.dumps(usuario.email, salt='recuperacao-senha')
            usuario.reset_token = token
            usuario.token_expira = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()

            msg = Message('Recuperação de Senha', recipients=[usuario.email])
            msg.body = f'Para redefinir sua senha, clique no link: {url_for("redefinir_senha", token=token, _external=True)}'
            mail.send(msg)

          #  flash('Um e-mail com instruções foi enviado para você.', 'sucesso')
            return redirect(url_for('login'))

        #flash('E-mail não encontrado.', 'erro')
        return redirect(url_for('recuperar_senha'))

    return render_template('recuperar_senha.html')

@app.route('/redefinir_senha/<token>', methods=['GET', 'POST'])
def redefinir_senha(token):
    try:
        email = serializer.loads(token, salt='recuperacao-senha', max_age=3600)
        usuario = Usuario.query.filter_by(email=email).first()

        if not usuario or usuario.reset_token != token or usuario.token_expira < datetime.utcnow():
            flash('Link inválido ou expirado.', 'erro')
            return redirect(url_for('login'))

        if request.method == 'POST':
            nova_senha = request.form.get('nova_senha')
            usuario.definir_senha(nova_senha)
            usuario.reset_token = None
            usuario.token_expira = None
            db.session.commit()

            flash('Senha redefinida com sucesso!', 'sucesso')
            return redirect(url_for('login'))

        return render_template('redefinir_senha.html', token=token)

    except (SignatureExpired, BadSignature):
        flash('Link inválido ou expirado.', 'erro')
        return redirect(url_for('login'))
    
@app.route('/tornar_admin/<int:user_id>')
@login_required
def tornar_admin(user_id):
    if not current_user.is_admin:
    
        return redirect(url_for('index'))

    usuario = Usuario.query.get(user_id)
    if usuario:
        usuario.is_admin = True
        db.session.commit()
        flash(f'{usuario.nome} foi definido como administrador.', 'sucesso')
    else:
        flash('Usuário não encontrado.', 'erro')

    return redirect(url_for('admin_usuarios'))

@app.route('/remover_admin/<int:user_id>')
@login_required
def remover_admin(user_id):
    if not current_user.is_admin:
        
        return redirect(url_for('index'))
    
    usuario = Usuario.query.get(user_id)
    if usuario:
        usuario.is_admin = False
        db.session.commit()
        
    else:
        flash('Usuário não encontrado.', 'erro')
    
    return redirect(url_for('admin_usuarios'))

@app.route('/atualizar_status/<int:pedido_id>/<status>')
@login_required
def atualizar_status(pedido_id, status):
    if not current_user.is_admin:
       # flash('Acesso negado!', 'erro')
        return redirect(url_for('index'))
    
    pedido = Pedido.query.get(pedido_id)
    if pedido:
        pedido.status = status
        db.session.commit()
            
    return redirect(url_for('admin_dashboard'))

# Rota para o carrinho de compras
@app.route('/acompanhamento')
@login_required
def acompanhamento():
    pedido = (
        Pedido.query
        .filter_by(usuario_id=current_user.id)
        .options(
            db.joinedload(Pedido.itens).joinedload(ItemPedido.produto) 
        )
        .order_by(Pedido.data_pedido.desc())
        .first()
    )
    if not pedido:
      #  flash('Nenhum pedido encontrado.', 'erro')
        return redirect(url_for('index'))
    return render_template('acompanhamento.html', pedido=pedido)
    
    # Verifica se os itens estão corretamente carregados
    itens_pedido = ItemPedido.query.filter_by(pedido_id=pedido.id).all()
    
    return render_template('acompanhamento.html', pedido=pedido, itens_pedido=itens_pedido)

@app.route('/carrinho', methods=['GET', 'POST'])
@login_required
def carrinho():
    if request.method == 'POST':
        try:
            # Dados básicos do pedido
            local_retirada = request.form.get('local_retirada')
            data_retirada_str = request.form.get('data_retirada')

            # Validação inicial
            if not local_retirada or not data_retirada_str:
            #    flash('Preencha todos os campos obrigatórios.', 'erro')
                return redirect(url_for('carrinho'))

            data_retirada = datetime.strptime(data_retirada_str, '%Y-%m-%dT%H:%M')

            # Criar pedido
            pedido = Pedido(
                usuario_id=current_user.id,
                local_retirada=local_retirada,
                data_retirada=data_retirada,
                taxa_entrega=10.0 if local_retirada == 'Entrega na Residencia' else 0.0,
                total=0.0,
                status='Em preparação'
            )
            db.session.add(pedido)
            db.session.flush()  # Gera o ID do pedido sem commit

            total_pedido = 0.0
            itens_validos = False

            # Processar itens do carrinho
            for key in request.form:
                if key.startswith('produto_'):
                    produto_id = int(key.split('_')[1])
                    quantidade = int(request.form.get(key))

                    # Pular quantidades inválidas
                    if quantidade <= 0:
                        continue

                    produto = Produto.query.get(produto_id)
                    if not produto:
                        app.logger.error(f"Produto ID {produto_id} não encontrado")
                        raise ValueError(f"Produto ID {produto_id} não existe")

                    if produto.estoque < quantidade:
                        app.logger.error(f"Estoque insuficiente para {produto.nome} (ID {produto.id})")
                        raise ValueError(f"Estoque insuficiente para {produto.nome}")

                    # Criar item do pedido
                    item = ItemPedido(
                        pedido_id=pedido.id,
                        produto_id=produto.id,
                        quantidade=quantidade,
                        preco_unitario=produto.preco
                    )
                    db.session.add(item)
                    
                    # Atualizar estoque e total
                    produto.estoque -= quantidade
                    total_pedido += produto.preco * quantidade
                    itens_validos = True

                    app.logger.debug(f"Item adicionado: {produto.nome} x{quantidade}")

            # Validar se há itens
            if not itens_validos:
                app.logger.error("Pedido sem itens válidos")
                raise ValueError("Adicione pelo menos um item ao carrinho")

            # Atualizar total do pedido
            pedido.total = total_pedido + pedido.taxa_entrega
            app.logger.debug(f"Total do pedido: {pedido.total}")

            # Commit final
            db.session.commit()
            flash('Pedido confirmado! Aguarde a preparação.', 'sucesso')
            return redirect(url_for('acompanhamento'))

        except ValueError as e:
            db.session.rollback()
            app.logger.error(f"Erro de validação: {str(e)}")
            flash(str(e), 'erro')
            return redirect(url_for('carrinho'))

        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Erro inesperado: {str(e)}", exc_info=True)
            flash('Erro interno ao processar o pedido.', 'erro')
            return redirect(url_for('carrinho'))

    # GET: Exibir produtos disponíveis
    produtos = Produto.query.filter(Produto.estoque > 0).all()
    min_date = (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')
    return render_template('carrinho.html', produtos=produtos, min_date=min_date)


from flask import flash, redirect, url_for

@app.route('/cancelar_pedido/<int:pedido_id>', methods=['POST'])
@login_required
def cancelar_pedido(pedido_id):
    # Buscar o pedido pelo ID e verificar se pertence ao usuário logado
    pedido = Pedido.query.filter_by(id=pedido_id, usuario_id=current_user.id).first()
    
    if not pedido:
        flash('Pedido não encontrado.', 'erro')
        return redirect(url_for('index'))
    
    # Verificar se o pedido pode ser cancelado (status "Pendente")
    if pedido.status != "Em preparação":
        flash('Este pedido não pode ser cancelado porque já está em andamento ou concluído.', 'erro')
        return redirect(url_for('acompanhamento'))
    
    # Atualizar o status do pedido para "Cancelado"
    pedido.status = "Cancelado"
    db.session.commit()
    
    flash('Pedido cancelado com sucesso.', 'sucesso')
    return redirect(url_for('acompanhamento'))

# API para gráfico de pedidos

@app.route('/admin/api_graficos', methods=['GET'])
@login_required
def api_graficos():
    # Verifica se o usuário é administrador
    if not current_user.is_admin:
        return jsonify({"error": "Acesso negado. Você não é um administrador."}), 403

    # Obtém as datas da requisição
    data_inicial_str = request.args.get('dataInicial')
    data_final_str = request.args.get('dataFinal')

    # Verifica se as datas foram fornecidas
    if not data_inicial_str or not data_final_str:
        return jsonify({"error": "Datas inicial e final são obrigatórias."}), 400

    try:
        # Converte as strings para objetos datetime
        data_inicial = datetime.strptime(data_inicial_str, '%Y-%m-%dT%H:%M')
        data_final = datetime.strptime(data_final_str, '%Y-%m-%dT%H:%M')
    except ValueError as e:
        return jsonify({"error": f"Formato de data inválido. Use o formato 'YYYY-MM-DDTHH:MM'. Erro: {str(e)}"}), 400

    # Filtra os pedidos no intervalo de datas
    pedidos = Pedido.query.filter(Pedido.data_pedido.between(data_inicial, data_final)).all()

    # Processa os dados para os gráficos
    dados = {
        'pedidos': [{
            'data_pedido': p.data_pedido.strftime('%Y-%m-%dT%H:%M'),  # Formato ISO 8601
            'quantidade': len(p.itens),
            'total': p.total
        } for p in pedidos],
        'cidadesBairros': obter_cidades_bairros(pedidos),
        'usuariosPedidos': obter_usuarios_mais_pedidos(pedidos),
        'diasMeses': obter_dias_meses_mais_pedidos(pedidos),
        'entregasRetiradas': obter_entregas_retiradas(pedidos)
    }

    return jsonify(dados)

# Função para agrupar pedidos por cidade e bairro
def obter_cidades_bairros(pedidos):
    cidades_bairros = {}
    for pedido in pedidos:
        usuario = Usuario.query.get(pedido.usuario_id)
        if usuario:
            chave = f"{usuario.cidade} - {usuario.bairro}"
            if chave not in cidades_bairros:
                cidades_bairros[chave] = 0
            cidades_bairros[chave] += 1
    return [{"cidade": chave.split(" - ")[0], "bairro": chave.split(" - ")[1], "pedidos": valor} 
            for chave, valor in cidades_bairros.items()]

# Função para obter os usuários que mais fizeram pedidos
def obter_usuarios_mais_pedidos(pedidos):
    usuarios_pedidos = {}
    for pedido in pedidos:
        usuario = Usuario.query.get(pedido.usuario_id)
        if usuario:
            if usuario.nome not in usuarios_pedidos:
                usuarios_pedidos[usuario.nome] = 0
            usuarios_pedidos[usuario.nome] += 1
    return [{"nome": nome, "pedidos": pedidos} for nome, pedidos in usuarios_pedidos.items()]

# Função para agrupar pedidos por dia e mês
def obter_dias_meses_mais_pedidos(pedidos):
    dias_pedidos = {}
    meses_pedidos = {}
    for pedido in pedidos:
        dia = pedido.data_pedido.strftime('%A')  # Dia da semana (ex: "Segunda")
        mes = pedido.data_pedido.strftime('%B')  # Mês (ex: "Janeiro")
        
        if dia not in dias_pedidos:
            dias_pedidos[dia] = 0
        dias_pedidos[dia] += 1
        
        if mes not in meses_pedidos:
            meses_pedidos[mes] = 0
        meses_pedidos[mes] += 1
    
    return [{"dia": dia, "pedidos": pedidos} for dia, pedidos in dias_pedidos.items()]

# Função para contar entregas e retiradas
def obter_entregas_retiradas(pedidos):
    entregas = 0
    retiradas = 0
    for pedido in pedidos:
        if pedido.local_retirada == 'Entrega na Residencia':
            entregas += 1
        else:
            retiradas += 1
    return {"entregas": entregas, "retiradas": retiradas}

# Função para agrupar pedidos por cidade e bairro
def obter_cidades_bairros(pedidos):
    cidades_bairros = {}
    for pedido in pedidos:
        usuario = Usuario.query.get(pedido.usuario_id)
        if usuario:
            chave = f"{usuario.cidade} - {usuario.bairro}"
            if chave not in cidades_bairros:
                cidades_bairros[chave] = 0
            cidades_bairros[chave] += 1
    return [{"cidade": chave.split(" - ")[0], "bairro": chave.split(" - ")[1], "pedidos": valor} 
            for chave, valor in cidades_bairros.items()]

# Função para obter os usuários que mais fizeram pedidos
def obter_usuarios_mais_pedidos(pedidos):
    usuarios_pedidos = {}
    for pedido in pedidos:
        usuario = Usuario.query.get(pedido.usuario_id)
        if usuario:
            if usuario.nome not in usuarios_pedidos:
                usuarios_pedidos[usuario.nome] = 0
            usuarios_pedidos[usuario.nome] += 1
    return [{"nome": nome, "pedidos": pedidos} for nome, pedidos in usuarios_pedidos.items()]

# Função para agrupar pedidos por dia e mês
def obter_dias_meses_mais_pedidos(pedidos):
    dias_pedidos = {}
    meses_pedidos = {}
    for pedido in pedidos:
        dia = pedido.data_pedido.strftime('%A')  # Dia da semana (ex: "Segunda")
        mes = pedido.data_pedido.strftime('%B')  # Mês (ex: "Janeiro")
        
        if dia not in dias_pedidos:
            dias_pedidos[dia] = 0
        dias_pedidos[dia] += 1
        
        if mes not in meses_pedidos:
            meses_pedidos[mes] = 0
        meses_pedidos[mes] += 1
    
    return [{"dia": dia, "pedidos": pedidos} for dia, pedidos in dias_pedidos.items()]

# Função para contar entregas e retiradas
def obter_entregas_retiradas(pedidos):
    entregas = 0
    retiradas = 0
    for pedido in pedidos:
        if pedido.local_retirada == 'Entrega na Residencia':
            entregas += 1
        else:
            retiradas += 1
    return {"entregas": entregas, "retiradas": retiradas}

@app.route('/admin/graficos')
@login_required
def graficos():
    if not current_user.is_admin:
      #  flash('Acesso negado. Você não é um administrador.', 'erro')
        return redirect(url_for('index'))
    return render_template('api_graficos.html')


# Rota para o painel do administrador (cadastro de produtos)
@app.route('/admin/produtos', methods=['GET', 'POST'])
@login_required
def admin_produtos():
    if not current_user.is_admin:
    #    flash('Acesso negado. Você não é um administrador.', 'erro')
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Verifica se um produto existente foi selecionado
        produto_id = request.form.get('produto_existente')
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        preco = float(request.form.get('preco'))
        estoque = int(request.form.get('estoque'))
        foto = None

        # Upload de foto
        if 'foto' in request.files:
            file = request.files['foto']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                foto = f"uploads/{filename}"

        if produto_id:  # Atualiza um produto existente
            produto = Produto.query.get_or_404(produto_id)
            produto.nome = nome or produto.nome
            produto.descricao = descricao or produto.descricao
            produto.preco = preco
            produto.estoque += estoque  # Soma ao estoque existente
            produto.foto = foto or produto.foto  # Mantém a foto anterior se nenhuma nova for enviada
            db.session.commit()
          #  flash('Estoque atualizado com sucesso!', 'sucesso')
        else:  # Cadastra um novo produto
            novo_produto = Produto(
                nome=nome,
                descricao=descricao,
                preco=preco,
                estoque=estoque,
                foto=foto
            )
            db.session.add(novo_produto)
            db.session.commit()
         #   flash('Produto cadastrado com sucesso!', 'sucesso')

        return redirect(url_for('admin_produtos'))

    # Recupera todos os produtos para preencher a lista suspensa
    produtos = Produto.query.all()
    return render_template('admin_produtos.html', produtos=produtos)


@app.route('/admin/base_admin')
@login_required
def base_admin():
    if not current_user.is_admin:
        flash('Acesso negado!', 'erro')
        return redirect(url_for('base_admin'))

@app.route('/admin_usuarios')
@login_required
def admin_usuarios():
    if not current_user.is_admin:
    #    flash('Acesso negado. Você não é um administrador.', 'erro')
        return redirect(url_for('index'))
    
    usuarios = Usuario.query.all()  # Recupera todos os usuários
    return render_template('admin_usuarios.html', usuarios=usuarios)

@app.route('/admin/detalhes_admin')
@login_required
def detalhes_admin():
    if not current_user.is_admin:
    #    flash('Acesso negado. Você não é um administrador.', 'erro')
        return redirect(url_for('index'))

    # Recupera o último pedido do administrador logado
    ultimo_pedido = (
        Pedido.query
        .filter_by(usuario_id=current_user.id)
        .order_by(Pedido.data_pedido.desc())
        .first()
    )

    # Calcula a diferença de dias desde o último pedido
    if current_user.ultimo_pedido:
        diferenca = datetime.utcnow() - current_user.ultimo_pedido
        dias_sem_pedido = diferenca.days
    else:
        dias_sem_pedido = None

    # Detalhes do último pedido (se existir)
    itens_pedido = []
    forma_entrega = None
    if ultimo_pedido:
        itens_pedido = ultimo_pedido.itens  # Itens do último pedido
        forma_entrega = "Entrega na Residência" if ultimo_pedido.local_retirada == "Entrega na Residencia" else "Retirada"

    # Passa os dados para o template
    return render_template(
        'detalhes_admin.html',
        usuario=current_user,
        dias_sem_pedido=dias_sem_pedido,
        ultimo_pedido=ultimo_pedido,
        itens_pedido=itens_pedido,
        forma_entrega=forma_entrega
    )


@app.route('/admin/detalhes_usuario/<int:user_id>')
@login_required
def detalhes_usuario(user_id):
    if not current_user.is_admin:
    #    flash('Acesso negado. Você não é um administrador.', 'erro')
        return redirect(url_for('index'))
    
    # Recupera o usuário pelo ID
    usuario = Usuario.query.get_or_404(user_id)
    
    # Recupera o último pedido do usuário
    ultimo_pedido = (
        Pedido.query
        .filter_by(usuario_id=usuario.id)
        .order_by(Pedido.data_pedido.desc())
        .first()
    )
    
    # Calcula a diferença de dias desde o último pedido
    if usuario.ultimo_pedido:
        diferenca = datetime.utcnow() - usuario.ultimo_pedido 
        dias_sem_pedido = diferenca.days
    else:
        dias_sem_pedido = None
    
    # Define a forma de entrega (se houver um último pedido)
    forma_entrega = "Entrega na Residência" if ultimo_pedido and ultimo_pedido.local_retirada == "Entrega na Residencia" else "Retirada"
    
    # Recupera os itens do último pedido (se houver)
    itens_pedido = ultimo_pedido.itens if ultimo_pedido else []
    
    # Passa os dados para o template
    return render_template(
        'detalhes_usuario.html',
        usuario=usuario,
        ultimo_pedido=ultimo_pedido,
        dias_sem_pedido=dias_sem_pedido,
        forma_entrega=forma_entrega,
        itens_pedido=itens_pedido
    )

@app.route('/admin/usuarios_inativos')
@login_required
def usuarios_inativos():
    if not current_user.is_admin:
    #    flash('Acesso negado. Você não é um administrador.', 'erro')
        return redirect(url_for('index'))
    
    # Calcula a data limite (30 dias atrás)
    data_limite = datetime.utcnow() - timedelta(days=15)
    
    # Consulta os usuários que não realizaram pedidos nos últimos 30 dias
    usuarios_inativos = (
        Usuario.query
        .outerjoin(Pedido, Usuario.id == Pedido.usuario_id)  # Junção com a tabela de pedidos
        .filter(
            (Pedido.data_pedido == None) | (Pedido.data_pedido < data_limite)  # Sem pedidos ou último pedido > 30 dias
        )
        .distinct()  # Remove duplicatas
        .all()
    )
    
    # Passa os dados para o template
    return render_template('usuarios_inativos.html', usuarios=usuarios_inativos)

# Cria o banco de dados e as tabelas
with app.app_context():
    db.create_all()

if __name__ == '__main__':
   #app.run(debug=True)
    
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
    