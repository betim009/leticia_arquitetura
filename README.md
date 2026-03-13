# leticia_arquitetura

## Setup inicial (Streamlit + Pandas)

### 1) Criar ambiente virtual `venv`

```bash
python3 -m venv .venv
```

### 2) Ativar o ambiente virtual

```bash
source .venv/bin/activate
```

### 3) Criar o arquivo `requirements.txt`

```bash
cat > requirements.txt << 'EOF'
streamlit
pandas
EOF
```

### 4) Instalar dependências do `requirements.txt`

```bash
pip install -r requirements.txt
```

### 5) (Opcional) Salvar versões instaladas no `requirements.txt`

```bash
pip freeze > requirements.txt
```

### 6) Rodar o projeto Streamlit

```bash
streamlit run app.py
```
