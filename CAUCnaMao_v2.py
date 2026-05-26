import os
import sys
import time
import random
import asyncio
import requests
import subprocess

import nodriver as uc

import tkinter as tk
import threading

URL            = "https://cauc.tesouro.gov.br/ng/#/extrato/ente/filtro"
URL_PDF        = "https://cauc.tesouro.gov.br/ng/extrato-cauc/pdfa"
BUSCA_TEXTO    = "sobral"
CNPJ_ALVO      = "07.598.634/0001-37"
CIDADE_ALVO    = "Sobral"
ID_EXTRATO     = "1"
ID_ENTE        = "1083"
BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
PASTA_DOWNLOAD = BASE_DIR
NOME_ARQUIVO   = "CAUC_Extrato_Sobral_CE.pdf"

ROXO    = "#534AB7"
ROXO_BG = "#EEEDFE"
CINZA   = "#888780"
BRANCO  = "#FFFFFF"
FUNDO   = "#F1EFE8"


# ── Splash (igual ao original) ─────────────────────────────────

class SplashCAUC:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("CAUCnaMão")
        self.root.configure(bg=FUNDO)
        self.root.resizable(False, False)
        self.root.attributes("-topmost", False)
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

        logo_path = os.path.join(BASE_DIR, "assets", "logo.png")
        self._logo_img = None
        if os.path.exists(logo_path):
            try:
                img_raw = tk.PhotoImage(file=logo_path)
                orig_w  = img_raw.width()
                orig_h  = img_raw.height()
                scale   = min(341 / orig_w, 253 / orig_h)
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

        linha = tk.Frame(card, bg=BRANCO)
        linha.pack(pady=(20, 30))

        self.canvas_spin = tk.Canvas(linha, width=20, height=20, bg=BRANCO,
                                     highlightthickness=0)
        self.canvas_spin.pack(side="left", padx=(0, 10))
        self.canvas_spin.create_oval(2, 2, 18, 18, outline=ROXO_BG, width=2)
        self.arco = self.canvas_spin.create_arc(2, 2, 18, 18, start=90, extent=270,
                                                outline=ROXO, width=2, style="arc")

        tk.Label(linha, text="Executando CAUC...", font=("Segoe UI", 11),
                 bg=BRANCO, fg=CINZA).pack(side="left")

    def _animar_spinner(self, angulo):
        self.canvas_spin.itemconfig(self.arco, start=angulo)
        self._anim_id = self.root.after(30, self._animar_spinner, (angulo - 10) % 360)

    def fechar(self, delay_ms=500):
        self.root.after(delay_ms, self._destruir)

    def _destruir(self):
        try:
            self.root.after_cancel(self._anim_id)
            self.root.destroy()
        except Exception:
            pass

    def iniciar(self):
        self.root.mainloop()


# ── Helpers ────────────────────────────────────────────────────

async def aguardar_angular(tab, timeout=15):
    """Aguarda o Angular estabilizar via JS."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        estavel = await tab.evaluate(
            "(typeof window.getAllAngularTestabilities === 'undefined') || "
            "window.getAllAngularTestabilities().every(x => x.isStable())"
        )
        if estavel:
            break
        await tab.sleep(0.5)
    await tab.sleep(1)


async def simular_comportamento_humano(tab):
    try:
        for _ in range(random.randint(3, 5)):
            x = random.randint(200, 800)
            y = random.randint(200, 600)
            await tab.mouse_move(x, y)
            await tab.sleep(random.uniform(0.2, 0.5))
    except Exception:
        pass
    await tab.sleep(random.uniform(0.8, 1.8))


async def digitar_humano(tab, elemento, texto):
    """Digita texto caractere a caractere com delay humano.
    Usa JS para limpar e send_keys para digitar (compatível com Angular).
    """
    await elemento.click()
    await asyncio.sleep(random.uniform(0.3, 0.6))

    # Limpa via JS sem tocar no set_value (que falha em text nodes do Angular)
    await tab.evaluate(
        "var el = document.querySelector(\"input[type='text']\");"
        "if(el){ el.value=''; el.dispatchEvent(new Event('input')); }"
    )
    await asyncio.sleep(0.2)

    for char in texto:
        await elemento.send_keys(char)
        await asyncio.sleep(random.uniform(0.08, 0.22))
    await asyncio.sleep(random.uniform(0.8, 1.5))


# ── Passos ─────────────────────────────────────────────────────

async def passo_1_abrir_site(tab):
    print("\n[1/4] Abrindo o portal CAUC...")
    await tab.get(URL)
    await aguardar_angular(tab, timeout=20)
    await tab.sleep(random.uniform(1.5, 2.5))
    print("    OK - Pagina carregada.")


async def passo_2_buscar_e_selecionar_sobral(tab):
    print("\n[2/4] Buscando e selecionando Sobral/CE...")
    await aguardar_angular(tab)
    await simular_comportamento_humano(tab)

    # Localiza o input de busca
    campo = None
    for tentativa in range(3):
        campo = await tab.query_selector("input[type='text']")
        if campo:
            break
        await tab.sleep(2)

    if campo is None:
        raise RuntimeError("Campo de busca nao encontrado.")

    await campo.scroll_into_view()
    await tab.sleep(0.5)
    await digitar_humano(tab, campo, BUSCA_TEXTO)
    print(f"    '{BUSCA_TEXTO}' digitado. Aguardando opcoes...")
    await tab.sleep(2)

    # Tenta encontrar a opção pelo CNPJ ou nome da cidade
    opcao = None
    seletores = [
        f"mat-option",           # genérico; filtramos pelo texto abaixo
    ]

    for _ in range(10):          # polling por até ~5s
        elementos = await tab.query_selector_all("mat-option")
        for el in elementos:
            texto = el.text or ""
            if CNPJ_ALVO in texto or CIDADE_ALVO in texto:
                opcao = el
                break
        if opcao:
            break
        # fallback: find() por texto
        try:
            opcao = await tab.find(CIDADE_ALVO, best_match=True, timeout=1)
        except Exception:
            pass
        if opcao:
            break
        await tab.sleep(0.5)

    if opcao is None:
        raise RuntimeError(f"Opcao '{CIDADE_ALVO}' nao apareceu na lista.")

    await opcao.scroll_into_view()
    await tab.sleep(random.uniform(0.3, 0.6))
    await simular_comportamento_humano(tab)
    await opcao.click()

    print(f"    OK - '{CIDADE_ALVO}' selecionado.")
    await tab.sleep(random.uniform(1.5, 2.5))


async def passo_3_resolver_hcaptcha(tab):
    print("\n[3/4] Resolvendo hCaptcha...")

    # Aguarda o iframe do hCaptcha aparecer
    iframe_elem = None
    for _ in range(30):          # até 15 s
        iframe_elem = await tab.query_selector("iframe[src*='hcaptcha']")
        if iframe_elem:
            break
        await tab.sleep(0.5)

    if iframe_elem is None:
        raise RuntimeError("Iframe do hCaptcha nao encontrado.")

    await iframe_elem.scroll_into_view()
    await tab.sleep(1.5)

    # nodriver: acessa o conteúdo do iframe via get_frames / CDP
    # A forma mais confiável é clicar diretamente nas coordenadas do checkbox
    # dentro do iframe usando mouse_click na posição calculada.
    pos = await iframe_elem.get_position()
    # O checkbox fica aproximadamente no centro-esquerdo do iframe hCaptcha
    # (offset ~30px da esquerda, ~25px do topo do iframe)
    click_x = int(pos.x + 35)
    click_y = int(pos.y + 25)

    print(f"    Clicando no checkbox (x={click_x}, y={click_y})...")
    await tab.mouse_click(click_x, click_y)
    await tab.sleep(3)

    print("    Checkbox clicado. Aguardando token...")

    # Polling pelo token hCaptcha
    token = None
    for _ in range(40):          # até 20 s
        try:
            token = await tab.evaluate(
                "document.querySelector('[name=\"h-captcha-response\"]')?.value || "
                "document.querySelector('[name=\"hcaptcha-response\"]')?.value || ''"
            )
            if token and len(token) > 20:
                break
        except Exception:
            pass
        await tab.sleep(0.5)

    if not token:
        raise RuntimeError(
            "Token hCaptcha nao foi gerado. "
            "O captcha pode ter exigido desafio visual — tente novamente."
        )

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
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
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


# ── Loop assíncrono principal ──────────────────────────────────

async def executar_automacao(resultado: dict):
    browser = None
    try:
        print("    Iniciando nodriver (Chrome sem deteccao)...")
        browser = await uc.start(
            sandbox=False,           # necessário em alguns ambientes Linux/CI
            lang="pt-BR",
        )
        tab = await browser.get(URL)  # já abre na aba principal

        await passo_1_abrir_site(tab)
        await passo_2_buscar_e_selecionar_sobral(tab)
        resultado["token"] = await passo_3_resolver_hcaptcha(tab)

    except Exception as e:
        resultado["erro"] = e
    finally:
        if browser:
            try:
                browser.stop()
            except Exception:
                pass


# ── Entrypoint ─────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  CAUCnaMão - Extrato PDF - Sobral/CE  [nodriver]")
    print("=" * 60)

    splash    = SplashCAUC()
    resultado = {"token": None, "erro": None}

    def thread_async():
        """Roda o loop asyncio numa thread separada para não bloquear o tkinter."""
        asyncio.run(executar_automacao(resultado))
        splash.fechar(delay_ms=500)

    t = threading.Thread(target=thread_async, daemon=True)
    t.start()
    splash.iniciar()   # bloqueia até o splash fechar
    t.join()

    if resultado["erro"]:
        print(f"\n  ERRO: {resultado['erro']}")
        sys.exit(1)

    passo_4_baixar_pdf(resultado["token"])
    print("\nConcluido!")


if __name__ == "__main__":
    main()