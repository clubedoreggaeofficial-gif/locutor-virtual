import os
import re
import asyncio
import ftplib
import requests
import edge_tts
from flask import Flask

app = Flask(__name__)

STREAM_URL = os.environ.get("STREAM_URL")
FTP_HOST = os.environ.get("FTP_HOST")
FTP_USER = os.environ.get("FTP_USER")
FTP_PASS = os.environ.get("FTP_PASS")
VOZ = "pt-BR-AntonioNeural"

def pegar_musica_atual():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(STREAM_URL, headers=headers, timeout=10)
        limpo = re.sub('<[^<]+?>', '', resp.text).strip()
        partes = limpo.split(",")
        musica = ",".join(partes[6:]).strip()
        return musica if musica else "nossa seleção especial"
    except Exception as e:
        print(f"Erro ao ler stream: {e}")
        return "a melhor programação da web"

async def criar_audio(texto, arquivo_saida):
    communicate = edge_tts.Communicate(texto, VOZ)
    await communicate.save(arquivo_saida)

def enviar_ftp(arquivo_local, nome_remoto):
    with ftplib.FTP(FTP_HOST) as ftp:
        ftp.login(FTP_USER, FTP_PASS)
        ftp.cwd("locutor")
        with open(arquivo_local, "rb") as f:
            ftp.storbinary(f"STOR {nome_remoto}", f)

@app.route("/")
def home():
    return "Locutor Virtual Online!"

@app.route("/gerar")
def gerar_locucao():
    musica = pegar_musica_atual()
    roteiro = f"Você está curtindo {musica}. Continue ligado aqui na nossa programação!"
    
    arquivo_mp3 = "locucao_atual.mp3"
    asyncio.run(criar_audio(roteiro, arquivo_mp3))
    enviar_ftp(arquivo_mp3, arquivo_mp3)
    
    return f"Sucesso! Locução gerada para: {musica}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
