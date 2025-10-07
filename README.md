# AutoCronograma_Estrategia

Extrator de conteúdo para cursos do Estratégia. Este repositório contém o script `Extrair.py` que usa Playwright para automatizar extração de títulos de disciplinas e aulas.

## Estrutura
- `Extrair.py` — script principal (já presente no diretório).
- `requirements.txt` — dependências Python (CustomTkinter e Playwright).
- `.gitignore` — arquivos e pastas ignorados pelo Git.

## Como usar (resumo rápido)
1. Criar e ativar um ambiente virtual Python (recomendado):

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
```

2. Instalar dependências:

```powershell
pip install -r requirements.txt
python -m playwright install
```

3. Executar o script:

```powershell
python Extrair.py
```

Na primeira execução, a GUI abrirá um navegador para login manual (ou utilizar o arquivo `session_state.json` para pular o login em execuções futuras).

## Criar repositório no GitHub
Você pode criar o repositório remoto e enviar o commit inicial de duas formas:

- Usando GitHub CLI (recomendado se estiver autenticado):

```powershell
gh repo create <usuario>/<repo> --public --source=. --remote=origin --push
```

- Usando a interface web: crie um repositório vazio e, então, rode:

```powershell
git remote add origin https://github.com/<usuario>/<repo>.git

git push -u origin main
```

Substitua `<usuario>` e `<repo>` conforme necessário.

## Observações
- O arquivo `session_state.json` contém estado de sessão (cookies); remova-o para forçar login com outra conta.
- Se preferir que eu crie o repositório remoto agora, informe o nome do repositório e se deve ser público ou privado, e se deseja usar uma token (entregue com segurança) ou o `gh` já autenticado no sistema.
