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

def pegar_musica_atual():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(STREAM_URL, headers=headers, timeout=10)
        limpo = re.sub('<[^<]+?>', '', resp.text).strip()
        partes = limpo.split(",")
        musica = ",".join(partes[6:]).strip()
        return musica if musica else "a nossa seleção especial"
    except Exception as e:
        print(f"Erro ao ler stream: {e}")
        return "o melhor do reggae"

def definir_locutora_e_roteiro(musica):
    # Horário oficial de Brasília (UTC-3)
    fuso_brasilia = timezone(timedelta(hours=-3))
    agora = datetime.now(fuso_brasilia)
    dia_semana = agora.weekday() # 0=Segunda, 1=Terça, 2=Quarta, 3=Quinta, 4=Sexta, 5=Sábado, 6=Domingo
    hora = agora.hour

    # Segunda a Sexta (0 a 4)
    if dia_semana <= 4:
        # Das 12h às 16h59 -> Programa Disco Reggae com Maya Roots (Francisca)
        if 12 <= hora < 17:
            voz = "pt-BR-FranciscaNeural"
            frases = [
                f"Aqui é Maya Roots no Disco Reggae, pela Clube do Reggae! Acabamos de curtir {musica}, e a sequência não para!",
                f"Você está no programa Disco Reggae com Maya Roots, na Clube do Reggae! Rolou agora {musica}. Continue sintonizado com a gente!",
                f"Disco Reggae no ar pela Clube do Reggae! Eu sou Maya Roots e você acabou de ouvir {musica}. Fique ligado!"
            ]
            return voz, random.choice(frases), "Maya Roots - Disco Reggae"

        # Das 17h às 18h59 -> Programa Conexão Jamaica com Ana Rasta (Thalita)
        elif 17 <= hora < 19:
            voz = "pt-BR-ThalitaNeural"
            frases = [
                f"Aqui é Ana Rasta no Conexão Jamaica, na Clube do Reggae! Rolou {musica} e tem muito mais som pesado vindo aí!",
                f"Conexão Jamaica no ar com Ana Rasta, pela Clube do Reggae! Você acabou de ouvir {musica}. Não saia daí!",
                f"Aqui na Clube do Reggae você curte o Conexão Jamaica com Ana Rasta! Passou por aqui {musica}. Continue com a gente!"
            ]
            return voz, random.choice(frases), "Ana Rasta - Conexão Jamaica"

    # Fora desses horários -> Retorna None para não gerar locução
    return None, None, None

async def criar_audio(texto, voz, arquivo_saida):
    communicate = edge_tts.Communicate(texto, voz)
    await communicate.save(arquivo_saida)

def enviar_ftp(arquivo_local, nome_remoto):
    with ftplib.FTP(FTP_HOST) as ftp:
        ftp.login(FTP_USER, FTP_PASS)
        ftp.cwd("locutor")
        with open(arquivo_local, "rb") as f:
            ftp.storbinary(f"STOR {nome_remoto}", f)

def limpar_ftp(nome_remoto):
    with ftplib.FTP(FTP_HOST) as ftp:
        ftp.login(FTP_USER, FTP_PASS)
        ftp.cwd("locutor")
        try:
            ftp.delete(nome_remoto)
        except Exception:
            pass

@app.route("/")
def home():
    return "Locutoras Virtuais Clube do Reggae Online!"

@app.route("/gerar")
def gerar_locucao():
    musica = pegar_musica_atual()
    voz, roteiro, programa = definir_locutora_e_roteiro(musica)
    arquivo_mp3 = "locucao_atual.mp3"
    
    # Se estiver fora do horário dos programas, apaga o áudio do FTP e não fala nada
    if voz is None:
        limpar_ftp(arquivo_mp3)
        return "Fora do horário dos programas (12h às 19h Seg-Sex). Pasta locutor limpa!"
    
    asyncio.run(criar_audio(roteiro, voz, arquivo_mp3))
    enviar_ftp(arquivo_mp3, arquivo_mp3)
    
    return f"Sucesso! [{programa}] Locução gerada para: {musica}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
