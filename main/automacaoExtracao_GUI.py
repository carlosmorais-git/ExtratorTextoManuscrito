import cv2
import base64
import requests 
import os
import time
import json
import csv
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


class ExtratorTextoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Extrator de Texto Manuscrito - GPT-4 Vision")
        self.root.geometry("800x700")
        self.root.resizable(True, True)
        
        # Variáveis de configuração
        self.api_key = tk.StringVar()
        self.pasta_selecionada = tk.StringVar()
        self.quantidade = tk.IntVar(value=5)
        self.system_prompt = tk.StringVar(value="Voce e um assistente especializado em extrair textos manuscritos de imagens.")
        self.user_prompt = tk.StringVar(value="Extraia so texto manuscrito desta imagem. Faca um formato de dicionario coloca a chave que o texto representa e o valor que e o texto manuscrito. Caso nao encontre, retorne 'NAO ENCONTRADO'. Atencao: Seja mais preciso os texto manuscrito, datas ou pontuacao. Sem caracteres especiais ou acentos.")
        self.processando = False
        self.resultados = []
        
        # Arquivo de configuração
        self.config_file = os.path.join(os.path.dirname(__file__), "config.json")
        self.carregar_configuracoes()
        
        self.criar_interface()
        
    def carregar_configuracoes(self):
        """Carrega configurações salvas do arquivo JSON"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.api_key.set(config.get("api_key", ""))
                    self.pasta_selecionada.set(config.get("pasta", ""))
                    self.quantidade.set(config.get("quantidade", 5))
                    self.system_prompt.set(config.get("system_prompt", self.system_prompt.get()))
                    self.user_prompt.set(config.get("user_prompt", self.user_prompt.get()))
            except Exception as e:
                print(f"Erro ao carregar configuracoes: {e}")
                
    def salvar_configuracoes(self):
        """Salva configurações no arquivo JSON"""
        config = {
            "api_key": self.api_key.get(),
            "pasta": self.pasta_selecionada.get(),
            "quantidade": self.quantidade.get(),
            "system_prompt": self.system_prompt.get(),
            "user_prompt": self.user_prompt.get()
        }
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Erro ao salvar configuracoes: {e}")
            return False
        
    def criar_interface(self):
        # Notebook (abas)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # ========== ABA HOME ==========
        self.home_frame = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(self.home_frame, text="🏠 Home")
        
        # ========== ABA CONFIGURAÇÕES ==========
        self.config_frame = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(self.config_frame, text="⚙️ Configurações")
        
        self.criar_aba_home()
        self.criar_aba_config()
        
    def criar_aba_home(self):
        """Cria a interface da aba Home"""
        # ========== TÍTULO ==========
        titulo = ttk.Label(
            self.home_frame, 
            text="🔍 Extrator de Texto Manuscrito",
            font=("Segoe UI", 18, "bold")
        )
        titulo.pack(pady=(0, 20))
        
        # ========== SEÇÃO CONFIGURAÇÕES RÁPIDAS ==========
        config_rapida_frame = ttk.LabelFrame(self.home_frame, text="⚡ Configuração Rápida", padding="15")
        config_rapida_frame.pack(fill=tk.X, pady=(0, 15))
        
        qtd_frame = ttk.Frame(config_rapida_frame)
        qtd_frame.pack(fill=tk.X)
        
        ttk.Label(qtd_frame, text="Quantidade de imagens:").pack(side=tk.LEFT)
        spinbox = ttk.Spinbox(qtd_frame, from_=1, to=100, textvariable=self.quantidade, width=10)
        spinbox.pack(side=tk.LEFT, padx=(10, 0))
        
        # Info da pasta atual
        self.pasta_info_home = ttk.Label(config_rapida_frame, text="", foreground="gray")
        self.pasta_info_home.pack(anchor=tk.W, pady=(10, 0))
        self.atualizar_info_pasta()
        
        # ========== BOTÕES DE AÇÃO ==========
        btn_frame = ttk.Frame(self.home_frame)
        btn_frame.pack(pady=15)
        
        self.btn_processar = ttk.Button(
            btn_frame, 
            text="🚀 Iniciar Extração",
            command=self.iniciar_processamento,
            style="Accent.TButton"
        )
        self.btn_processar.pack(side=tk.LEFT, ipadx=20, ipady=10, padx=(0, 10))
        
        btn_config = ttk.Button(
            btn_frame, 
            text="⚙️ Configurações",
            command=lambda: self.notebook.select(1)
        )
        btn_config.pack(side=tk.LEFT, ipadx=10, ipady=10)
        
        # ========== ÁREA DE LOG ==========
        log_frame = ttk.LabelFrame(self.home_frame, text="📋 Log de Processamento", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(
            log_frame, 
            height=12, 
            font=("Consolas", 10),
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            state=tk.DISABLED
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_text.yview)
        
        # ========== BARRA DE PROGRESSO ==========
        self.progress = ttk.Progressbar(self.home_frame, mode='determinate')
        self.progress.pack(fill=tk.X, pady=(10, 0))
        
        # Status
        self.status_label = ttk.Label(self.home_frame, text="Pronto para processar", foreground="green")
        self.status_label.pack(pady=(5, 0))
        
        # ========== EXPORTAÇÃO ==========
        export_frame = ttk.LabelFrame(self.home_frame, text="📤 Exportar Resultados", padding="10")
        export_frame.pack(fill=tk.X, pady=(10, 0))
        
        export_btn_frame = ttk.Frame(export_frame)
        export_btn_frame.pack()
        
        self.btn_export_json = ttk.Button(
            export_btn_frame, 
            text="💾 Exportar JSON",
            command=self.exportar_json,
            state=tk.DISABLED
        )
        self.btn_export_json.pack(side=tk.LEFT, padx=(0, 10), ipadx=10, ipady=5)
        
        self.btn_export_csv = ttk.Button(
            export_btn_frame, 
            text="📊 Exportar CSV",
            command=self.exportar_csv,
            state=tk.DISABLED
        )
        self.btn_export_csv.pack(side=tk.LEFT, ipadx=10, ipady=5)
        
    def criar_aba_config(self):
        """Cria a interface da aba Configurações"""
        # ========== TÍTULO ==========
        titulo = ttk.Label(
            self.config_frame, 
            text="⚙️ Configurações",
            font=("Segoe UI", 18, "bold")
        )
        titulo.pack(pady=(0, 20))
        
        # ========== SEÇÃO API KEY ==========
        api_frame = ttk.LabelFrame(self.config_frame, text="🔑 Chave da API OpenAI", padding="15")
        api_frame.pack(fill=tk.X, pady=(0, 15))
        
        api_input_frame = ttk.Frame(api_frame)
        api_input_frame.pack(fill=tk.X)
        
        self.api_entry = ttk.Entry(api_input_frame, textvariable=self.api_key, show="*", font=("Consolas", 11))
        self.api_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        self.btn_mostrar = ttk.Button(api_input_frame, text="👁 Mostrar", command=self.toggle_api_key, width=12)
        self.btn_mostrar.pack(side=tk.RIGHT)
        
        self.api_display = ttk.Label(api_frame, text="", font=("Consolas", 10), foreground="gray")
        self.api_display.pack(anchor=tk.W, pady=(10, 0))
        self.api_key.trace_add("write", self.atualizar_api_display)
        self.atualizar_api_display()
        
        # ========== SEÇÃO PASTA ==========
        pasta_frame = ttk.LabelFrame(self.config_frame, text="📁 Pasta de Imagens", padding="15")
        pasta_frame.pack(fill=tk.X, pady=(0, 15))
        
        pasta_input_frame = ttk.Frame(pasta_frame)
        pasta_input_frame.pack(fill=tk.X)
        
        self.pasta_entry = ttk.Entry(pasta_input_frame, textvariable=self.pasta_selecionada, font=("Segoe UI", 10))
        self.pasta_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        btn_selecionar = ttk.Button(pasta_input_frame, text="📂 Selecionar", command=self.selecionar_pasta, width=12)
        btn_selecionar.pack(side=tk.RIGHT)
        
        self.pasta_info = ttk.Label(pasta_frame, text="Nenhuma pasta selecionada", foreground="gray")
        self.pasta_info.pack(anchor=tk.W, pady=(10, 0))
        
        # ========== SEÇÃO PROMPTS ==========
        prompts_frame = ttk.LabelFrame(self.config_frame, text="💬 Prompts", padding="15")
        prompts_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # System Prompt
        ttk.Label(prompts_frame, text="System Prompt:", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        
        system_scroll = ttk.Scrollbar(prompts_frame)
        system_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.system_text = tk.Text(prompts_frame, height=4, font=("Consolas", 10), wrap=tk.WORD)
        self.system_text.pack(fill=tk.X, pady=(5, 15))
        self.system_text.insert("1.0", self.system_prompt.get())
        
        # User Prompt
        ttk.Label(prompts_frame, text="User Prompt:", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        
        self.user_text = tk.Text(prompts_frame, height=6, font=("Consolas", 10), wrap=tk.WORD)
        self.user_text.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        self.user_text.insert("1.0", self.user_prompt.get())
        
        # ========== BOTÕES ==========
        btn_frame = ttk.Frame(self.config_frame)
        btn_frame.pack(pady=(15, 0))
        
        btn_salvar = ttk.Button(
            btn_frame, 
            text="💾 Salvar Configurações",
            command=self.salvar_configs_click
        )
        btn_salvar.pack(side=tk.LEFT, ipadx=15, ipady=8, padx=(0, 10))
        
        btn_resetar = ttk.Button(
            btn_frame, 
            text="🔄 Resetar Padrão",
            command=self.resetar_configs
        )
        btn_resetar.pack(side=tk.LEFT, ipadx=15, ipady=8)
        
    def salvar_configs_click(self):
        """Salva as configurações quando o botão é clicado"""
        # Atualiza as variáveis com o conteúdo dos Text widgets
        self.system_prompt.set(self.system_text.get("1.0", tk.END).strip())
        self.user_prompt.set(self.user_text.get("1.0", tk.END).strip())
        
        if self.salvar_configuracoes():
            self.atualizar_info_pasta()
            messagebox.showinfo("Sucesso", "Configurações salvas com sucesso!")
        else:
            messagebox.showerror("Erro", "Erro ao salvar configurações!")
            
    def resetar_configs(self):
        """Reseta as configurações para os valores padrão"""
        if messagebox.askyesno("Confirmar", "Deseja resetar todas as configurações para o padrão?"):
            self.system_prompt.set("Voce e um assistente especializado em extrair textos manuscritos de imagens.")
            self.user_prompt.set("Extraia so texto manuscrito desta imagem. Faca um formato de dicionario coloca a chave que o texto representa e o valor que e o texto manuscrito. Caso nao encontre, retorne 'NAO ENCONTRADO'. Atencao: Seja mais preciso os texto manuscrito, datas ou pontuacao. Sem caracteres especiais ou acentos.")
            
            self.system_text.delete("1.0", tk.END)
            self.system_text.insert("1.0", self.system_prompt.get())
            
            self.user_text.delete("1.0", tk.END)
            self.user_text.insert("1.0", self.user_prompt.get())
            
            messagebox.showinfo("Sucesso", "Configurações resetadas!")
        
    def toggle_api_key(self):
        """Alterna entre mostrar e ocultar a API key"""
        if self.api_entry.cget('show') == '*':
            self.api_entry.config(show='')
            self.btn_mostrar.config(text="🙈 Ocultar")
        else:
            self.api_entry.config(show='*')
            self.btn_mostrar.config(text="👁 Mostrar")
            
    def atualizar_api_display(self, *args):
        """Atualiza o display mascarado da API key"""
        key = self.api_key.get()
        if len(key) > 10:
            masked = key[:10] + "*" * (len(key) - 10)
            self.api_display.config(text=f"Chave: {masked}")
        elif key:
            self.api_display.config(text=f"Chave: {key}")
        else:
            self.api_display.config(text="")
            
    def selecionar_pasta(self):
        """Abre diálogo para selecionar pasta"""
        pasta = filedialog.askdirectory(title="Selecione a pasta com as imagens")
        if pasta:
            self.pasta_selecionada.set(pasta)
            self.atualizar_info_pasta()
            
    def atualizar_info_pasta(self):
        """Atualiza informações sobre a pasta selecionada"""
        pasta = self.pasta_selecionada.get()
        if pasta and os.path.exists(pasta):
            extensoes = ['.jpg', '.jpeg', '.png']
            imagens = [f for f in os.listdir(pasta) 
                      if os.path.splitext(f)[1].lower() in extensoes]
            texto = f"✅ {len(imagens)} imagens encontradas em: {pasta}"
            if hasattr(self, 'pasta_info'):
                self.pasta_info.config(text=texto, foreground="green")
            if hasattr(self, 'pasta_info_home'):
                self.pasta_info_home.config(text=texto, foreground="green")
        else:
            if hasattr(self, 'pasta_info'):
                self.pasta_info.config(text="❌ Pasta inválida ou não selecionada", foreground="red")
            if hasattr(self, 'pasta_info_home'):
                self.pasta_info_home.config(text="⚠️ Configure a pasta nas Configurações", foreground="orange")
            
    def exportar_json(self):
        """Exporta os resultados para JSON"""
        if not self.resultados:
            messagebox.showwarning("Aviso", "Nenhum resultado para exportar!")
            return
            
        arquivo = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Salvar como JSON"
        )
        
        if arquivo:
            try:
                with open(arquivo, 'w', encoding='utf-8') as f:
                    json.dump(self.resultados, f, ensure_ascii=False, indent=2)
                messagebox.showinfo("Sucesso", f"Resultados exportados para:\n{arquivo}")
                self.log(f"💾 JSON exportado: {arquivo}")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao exportar: {e}")
                
    def exportar_csv(self):
        """Exporta os resultados para CSV"""
        if not self.resultados:
            messagebox.showwarning("Aviso", "Nenhum resultado para exportar!")
            return
            
        arquivo = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Salvar como CSV"
        )
        
        if arquivo:
            try:
                with open(arquivo, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=["imagem", "nome_extraido", "tempo"])
                    writer.writeheader()
                    writer.writerows(self.resultados)
                messagebox.showinfo("Sucesso", f"Resultados exportados para:\n{arquivo}")
                self.log(f"📊 CSV exportado: {arquivo}")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao exportar: {e}")
            
    def log(self, mensagem):
        """Adiciona mensagem ao log"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, mensagem + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        
    def extrair_nome_gpt4(self, imagem_path, api_key, system_prompt=None, user_prompt=None):
        """Versão SIMPLES para testar o fluxo básico"""
        
        # 1. Carregar imagem
        img = cv2.imread(imagem_path)
        if img is None:
            return "ERRO: Imagem não carregada"
        
        # 2. Converter para base64
        _, buffer = cv2.imencode('.jpg', img)
        img_base64 = base64.b64encode(buffer).decode('utf-8')

        MENSAGEM = []

        if system_prompt:
            MENSAGEM.append({
                "role": "system",
                "content": system_prompt
            })
        
        # Usa o user_prompt passado ou um padrão
        prompt_texto = user_prompt if user_prompt else "Extraia o texto manuscrito desta imagem."
        
        MENSAGEM.append({
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": prompt_texto
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{img_base64}",
                        "detail": "high"
                    }
                }
            ]
        })
        
        # 3. Chamar GPT-4 Vision
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-4o-mini",
            "messages": MENSAGEM,
            "max_tokens": 200
        }
        
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=10
            )
            
            data = response.json()
            
            if "error" in data:
                return f"ERRO_API: {data['error']['message']}"
                
            resposta = data["choices"][0]["message"]["content"].strip()
            return resposta
            
        except Exception as e:
            return f"ERRO_API: {str(e)}"
            
    def processar_imagens(self):
        """Processa as imagens em thread separada"""
        api_key = self.api_key.get()
        pasta = self.pasta_selecionada.get()
        quantidade = self.quantidade.get()
        
        # Pegar prompts atualizados
        system_prompt = self.system_text.get("1.0", tk.END).strip()
        user_prompt = self.user_text.get("1.0", tk.END).strip()
        
        self.log("=" * 50)
        self.log("🚀 INICIANDO EXTRAÇÃO DE TEXTO")
        self.log("=" * 50)
        
        # Listar imagens
        extensoes = ['.jpg', '.jpeg', '.png']
        imagens = [f for f in os.listdir(pasta) 
                  if os.path.splitext(f)[1].lower() in extensoes][:quantidade]
        
        total = len(imagens)
        self.log(f"📸 {total} imagens a processar\n")
        
        self.resultados = []
        
        for i, img_nome in enumerate(imagens, 1):
            if not self.processando:
                self.log("\n⛔ Processamento cancelado!")
                break
                
            caminho = os.path.join(pasta, img_nome)
            
            self.log(f"[{i}/{total}] Processando: {img_nome}")
            self.root.update_idletasks()
            
            inicio = time.time()
            nome_extraido = self.extrair_nome_gpt4(caminho, api_key, system_prompt=system_prompt, user_prompt=user_prompt)
            tempo = time.time() - inicio
            
            self.resultados.append({
                "imagem": img_nome,
                "nome_extraido": nome_extraido,
                "tempo": round(tempo, 2)
            })
            
            status = "✅" if "ERRO" not in nome_extraido else "❌"
            self.log(f"   {status} Resultado: {nome_extraido[:100]}...")
            self.log(f"   ⏱️ Tempo: {tempo:.2f}s\n")
            
            # Atualizar progresso
            self.progress['value'] = (i / total) * 100
            self.root.update_idletasks()
            
            time.sleep(0.5)
        
        # Resumo final
        self.log("=" * 50)
        self.log("📊 RESUMO FINAL")
        self.log("=" * 50)
        
        sucesso = sum(1 for r in self.resultados if "ERRO" not in r["nome_extraido"])
        self.log(f"✅ Sucesso: {sucesso}/{total}")
        self.log(f"❌ Erros: {total - sucesso}/{total}")
        
        # Salvar resultados em JSON automaticamente
        if self.resultados:
            json_path = os.path.join(pasta, "resultados_extracao.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(self.resultados, f, ensure_ascii=False, indent=2)
            self.log(f"\n💾 Resultados salvos em: {json_path}")
            
            # Habilitar botões de exportação
            self.btn_export_json.config(state=tk.NORMAL)
            self.btn_export_csv.config(state=tk.NORMAL)
        
        self.processando = False
        self.btn_processar.config(text="🚀 Iniciar Extração", state=tk.NORMAL)
        self.status_label.config(text="✅ Processamento concluído!", foreground="green")
        
        messagebox.showinfo("Concluído", f"Processamento finalizado!\n\n✅ Sucesso: {sucesso}\n❌ Erros: {total - sucesso}")
        
    def iniciar_processamento(self):
        """Inicia o processamento das imagens"""
        # Validações
        if not self.api_key.get():
            messagebox.showerror("Erro", "Por favor, insira a chave da API OpenAI!")
            return
            
        if not self.pasta_selecionada.get():
            messagebox.showerror("Erro", "Por favor, selecione uma pasta com imagens!")
            return
            
        if not os.path.exists(self.pasta_selecionada.get()):
            messagebox.showerror("Erro", "A pasta selecionada não existe!")
            return
            
        # Limpar log
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        # Resetar progresso
        self.progress['value'] = 0
        
        # Iniciar processamento em thread separada
        self.processando = True
        self.btn_processar.config(text="⏳ Processando...", state=tk.DISABLED)
        self.status_label.config(text="🔄 Processando imagens...", foreground="orange")
        
        thread = threading.Thread(target=self.processar_imagens, daemon=True)
        thread.start()


def main():
    root = tk.Tk()
    
    # Estilo
    style = ttk.Style()
    style.theme_use('clam')
    
    app = ExtratorTextoApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
