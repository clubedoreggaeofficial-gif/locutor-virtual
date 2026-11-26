import os
import random
import asyncio
import ftplib
import edge_tts
from datetime import datetime, timezone, timedelta
from flask import Flask

app = Flask(__name__)

FTP_HOST = os.environ.get("FTP_HOST")
FTP_USER = os.environ.get("FTP_USER")
FTP_PASS = os.environ.get("FTP_PASS")

def formatar_hora_falada(agora):
    h = agora.hour
    m = agora.minute
    texto_hora = f"{h} horas" if h != 1 else "1 hora"
    if m == 0:
        return f"{texto_hora} em ponto"
    elif m == 1:
        return f"{texto_hora} e 1 minuto"
    else:
        return f"{texto_hora} e {m} minutos"

def escolher_roteiro_maya(agora):
    hora_str = formatar_hora_falada(agora)
    
    falas = {
        "1": f"Beleza, galera do reggae! Agora são {hora_str}. Sou Maya Roots e, a partir de agora, vamos juntinhos eu daqui e você daí, comandando o programa Disco Reggae que hoje está recheado de pedras pra você curtir! Participe junto com a gente através do nosso site: www ponto clube do reggae ponto com ponto br. E também no RádiosNet: na barra de pesquisa, é só digitar Rádio Clube do Reggae FM e clicar em cima do ícone para ouvir nossa programação! Então vamos lá iniciar nosso Disco Reggae de hoje, trazendo a primeira sequência de pedras!",
        "2": f"Eita maravilha! Já são {hora_str} e nossa primeira sequência de hoje veio com tudo... curtimos aí só pedras de responsa! E já aproveito para mandar um beijo especial a todos que estão ligadinhos com a gente em qualquer lugar do Brasil e do mundo. Abraçar a galera ligada no Conexão Jamaica lá em Teresina, no Piauí, e a galera de Pato Branco, no Paraná... cheiro da Maya Roots pra vocês! Então, vamos com o segundo bloco de hoje!",
        "3": f"Que maravilha, já estamos de volta aqui no Disco Reggae, agora são {hora_str}! E que sequência de pedras, hein? Me diz aí o que achou... demais, né?! Eu achei top demais, só regaço de primeira! Aqui no Disco Reggae é assim, e se tiver Maya Roots no comando aí fica completo! Em breve estarei liberando o WhatsApp pra galera participar... fica ligado nas novidades que logo estarão disponíveis aí pra você, regueiro e regueira que está ligadinho com a gente. Mas vamos deixar de papo e vamos de pedras pra essa galera linda que está ouvindo nosso programa Disco Reggae!",
        "4": f"Opa! Já de volta aqui com o Disco Reggae na minha, na sua Rádio Clube do Reggae FM! Agora são {hora_str} e ficaremos juntinhos até as cinco da tarde, tocando só o melhor do ritmo da Jamaica pra você. E quero sua participação através do site da rádio: www ponto clube do reggae ponto com ponto br! Em breve também estará disponível no aplicativo para Android e iPhone. Mas é hora de reggae pra galera, né? Já falamos demais! Chegando mais cinco pedras e já estarei de volta!"
    }

    # Entre 11h45 e 12h25 usa a Fala 1 (Abertura do programa)
    if (agora.hour == 11 and agora.minute >= 45) or (agora.hour == 12 and agora.minute <= 25):
        return falas["1"], "Fala 1 (Abertura)"
    
    # Nos demais horários do programa (12h26 às 16h59), alterna entre as Falas 2, 3 e 4
    escolha = random.choice(["2", "3", "4"])
    return falas[escolha], f"Fala {escolha}"

async def criar_audio(texto, voz, arquivo_saida):
    communicate = edge_tts.Communicate(texto, voz)
    await communicate.save(arquivo_saida)

def atualizar_ftp(arquivo_local, nome_novo):
    ftp = ftplib.FTP()
    ftp.connect(FTP_HOST, 21, timeout=15)
    ftp.login(FTP_USER, FTP_PASS)
    ftp.set_pasv(True)
    ftp.cwd("locutor")
    
    # Apaga qualquer áudio antigo da pasta
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
    return "OK"

@app.route("/gerar")
def gerar_locucao():
    fuso_brasilia = timezone(timedelta(hours=-3))
    agora = datetime.now(fuso_brasilia)
    dia_semana = agora.weekday() # 0=Seg a 4=Sex
    hora = agora.hour

    # Somente Segunda a Sexta, das 11h45 às 16h59
    if dia_semana <= 4 and ((hora == 11 and agora.minute >= 45) or (12 <= hora < 17)):
        roteiro, qual_fala = escolher_roteiro_maya(agora)
        voz = "pt-BR-FranciscaNeural"
        
        carimbo = agora.strftime("%H%M%S")
        arquivo_mp3 = f"maya_{carimbo}.mp3"
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(criar_audio(roteiro, voz, arquivo_mp3))
        loop.close()
        
        atualizar_ftp(arquivo_mp3, arquivo_mp3)
        if os.path.exists(arquivo_mp3):
            os.remove(arquivo_mp3)
            
        return f"OK: Maya Roots ({qual_fala})"

    # Fora do horário -> limpa a pasta
    atualizar_ftp(None, None)
    return "OK: Fora do horario"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
