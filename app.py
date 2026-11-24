import os
import re
import random
import asyncio
import ftplib
import requests
import edge_tts
from datetime import datetime, timezone, timedelta
from flask import Flask

app = Flask(__name__)

STREAM_URL = os.environ.get("STREAM_URL")
FTP_HOST = os.environ.get("FTP_HOST")
FTP_USER = os.environ.get("FTP_USER")
FTP_PASS = os.environ.get("FTP_PASS")

def pegar_ultimas_musicas():
    try:
        base_url = STREAM_URL.rsplit("/", 1)
        played_url = f"{base_url}/played.html"
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(played_url, headers=headers, timeout=10)
        
        linhas = re.findall(r'<tr><td>(.*?)</td><td>(.*?)</td>', resp.text)
        musicas = []
        palavras_ignoradas = ["locucao", "maya_", "vinheta", "vns", "sr -", "comercial"]
        
        for hora_t, titulo in linhas:
            titulo_limpo = re.sub('<[^<]+?>', '', titulo).strip()
            titulo_minusculo = titulo_limpo.lower()
            
            # Pula se estiver vazio ou se for vinheta/locução
            if not titulo_limpo or any(p in titulo_minusculo for p in palavras_ignoradas):
                continue
                
            if titulo_limpo not in musicas:
                musicas.append(titulo_limpo)
            if len(musicas) == 3:
                break
                
        if len(musicas) >= 3:
            return f"{musicas}, {musicas} e {musicas}"
        elif len(musicas) == 2:
            return f"{musicas} e {musicas}"
        elif len(musicas) == 1:
            return musicas
    except Exception as e:
        print(f"Erro ao ler histórico: {e}")

    try:
        resp = requests.get(STREAM_URL, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        limpo = re.sub('<[^<]+?>', '', resp.text).strip()
        partes = limpo.split(",")
        musica = ",".join(partes[6:]).strip()
        return musica if musica else "a nossa seleção especial"
    except Exception:
        return "o melhor do reggae"

async def criar_audio(texto, voz, arquivo_saida):
    communicate = edge_tts.Communicate(texto, voz)
    await communicate.save(arquivo_saida)

def atualizar_ftp(arquivo_local, nome_novo):
    ftp = ftplib.FTP()
    ftp.connect(FTP_HOST, 21, timeout=15)
    ftp.login(FTP_USER, FTP_PASS)
    ftp.set_pasv(True)
    ftp.cwd("locutor")
    
    # Apaga qualquer áudio antigo da pasta para o AutoDJ nunca repetir fala velha
    for arq in ftp.nlst():
        if arq.endswith(".mp3"):
            try:
                ftp.delete(arq)
            except Exception:
                pass
                
    if arquivo_local and nome_novo:
        with open(arquivo_local, "rb") as f:
            ftp.storbinary(f"STOR {nome_novo}", f)
    ftp.quit()

@app.route("/")
def home():
    return "Maya Roots Online!"

@app.route("/gerar")
def gerar_locucao():
    fuso_brasilia = timezone(timedelta(hours=-3))
    agora = datetime.now(fuso_brasilia)
    dia_semana = agora.weekday() # 0=Seg a 4=Sex
    hora = agora.hour

    # Somente Segunda a Sexta, das 12h às 16h59 (Programa Disco Reggae)
    if dia_semana <= 4 and (12 <= hora < 17):
        sequencia = pegar_ultimas_musicas()
        voz = "pt-BR-FranciscaNeural"
        frases = [
            f"Aqui é Maya Roots no Disco Reggae, pela Clube do Reggae! Você curtiu na nossa sequência: {sequencia}. E o som não para!",
            f"Você está no Disco Reggae com Maya Roots, na Clube do Reggae! Passaram por aqui: {sequencia}. Continue sintonizado!",
            f"Disco Reggae no ar pela Clube do Reggae! Eu sou Maya Roots e você acabou de ouvir: {sequencia}. Fique ligado!"
        ]
        roteiro = random.choice(frases)
        
        carimbo = agora.strftime("%H%M%S")
        arquivo_mp3 = f"maya_{carimbo}.mp3"
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(criar_audio(roteiro, voz, arquivo_mp3))
        loop.close()
        
        atualizar_ftp(arquivo_mp3, arquivo_mp3)
        if os.path.exists(arquivo_mp3):
            os.remove(arquivo_mp3)
            
        return f"Sucesso! [Maya Roots - Disco Reggae] Sequência lida: {sequencia}"

    # Fora do horário da Maya Roots -> limpa a pasta e fica em silêncio
    atualizar_ftp(None, None)
    return "Fora do horário da Maya Roots (12h às 17h Seg-Sex). Pasta limpa!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
