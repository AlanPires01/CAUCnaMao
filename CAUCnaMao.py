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
import requests
import subprocess

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


URL            = "https://cauc.tesouro.gov.br/ng/#/extrato/ente/filtro"
URL_PDF        = "https://cauc.tesouro.gov.br/ng/extrato-cauc/pdfa"
BUSCA_TEXTO    = "sobral"
CNPJ_ALVO      = "07.598.634/0001-37"
CIDADE_ALVO    = "Sobral"
ID_EXTRATO     = "1"
ID_ENTE        = "1083"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_DOWNLOAD = BASE_DIR
VERSAO_CHROME  = 147
NOME_ARQUIVO   = "CAUC_Extrato_Sobral_CE.pdf"


# ──────────────────────────────────────────────────────────────

def criar_driver() -> uc.Chrome:
    os.makedirs(PASTA_DOWNLOAD, exist_ok=True)

    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")

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


def digitar_no_input(driver, elemento, texto):
    try:
        elemento.click()
        time.sleep(0.4)
        elemento.send_keys(Keys.CONTROL + "a")
        elemento.send_keys(texto)
        time.sleep(1.2)
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
    print("    OK - Pagina carregada.")


def passo_2_buscar_e_selecionar_sobral(driver):
    print("\n[2/4] Buscando e selecionando Sobral/CE...")

    WebDriverWait(driver, 25).until(
        lambda d: len(d.find_elements(By.CSS_SELECTOR, "input[type='text']")) > 0
    )
    aguardar_angular(driver)

    campo = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='text']"))
    )

    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", campo)
    time.sleep(0.5)

    if not digitar_no_input(driver, campo, BUSCA_TEXTO):
        raise RuntimeError("Nao foi possivel digitar no campo de busca.")

    print(f"    '{BUSCA_TEXTO}' digitado. Aguardando opcoes...")
    time.sleep(2)

    # Seleciona Sobral na lista
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
    time.sleep(0.3)
    opcao.click()
    print(f"    OK - '{CIDADE_ALVO}' selecionado.")
    time.sleep(2)


def passo_3_resolver_hcaptcha(driver):
    """
    Entra no iframe do hCaptcha, clica no checkbox e captura o token
    gerado no campo hcaptcha-response do DOM principal.
    """
    print("\n[3/4] Resolvendo hCaptcha...")

    # Aguarda o iframe do hCaptcha aparecer
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
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", checkbox)
    time.sleep(1)
    driver.execute_script("arguments[0].click();", checkbox)
    time.sleep(3)  # aguarda o token ser gerado

    driver.switch_to.default_content()
    print("    Checkbox clicado. Aguardando token...")

    # Captura o token gerado pelo hCaptcha no campo oculto do DOM
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
        raise RuntimeError(
            "Token hCaptcha nao foi gerado.\n"
            "O captcha pode ter exigido desafio visual — tente novamente."
        )

    print(f"    OK - Token capturado! ({len(token)} chars)")
    return token


def passo_4_baixar_pdf(token: str):
    """Usa requests para baixar o PDF diretamente com o token capturado."""
    print("\n[4/4] Baixando PDF via requests...")

    params = {
        "idExtrato":       ID_EXTRATO,
        "idEnte":          ID_ENTE,
        "hCaptchaResponse": token,
    }

    headers = {
        "Accept":          "application/pdf",
        "Referer":         "https://cauc.tesouro.gov.br/",
        "User-Agent":      "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
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
    cd = resp.headers.get("content-disposition", "")
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
        driver.quit()  # navegador nao e mais necessario
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
