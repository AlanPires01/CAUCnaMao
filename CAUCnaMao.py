"""
Script para baixar o Extrato CAUC de Sobral/CE.
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

ROXO    = "#534AB7"
ROXO_BG = "#EEEDFE"
CINZA   = "#888780"
BRANCO  = "#FFFFFF"
FUNDO   = "#F1EFE8"


class SplashCAUC:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("CAUCnaMão")
        self.root.configure(bg=FUNDO)
        self.root.resizable(False, False)
        self.root.overrideredirect(True)

        self._centralizar(600, 350)
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

        # ── Logo ───────────────────────────────────────────────
        logo_path = os.path.join(BASE_DIR, "assets", "logo.png")
        self._logo_img = None
        if os.path.exists(logo_path):
            try:
                img_raw = tk.PhotoImage(file=logo_path)

                # Calcula zoom/subsample para chegar em 85x63
                orig_w = img_raw.width()
                orig_h = img_raw.height()

                scale_w = 341 / orig_w
                scale_h = 253 / orig_h
                scale   = min(scale_w, scale_h)

                if scale < 1:
                    fator = max(1, round(1 / scale))
                    self._logo_img = img_raw.subsample(fator, fator)
                elif scale > 1:
                    fator = max(1, round(scale))
                    self._logo_img = img_raw.zoom(fator, fator)
                else:
                    self._logo_img = img_raw

                tk.Label(card, image=self._logo_img, bg=BRANCO).pack(pady=(30, 10))
            except Exception:
                pass

        if self._logo_img is None:
            tk.Label(card, text="CAUCnaMão", font=("Segoe UI", 16, "bold"),
                     bg=BRANCO, fg="#1a1a1a").pack(pady=(40, 10))

        # ── Spinner + texto ────────────────────────────────────
        linha = tk.Frame(card, bg=BRANCO)
        linha.pack(pady=(20, 30))

        self.canvas_spin = tk.Canvas(linha, width=20, height=20, bg=BRANCO, highlightthickness=0)
        self.canvas_spin.pack(side="left", padx=(0, 10))
        self.canvas_spin.create_oval(2, 2, 18, 18, outline=ROXO_BG, width=2)
        self.arco = self.canvas_spin.create_arc(2, 2, 18, 18, start=90, extent=270,
                                                outline=ROXO, width=2, style="arc")

        tk.Label(linha, text="Executando CAUC...", font=("Segoe UI", 11),
                 bg=BRANCO, fg=CINZA).pack(side="left")

    def _animar_spinner(self, angulo):
        self.canvas_spin.itemconfig(self.arco, start=angulo)
        self._anim_id = self.root.after(30, self._animar_spinner, (angulo - 10) % 360)

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

    # Aguarda o iframe aparecer no DOM
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "iframe[src*='hcaptcha']")
            )
        )
    except TimeoutException:
        raise RuntimeError("Iframe do hCaptcha nao encontrado.")

    # Rola até o iframe para tirar o header do caminho
    iframe_externo = driver.find_element(By.CSS_SELECTOR, "iframe[src*='hcaptcha']")
    driver.execute_script(
        "arguments[0].scrollIntoView({block: 'center', inline: 'center'});",
        iframe_externo
    )
    time.sleep(1.5)

    # Entra no iframe
    driver.switch_to.frame(iframe_externo)
    print("    Iframe encontrado. Clicando no checkbox...")

    checkbox = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#checkbox"))
    )

    # Tenta clique normal primeiro; se falhar, usa JavaScript
    try:
        checkbox.click()
    except Exception:
        driver.execute_script("arguments[0].click();", checkbox)

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

    print(f"\n    SUCESSO! PDF salvo em: {caminho}")
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

    def executar():
        splash.fechar(delay_ms=2000)

        driver = None
        try:
            driver = criar_driver()
            passo_1_abrir_site(driver)
            passo_2_buscar_e_selecionar_sobral(driver)
            token = passo_3_resolver_hcaptcha(driver)
            try: driver.quit()
            except Exception: pass
            passo_4_baixar_pdf(token)

        except Exception as e:
            print(f"\n  ERRO: {e}")
            try: driver.quit()
            except Exception: pass

    t = threading.Thread(target=executar, daemon=False)  # ← daemon=False
    t.start()
    splash.iniciar()  # trava até a splash fechar (2s)
    t.join()          # ← aguarda o script terminar antes de sair

if __name__ == "__main__":
    main()
