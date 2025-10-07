import sys
import subprocess
import os
import threading
import re
import time
from typing import List, Dict, Tuple
from urllib.parse import urljoin 

# --- VERIFICAÇÃO E INSTALAÇÃO DE DEPENDÊNCIAS ---
try:
    import customtkinter as ctk
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Dependências não encontradas. Iniciando a instalação...")
    
    # Lista de pacotes a serem instalados
    packages = ["customtkinter", "playwright"]
    
    # 1. Instalar pacotes usando pip
    try:
        print(f"Instalando: {', '.join(packages)}...")
        # Adiciona '--quiet' para reduzir o output do pip no terminal
        subprocess.check_call([sys.executable, "-m", "pip", "install", *packages], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("Instalação dos pacotes concluída.")
    except Exception as e:
        print(f"Erro ao instalar pacotes: {e}")
        print("Tente executar manualmente: pip install customtkinter playwright")
        sys.exit(1)

    # 2. Instalar os navegadores do Playwright
    try:
        print("Instalando os navegadores do Playwright...")
        subprocess.check_call([sys.executable, "-m", "playwright", "install"])
        print("Instalação dos navegadores concluída.")
    except Exception as e:
        print(f"Erro ao instalar navegadores do Playwright: {e}")
        print("Tente executar manualmente: playwright install")
        sys.exit(1)

    # Força a re-importação após a instalação
    import customtkinter as ctk
    from playwright.sync_api import sync_playwright

# --- CONFIGURAÇÕES GLOBAIS ---
NOME_ARQUIVO_SAIDA = "estrutura_curso_extraida.txt"
# Arquivo para salvar e carregar o estado da sessão (cookies, etc.)
STORAGE_STATE_PATH = "session_state.json"
# Deve ser False para o primeiro login manual. Pode ser True para execuções subsequentes.
HEADLESS_MODE = False 
# ------------------------------

class App(ctk.CTk):
    """Classe principal da aplicação CustomTkinter."""
    
    # --- SELECTORS ESPECÍFICOS PARA O SITE DO ALUNO ---
    DISCIPLINE_CARD_SELECTOR = "div.course-item-wrapper, div[data-testid='course-card'], .v-card.course-card"
    DISCIPLINE_TITLE_LINK_SELECTOR = "a.discipline-title-link, a:has(h4), .course-name a"
    LESSON_TITLE_SELECTOR = "li.lesson-item-wrapper h4, div.lesson-title, div.module-title-wrapper, .lesson-item-title"

    def __init__(self):
        super().__init__()

        # Configuração básica da janela
        self.title("Extrator de Conteúdo - URL Direta")
        self.geometry("500x320")
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        
        # Variável para a URL
        self.course_url = ctk.StringVar(value="https://www.estrategiaconcursos.com.br/app/dashboard/pacote/355801")
        
        # Configurar a grade (grid)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure((0, 1, 2, 3, 4), weight=1) 

        # 1. Título
        self.title_label = ctk.CTkLabel(self, text="Extrator de Conteúdo Estratégia", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="n")

        # 2. Campo de Entrada para a URL
        self.input_label = ctk.CTkLabel(self, text="URL do Pacote (Ex: https://.../pacote/123):")
        self.input_label.grid(row=1, column=0, padx=20, pady=(0, 5), sticky="sw")
        
        self.input_entry = ctk.CTkEntry(self, textvariable=self.course_url, width=400)
        self.input_entry.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="n")

        # 3. Botão de Ação
        self.extract_button = ctk.CTkButton(self, text="Iniciar Extração", command=self.start_extraction_thread)
        self.extract_button.grid(row=3, column=0, padx=20, pady=(10, 10), sticky="n")

        # 4. Mensagem de Status
        self.status_label = ctk.CTkLabel(self, text="")
        self.status_label.grid(row=4, column=0, padx=20, pady=(10, 20), sticky="s")
        
    def start_extraction_thread(self):
        """Inicia a extração em uma nova thread para evitar o congelamento da GUI."""
        url = self.course_url.get().strip()
        if not url or not url.startswith("http"):
            self.update_status("Por favor, insira uma URL válida.", "orange")
            return
            
        self.update_status(f"Iniciando extração de: {url}", "blue")
        self.extract_button.configure(state="disabled")
        
        # Cria e inicia a thread para a raspagem
        thread = threading.Thread(target=self.run_playwright_scraper, args=(url,))
        thread.start()

    def update_status(self, message: str, color: str = "white"):
        """Método seguro para atualizar a label de status da thread principal."""
        self.after(0, lambda: self.status_label.configure(text=message, text_color=color))
        
    def scrape_discipline_lessons(self, page, discipline_url: str) -> List[str]:
        """Navega para a URL da disciplina e extrai os títulos das aulas."""
        try:
            self.update_status(f"  > Acessando disciplina: {discipline_url}", "cyan")
            page.goto(discipline_url, wait_until="domcontentloaded", timeout=30000)
            
            # Tentar expandir o conteúdo, pois as aulas podem estar colapsadas
            try:
                # Seletor para o botão de expandir
                expand_button_xpath = "//button[contains(., 'Expandir todos') or contains(., 'Visualizar conteúdo completo') or contains(., 'Ver tudo') or contains(., 'Expandir')]"
                page.wait_for_selector(expand_button_xpath, timeout=3000)
                page.click(expand_button_xpath)
                page.wait_for_timeout(1000)
            except:
                print("    Botão 'Expandir' não encontrado na página da disciplina.")
            
            # Extrair os títulos das aulas
            lessons = page.query_selector_all(self.LESSON_TITLE_SELECTOR)
            
            lesson_titles = []
            for lesson in lessons:
                title_text = lesson.inner_text().strip()
                # Filtrar textos curtos que não sejam títulos de aula
                if title_text and len(title_text) > 5 and 'aula' in title_text.lower():
                    lesson_titles.append(title_text)
                    
            return lesson_titles
            
        except Exception as e:
            print(f"    AVISO: Falha ao raspar aulas em {discipline_url}. Erro: {e}")
            return [f"ERRO: Não foi possível extrair as aulas. {e.__class__.__name__}"]

    def wait_for_post_login(self, page, timeout: int = 300000) -> bool:
        """Aguarda indicadores que confirmem login bem-sucedido.

        Retorna True se detectar sucesso (URL do dashboard ou seletores típicos),
        caso contrário False após timeout (ms).
        """
        # Seletores que comumente aparecem em páginas de usuário/logadas
        indicators = [
            "h1",
            ".course-title",
            ".course-header",
            ".dashboard-title",
            "nav[data-testid='main-nav']",
            ".user-menu",
            ".dashboard-content",
        ]

        check_interval = 1.0
        elapsed = 0.0
        timeout_s = timeout / 1000.0

        while elapsed < timeout_s:
            try:
                current_url = page.url
                # Verifica padrões de URL do dashboard/app
                if any(pat in current_url for pat in ["/app/dashboard", "/dashboard", "/app/"]):
                    return True

                # Verifica se algum seletor indicador está presente e visível
                for sel in indicators:
                    try:
                        el = page.query_selector(sel)
                        if el and getattr(el, 'is_visible', lambda: True)():
                            return True
                    except Exception:
                        # ignorar erros transitórios ao consultar seletores
                        pass
            except Exception:
                # ignorar erros de leitura de URL
                pass

            time.sleep(check_interval)
            elapsed += check_interval

        return False

    def run_playwright_scraper(self, url: str):
        """Função principal que coordena a extração multi-nível, com gerenciamento de sessão."""
        browser = None
        context = None
        course_structure = [] 
        
        # Verifica se o estado da sessão já existe
        load_state = os.path.exists(STORAGE_STATE_PATH)
        
        try:
            with sync_playwright() as p:
                # A sessão só pode ser carregada se o navegador for lançado primeiro
                browser = p.chromium.launch(headless=HEADLESS_MODE)
                
                # Configura o contexto do navegador
                context_args = {}
                if load_state:
                    # Carrega o estado da sessão (cookies, local storage)
                    context_args["storage_state"] = STORAGE_STATE_PATH

                context = browser.new_context(**context_args)
                page = context.new_page()

                # --- PASSO 1: GERENCIAMENTO DE LOGIN ---
                
                if load_state:
                    self.update_status("Sessão carregada. Pulando login manual.", "green")
                else:
                    self.update_status(f"Abrindo navegador para login manual em: {url}", "orange")
                    
                page.goto(url, wait_until="domcontentloaded") 

                if not load_state:
                    # --- FLUXO DE PRIMEIRO LOGIN MANUAL ---
                    # Instruções para o usuário: não é necessário pressionar ENTER.
                    self.update_status("⚠️ Faça login no navegador aberto. O script detectará automaticamente quando o login for concluído (pode levar alguns minutos).", "yellow")
                    print("\n" + "="*50)
                    print(">>> LOGIN MANUAL NECESSÁRIO. Complete o login no navegador. O script irá detectar automaticamente quando o login for validado. <<<")
                    print("="*50 + "\n")

                    # Timeout aumentado para permitir login manual (padrão 300s / 5 minutos)
                    VALIDATION_TIMEOUT = 300000  # 300 segundos (5 minutos)

                    # Verificação Pós-Login usando heurísticas mais robustas
                    self.update_status("Verificando login e aguardando redirecionamento/elementos da área logada (até 5 minutos)...", "blue")
                    try:
                        ok = self.wait_for_post_login(page, timeout=VALIDATION_TIMEOUT)
                        if not ok:
                            # Salva diagnóstico para análise
                            try:
                                ts = int(time.time())
                                screenshot_path = f"login_timeout_{ts}.png"
                                html_path = f"login_timeout_{ts}.html"
                                page.screenshot(path=screenshot_path, full_page=True)
                                with open(html_path, 'w', encoding='utf-8') as hf:
                                    hf.write(page.content())
                                print(f"Diagnóstico salvo: {screenshot_path}, {html_path}")
                            except Exception as diag_e:
                                print(f"Falha ao salvar diagnóstico de timeout: {diag_e}")

                            self.update_status("Falha no login/validação após o tempo limite. Verifique se você concluiu o login no navegador aberto.", "red")
                            if os.path.exists(STORAGE_STATE_PATH):
                                os.remove(STORAGE_STATE_PATH)
                            raise Exception("Falha na validação pós-login: timeout")

                        # Salva o estado da sessão para uso futuro
                        context.storage_state(path=STORAGE_STATE_PATH)
                        self.update_status("Estado da sessão salvo com sucesso. Próximas extrações serão mais rápidas.", "green")
                    except Exception as check_e:
                        # Em caso de erro, limpa o estado salvo (se existir)
                        if os.path.exists(STORAGE_STATE_PATH):
                            os.remove(STORAGE_STATE_PATH)
                        raise
                
                # Garante que estamos na URL correta após o login/carregamento da sessão
                page.goto(url, wait_until="domcontentloaded")

                # Tenta extrair o título principal do curso (Pacote)
                try:
                    titulo_pacote = page.inner_text("h1").strip()
                except:
                    titulo_pacote = f"Pacote: {url}"

                # --- PASSO 2 & 3: EXTRAIR LINKS E RASPAR AULAS ---
                
                self.update_status("Encontrando as disciplinas...", "blue")
                discipline_elements = page.query_selector_all(self.DISCIPLINE_CARD_SELECTOR)
                
                if not discipline_elements:
                    raise Exception(f"Nenhuma disciplina encontrada com o seletor: {self.DISCIPLINE_CARD_SELECTOR}. Ajuste o seletor.")

                disciplines_to_scrape: List[Tuple[str, str]] = [] 
                
                for element in discipline_elements:
                    try:
                        link_element = element.query_selector(self.DISCIPLINE_TITLE_LINK_SELECTOR)
                        if link_element:
                            discipline_name = link_element.inner_text().strip()
                            discipline_href = link_element.get_attribute("href")
                            
                            if discipline_name and discipline_href:
                                full_url = urljoin(url, discipline_href) 
                                disciplines_to_scrape.append((discipline_name, full_url))
                                # print(f"  - Link Encontrado: {discipline_name}")
                    except Exception as e:
                        print(f"Aviso: Falha ao extrair link de disciplina. Erro: {e}")

                if not disciplines_to_scrape:
                     raise Exception("Nenhum link de disciplina válido encontrado.")

                total_disciplines = len(disciplines_to_scrape)
                for i, (name, discipline_url) in enumerate(disciplines_to_scrape):
                    self.update_status(f"[{i + 1}/{total_disciplines}] Extraindo aulas de: {name}...", "green")
                    lessons = self.scrape_discipline_lessons(page, discipline_url)
                    course_structure.append({"name": name, "lessons": lessons})
                    
                # --- PASSO 4: PROCESSAR E SALVAR ---
                conteudo_formatado = self.formatar_conteudo(titulo_pacote, course_structure)
                
                with open(NOME_ARQUIVO_SAIDA, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(conteudo_formatado))
                
                self.update_status(f"✅ Sucesso! Estrutura salva em: {NOME_ARQUIVO_SAIDA}", "green")

        except Exception as e:
            error_message = f"❌ Erro na extração: {e.__class__.__name__}. Mensagem: {e}"
            self.update_status(error_message, "red")
            print(f"Erro completo: {e}")
            
        finally:
            if context:
                context.close()
            if browser:
                 browser.close()
            self.extract_button.configure(state="normal")
            
    def formatar_conteudo(self, titulo_pacote: str, course_structure: List[Dict]) -> List[str]:
        """Formata a estrutura aninhada no formato Disciplina/Aulas."""
        linhas = []
        linhas.append(f"Pacote/Curso Principal: {titulo_pacote}")
        linhas.append("=" * (len(titulo_pacote) + 26))
        linhas.append("")
        
        for i, discipline in enumerate(course_structure):
            # 1. Título da Disciplina
            linhas.append(f"{i + 1}. Disciplina: {discipline['name']}")
            
            # 2. Aulas
            if discipline.get('lessons'):
                for lesson in discipline['lessons']:
                    # Indentação com 3 espaços e hífen
                    linhas.append(f"   - {lesson}")
            else:
                linhas.append("   [Nenhuma aula encontrada ou erro na extração.]")
            linhas.append("") 
            
        return linhas

if __name__ == "__main__":
    print("Iniciando script. Verificando dependências...")
    
    # Se o arquivo de sessão existir, informa o usuário para que ele possa apagar se precisar logar com outra conta.
    if os.path.exists(STORAGE_STATE_PATH):
        print(f"Sessão anterior encontrada em '{STORAGE_STATE_PATH}'. O login manual será PULADO.")
        print("Para logar com outra conta, apague este arquivo e execute novamente.")

    app = App()
    app.mainloop()
