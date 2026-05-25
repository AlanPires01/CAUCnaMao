"""
Script para baixar o Extrato CAUC de Sobral/CE.

Fluxo:
  1. Abre o navegador e navega para a pagina
  2. Busca e seleciona Sobral/CE
  3. Clica no checkbox do hCaptcha automaticamente
  4. Intercepta o token hCaptchaResponse gerado
  5. Faz o download do PDF diretamente via requests (sem depender do navegador)

Requisitos:
    pip install undetected-chromedriver selenium webdriver-manager requests
"""

import os
import sys
import time
import random
import requests
import subprocess

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import tkinter as tk
import threading

try:
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    print("Dependencia faltando. Execute: pip install selenium webdriver-manager undetected-chromedriver requests")
    sys.exit(1)


URL            = "https://cauc.tesouro.gov.br/ng/#/extrato/ente/filtro"
URL_PDF        = "https://cauc.tesouro.gov.br/ng/extrato-cauc/pdfa"
BUSCA_TEXTO    = "sobral"
CNPJ_ALVO      = "07.598.634/0001-37"
CIDADE_ALVO    = "Sobral"
ID_EXTRATO     = "1"
ID_ENTE        = "1083"
BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
PASTA_DOWNLOAD = BASE_DIR
VERSAO_CHROME  = 131
NOME_ARQUIVO   = "CAUC_Extrato_Sobral_CE.pdf"

ROXO      = "#534AB7"
ROXO_BG   = "#EEEDFE"
VERDE     = "#3B6D11"
CINZA     = "#888780"
BRANCO    = "#FFFFFF"
VERMELHO  = "#A32D2D"
VERM_BG   = "#FCEBEB"
FUNDO     = "#F1EFE8"

PASSOS = [
    "Abrindo portal CAUC",
    "Buscando Sobral/CE",
    "Resolvendo hCaptcha",
    "Baixando PDF",
]

class SplashCAUC:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("CAUCnaMão")
        self.root.configure(bg=FUNDO)
        self.root.resizable(False, False)
        self.root.overrideredirect(True)

        self._centralizar(380, 300)
        self._build()
        self._animar_spinner(0)

    def _centralizar(self, w, h):
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def _build(self):
        card = tk.Frame(self.root, bg=BRANCO, bd=1, relief="solid")
        card.pack(fill="both", expand=True, padx=2, pady=2)

        # ── Cabeçalho ──────────────────────────────────────────
        topo = tk.Frame(card, bg=BRANCO)
        topo.pack(fill="x", padx=20, pady=(20, 10))

        # ── Logo ───────────────────────────────────────────────
        logo_path = os.path.join(BASE_DIR, "assets", "logo.png")
        self._logo_img = None
        if os.path.exists(logo_path):
            try:
                self._logo_img = tk.PhotoImage(file=logo_path)
                tk.Label(topo, image=self._logo_img, bg=BRANCO).pack()
            except Exception:
                pass

        # ── Spinner (exibido apenas se logo não carregar) ──────
        if self._logo_img is None:
            self.canvas_spin = tk.Canvas(topo, width=52, height=52, bg=BRANCO, highlightthickness=0)
            self.canvas_spin.pack()
            self.canvas_spin.create_oval(4, 4, 48, 48, outline=ROXO_BG, width=3)
            self.arco = self.canvas_spin.create_arc(4, 4, 48, 48, start=90, extent=270, outline=ROXO, width=3, style="arc")
            self.canvas_spin.create_oval(14, 14, 38, 38, fill=ROXO_BG, outline="")
            self.canvas_spin.create_text(26, 26, text="↓", font=("Segoe UI", 14), fill=ROXO)
        else:
            # Canvas fake para _animar_spinner não quebrar
            self.canvas_spin = tk.Canvas(topo, width=0, height=0, highlightthickness=0)
            self.arco = self.canvas_spin.create_arc(0, 0, 0, 0, start=0, extent=0, style="arc")

        sep = tk.Frame(card, bg="#E0E0E0", height=1)
        sep.pack(fill="x", padx=0, pady=12)

        # ── Lista de passos ────────────────────────────────────
        self.frame_passos = tk.Frame(card, bg=BRANCO)
        self.frame_passos.pack(fill="x", padx=20)

        self.labels_icone = []
        self.labels_texto = []

        for texto in PASSOS:
            row = tk.Frame(self.frame_passos, bg=BRANCO)
            row.pack(fill="x", pady=3)

            icone = tk.Label(row, text="○", font=("Segoe UI", 11), bg=BRANCO, fg=CINZA, width=2)
            icone.pack(side="left")

            label = tk.Label(row, text=texto, font=("Segoe UI", 10), bg=BRANCO, fg=CINZA, anchor="w")
            label.pack(side="left", fill="x")

            self.labels_icone.append(icone)
            self.labels_texto.append(label)

        # ── Área de erro ───────────────────────────────────────
        self.frame_erro = tk.Frame(card, bg=VERM_BG, bd=1, relief="solid")
        self.lbl_erro_titulo = tk.Label(self.frame_erro, text="", font=("Segoe UI", 9, "bold"), bg=VERM_BG, fg=VERMELHO, anchor="w")
        self.lbl_erro_detalhe = tk.Label(self.frame_erro, text="", font=("Segoe UI", 8), bg=VERM_BG, fg=VERMELHO, anchor="w", wraplength=310, justify="left")

    def _animar_spinner(self, angulo):
        self.canvas_spin.itemconfig(self.arco, start=angulo)
        self._anim_id = self.root.after(30, self._animar_spinner, (angulo - 10) % 360)

    def marcar_concluido(self, indice):
        self.root.after(0, self._set_concluido, indice)

    def marcar_ativo(self, indice):
        self.root.after(0, self._set_ativo, indice)

    def mostrar_erro(self, titulo, detalhe=""):
        self.root.after(0, self._set_erro, titulo, detalhe)

    def _set_concluido(self, i):
        self.labels_icone[i].config(text="✓", fg=VERDE)
        self.labels_texto[i].config(fg=VERDE)

    def _set_ativo(self, i):
        self.labels_icone[i].config(text="●", fg=ROXO)
        self.labels_texto[i].config(fg="#1a1a1a", font=("Segoe UI", 10, "bold"))

    def _set_erro(self, titulo, detalhe):
        self.lbl_erro_titulo.config(text=f"✕  {titulo}")
        self.lbl_erro_detalhe.config(text=detalhe)
        self.lbl_erro_titulo.pack(anchor="w", padx=10, pady=(8, 2))
        if detalhe:
            self.lbl_erro_detalhe.pack(anchor="w", padx=10, pady=(0, 8))
        self.frame_erro.pack(fill="x", padx=20, pady=(10, 8))
        self.root.after(0, self._ajustar_altura)

    def _ajustar_altura(self):
        self.root.update_idletasks()
        h = self.root.winfo_reqheight() + 10
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w = 380
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def fechar(self, delay_ms=1500):
        self.root.after(delay_ms, self._destruir)

    def _destruir(self):
        try:
            self.root.after_cancel(self._anim_id)
            self.root.destroy()
        except Exception:
            pass

    def iniciar(self):
        self.root.mainloop()

# ──────────────────────────────────────────────────────────────

def criar_driver() -> uc.Chrome:
    os.makedirs(PASTA_DOWNLOAD, exist_ok=True)

    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = uc.Chrome(options=options, version_main=VERSAO_CHROME)
    print(f"    Chrome aberto (undetected v{VERSAO_CHROME}).")
    return driver


def aguardar_angular(driver, timeout=15):
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script(
                "return (typeof window.getAllAngularTestabilities === 'undefined') || "
                "window.getAllAngularTestabilities().every(x => x.isStable())"
            )
        )
    except Exception:
        pass
    time.sleep(1)


def simular_comportamento_humano(driver):
    """Movimentos de mouse e pausas aleatórias para parecer humano."""
    try:
        action = ActionChains(driver)
        body   = driver.find_element(By.TAG_NAME, "body")

        for _ in range(random.randint(3, 6)):
            x = random.randint(-200, 200)
            y = random.randint(-100, 100)
            action.move_to_element_with_offset(body, x, y)
            action.pause(random.uniform(0.2, 0.6))

        action.perform()
        time.sleep(random.uniform(1.0, 2.5))
    except Exception:
        pass


def digitar_no_input(driver, elemento, texto):
    """Digita letra por letra com pausas aleatórias para simular humano."""
    try:
        elemento.click()
        time.sleep(random.uniform(0.3, 0.7))
        elemento.send_keys(Keys.CONTROL + "a")
        time.sleep(0.2)

        for char in texto:
            elemento.send_keys(char)
            time.sleep(random.uniform(0.08, 0.25))

        time.sleep(random.uniform(1.0, 2.0))
        if (elemento.get_attribute("value") or "").strip():
            return True
    except Exception:
        pass

    try:
        ActionChains(driver)\
            .move_to_element(elemento).click().pause(0.4)\
            .key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL)\
            .send_keys(texto).perform()
        time.sleep(1.2)
        if (elemento.get_attribute("value") or "").strip():
            return True
    except Exception:
        pass

    return False


# ──────────────────────────────────────────────────────────────

def passo_1_abrir_site(driver):
    print("\n[1/4] Abrindo o portal CAUC...")
    driver.get(URL)
    aguardar_angular(driver, timeout=20)
    time.sleep(random.uniform(1.5, 3.0))
    print("    OK - Pagina carregada.")


def passo_2_buscar_e_selecionar_sobral(driver):
    print("\n[2/4] Buscando e selecionando Sobral/CE...")

    WebDriverWait(driver, 25).until(
        lambda d: len(d.find_elements(By.CSS_SELECTOR, "input[type='text']")) > 0
    )
    aguardar_angular(driver)

    simular_comportamento_humano(driver)

    campo = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='text']"))
    )

    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", campo)
    time.sleep(random.uniform(0.4, 0.8))

    if not digitar_no_input(driver, campo, BUSCA_TEXTO):
        raise RuntimeError("Nao foi possivel digitar no campo de busca.")

    print(f"    '{BUSCA_TEXTO}' digitado. Aguardando opcoes...")
    time.sleep(2)

    xpaths = [
        f"//mat-option[contains(., '{CNPJ_ALVO}')]",
        f"//mat-option[contains(., '{CIDADE_ALVO}')]",
        f"//*[contains(@class,'option') and contains(., '{CIDADE_ALVO}')]",
        f"//*[contains(text(), '{CNPJ_ALVO}')]",
    ]

    opcao = None
    for xpath in xpaths:
        try:
            opcao = WebDriverWait(driver, 8).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            break
        except TimeoutException:
            continue

    if opcao is None:
        raise RuntimeError(f"Opcao '{CIDADE_ALVO}' nao apareceu na lista.")

    driver.execute_script("arguments[0].scrollIntoView(true);", opcao)
    time.sleep(random.uniform(0.3, 0.7))

    simular_comportamento_humano(driver)
    opcao.click()

    print(f"    OK - '{CIDADE_ALVO}' selecionado.")
    time.sleep(random.uniform(1.5, 2.5))


def passo_3_resolver_hcaptcha(driver):
    print("\n[3/4] Resolvendo hCaptcha...")

    try:
        WebDriverWait(driver, 15).until(
            EC.frame_to_be_available_and_switch_to_it(
                (By.CSS_SELECTOR, "iframe[src*='hcaptcha']")
            )
        )
    except TimeoutException:
        raise RuntimeError("Iframe do hCaptcha nao encontrado.")

    print("    Iframe encontrado. Clicando no checkbox...")

    checkbox = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "#checkbox"))
    )

    checkbox.click()
    time.sleep(3)

    driver.switch_to.default_content()
    print("    Checkbox clicado. Aguardando token...")

    token = None
    for _ in range(20):
        try:
            token = driver.execute_script(
                "return document.querySelector('[name=\"h-captcha-response\"]')"
                "?.value || "
                "document.querySelector('[name=\"hcaptcha-response\"]')"
                "?.value || '';"
            )
            if token and len(token) > 20:
                break
        except Exception:
            pass
        time.sleep(0.5)

    if not token:
        raise RuntimeError("Token hCaptcha nao foi gerado.")

    print(f"    OK - Token capturado! ({len(token)} chars)")
    return token


def passo_4_baixar_pdf(token: str):
    """Usa requests para baixar o PDF diretamente com o token capturado."""
    print("\n[4/4] Baixando PDF via requests...")

    params = {
        "idExtrato":        ID_EXTRATO,
        "idEnte":           ID_ENTE,
        "hCaptchaResponse": token,
    }

    headers = {
        "Accept":     "application/pdf",
        "Referer":    "https://cauc.tesouro.gov.br/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/131.0.0.0 Safari/537.36",
    }

    resp = requests.get(URL_PDF, params=params, headers=headers, timeout=30)

    if resp.status_code != 200:
        raise RuntimeError(
            f"Servidor retornou status {resp.status_code}.\n"
            f"Resposta: {resp.text[:200]}"
        )

    if "application/pdf" not in resp.headers.get("content-type", ""):
        raise RuntimeError(
            f"Resposta nao e um PDF. Content-Type: {resp.headers.get('content-type')}\n"
            f"Conteudo: {resp.text[:200]}"
        )

    cd   = resp.headers.get("content-disposition", "")
    nome = NOME_ARQUIVO
    if "filename" in cd:
        import urllib.parse
        parte = cd.split("filename")[-1]
        parte = parte.replace("*=utf-8''", "").replace("=", "").strip().strip('"')
        nome  = urllib.parse.unquote(parte) or NOME_ARQUIVO

    caminho = os.path.join(PASTA_DOWNLOAD, nome)
    with open(caminho, "wb") as f:
        f.write(resp.content)

    print(f"\n    SUCESSO! PDF salvo em:")
    print(f"    {caminho}")
    print(f"    Tamanho: {len(resp.content) / 1024:.1f} KB")

    print("\n    Abrindo o PDF...")
    try:
        if sys.platform.startswith("win"):
            os.startfile(caminho)
        elif sys.platform.startswith("darwin"):
            subprocess.run(["open", caminho], check=True)
        else:
            subprocess.run(["xdg-open", caminho], check=True)
    except Exception as e:
        print(f"    Nao foi possivel abrir automaticamente: {e}")
        print(f"    Abra manualmente em: {caminho}")


# ──────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  CAUCnaMão - Extrato PDF - Sobral/CE")
    print("=" * 60)

    splash = SplashCAUC()
    driver = None

    def executar():
        nonlocal driver
        try:
            driver = criar_driver()

            splash.marcar_ativo(0)
            passo_1_abrir_site(driver)
            splash.marcar_concluido(0)

            splash.marcar_ativo(1)
            passo_2_buscar_e_selecionar_sobral(driver)
            splash.marcar_concluido(1)

            splash.marcar_ativo(2)
            token = passo_3_resolver_hcaptcha(driver)
            splash.marcar_concluido(2)

            try: driver.quit()
            except Exception: pass

            splash.marcar_ativo(3)
            passo_4_baixar_pdf(token)
            splash.marcar_concluido(3)

            splash.fechar(delay_ms=1500)

        except RuntimeError as e:
            msg = str(e)
            splash.mostrar_erro("Falha na automação", msg)
            splash.fechar(delay_ms=5000)
            try: driver.quit()
            except Exception: pass

        except Exception as e:
            splash.mostrar_erro("Erro inesperado", str(e))
            splash.fechar(delay_ms=5000)
            try: driver.quit()
            except Exception: pass

    t = threading.Thread(target=executar, daemon=True)
    t.start()
    splash.iniciar()

if __name__ == "__main__":
    main()