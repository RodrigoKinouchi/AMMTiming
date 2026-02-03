# AMM Timing - Análise de Dados de Corrida

Aplicativo Streamlit para análise de dados de treino e corrida da equipe Amattheis.

## 🚀 Deploy no Streamlit Sharing

### Requisitos
- Repositório GitHub público (para plano gratuito)
- Arquivo principal: `main.py`
- `requirements.txt` com todas as dependências

### Configuração
1. Faça push do código para um repositório GitHub público
2. Acesse [share.streamlit.io](https://share.streamlit.io)
3. Conecte seu repositório
4. O Streamlit detectará automaticamente o `main.py`

### ⚠️ Importante sobre Privacidade

**Streamlit Community Cloud (Gratuito):**
- ✅ Requer repositório **público** no GitHub
- ⚠️ Qualquer pessoa pode ver seu código no GitHub
- ✅ Mas o acesso ao aplicativo pode ser restrito (apenas pessoas com o link)

**Streamlit Cloud Team (Pago):**
- ✅ Permite repositório **privado**
- ✅ Controle de acesso ao aplicativo
- 💰 Requer assinatura paga

### Estrutura do Projeto
```
AMMTiming/
├── main.py                 # Arquivo principal
├── requirements.txt        # Dependências
├── functions/
│   ├── constants.py       # Constantes e configurações
│   ├── database.py        # Módulo de banco de dados SQLite
│   └── utils.py           # Funções utilitárias
├── images/                 # Imagens (logos, capas)
│   ├── capa.png
│   ├── capa2.png
│   ├── carro.png
│   └── stocklogo.png
└── .streamlit/
    └── config.toml        # Configurações do Streamlit
```

### Banco de Dados
- O banco SQLite (`amm_timing.db`) é criado automaticamente
- No Streamlit Sharing, o banco é **compartilhado entre todos os usuários**
- Todos verão as mesmas sessões salvas

### Notas
- O arquivo `.gitignore` já está configurado para ignorar `*.db`
- Não faça commit do banco de dados no GitHub
