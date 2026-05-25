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
VERSAO_CHROME  =  131
NOME_ARQUIVO   = "CAUC_Extrato_Sobral_CE.pdf"


# ──────────────────────────────────────────────────────────────

def criar_driver() -> uc.Chrome:
    os.makedirs(PASTA_DOWNLOAD, exist_ok=True)

    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # ✅ Sem --disable-gpu, --disable-extensions, --disable-infobars
    # ✅ Sem --disable-blink-features=AutomationControlled (o uc já cuida disso)
    # ✅ Sem --user-agent manual (deixa o Chrome definir o próprio)
    # ✅ Sem --window-size fixo (deixa --start-maximized agir)

    driver = uc.Chrome(options=options, version_main=VERSAO_CHROME)

    # ❌ REMOVER o execute_cdp_cmd com o script de navigator.webdriver
    # Ele paradoxalmente DENUNCIA automação ao redefinir a propriedade

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
    # Pequena pausa humana após carregar a página
    time.sleep(random.uniform(1.5, 3.0))
    print("    OK - Pagina carregada.")


def passo_2_buscar_e_selecionar_sobral(driver):
    print("\n[2/4] Buscando e selecionando Sobral/CE...")

    WebDriverWait(driver, 25).until(
        lambda d: len(d.find_elements(By.CSS_SELECTOR, "input[type='text']")) > 0
    )
    aguardar_angular(driver)

    # Simula comportamento humano antes de interagir
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

    # Simula movimento do mouse até a opção antes de clicar
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

    # Tenta usar o nome do arquivo do header Content-Disposition
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

    # ── Abre o PDF com o visualizador padrão do sistema ──
    print("\n    Abrindo o PDF...")
    try:
        if sys.platform.startswith("win"):
            os.startfile(caminho)
        elif sys.platform.startswith("darwin"):
            subprocess.run(["open", caminho], check=True)
        else:  # Linux
            subprocess.run(["xdg-open", caminho], check=True)
    except Exception as e:
        print(f"    Nao foi possivel abrir automaticamente: {e}")
        print(f"    Abra manualmente em: {caminho}")


# ──────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  CAUC Tesouro - Extrato PDF - Sobral/CE")
    print("=" * 60)

    driver = criar_driver()

    try:
        passo_1_abrir_site(driver)
        passo_2_buscar_e_selecionar_sobral(driver)
        token = passo_3_resolver_hcaptcha(driver)
        try:
            driver.quit()
        except Exception:
            pass
        print("\n    Navegador encerrado. Baixando PDF...")
        passo_4_baixar_pdf(token)
        print("\nConcluido!")

    except RuntimeError as e:
        print(f"\nERRO: {e}")
        try:
            driver.quit()
        except Exception:
            pass
        sys.exit(1)

    except KeyboardInterrupt:
        print("\nInterrompido pelo usuario.")
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    main()