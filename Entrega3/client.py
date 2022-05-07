from tkinter import * 
import socket
import os
from time import sleep
from socket import timeout

serverIP = "127.0.0.1"
serverPort = 5001

clientMessage = ""
checksum = 0
seqNumber = 0

def carry(a, b):
    c = a + b
    return (c & 0xffff) + (c >> 16)

def checksum_calc(msg):
    s = 0
    if len(msg) % 2 == 0:
        pass
    else:
        msg = msg + 's'
    for i in range(0, len(msg), 2):
        w = ord(msg[i]) + (ord(msg[i+1]) << 8)
        s = carry(s, w)
    return ~s & 0xffff

def send(gap, destination, checksum):
    clientMessage = input("Sua mensagem: ") # Pegamos entrada do teclado
    checksum = checksum_calc(clientMessage)
    
    # Fazemos envio da mensagem para o outro lado
    udpSocketClient.sendto(f"{checksum}{gap}{clientMessage}{gap}{seqNumber}".encode('utf-8'), destination)

def waitACK(udpSocketClient, gap, seqNumber, clientMessage, checksum):
    # No rdt3.0, ao enviarmos um pacote, ficamos esperando em loop até que chegue o ACK correto.
    # Ou seja, caso chegue o ACK do pacote errado, continuamos esperando. Caso esperemos demais,
    # o temporizador vai estourar, então faremos reenvio do pacote e o reset o temporizador.

    auxWhile = 1 # Variável auxiliar para o loop
    flagWhile = 1 # Flag para controlar o loop
    while auxWhile:
        udpSocketClient.settimeout(0.6) # Definimos o tempo do nosso temporizador
        try:
            isACK, source = udpSocketClient.recvfrom(4096) # Esperamos o ACK do nosso pacote
            isACK = isACK.decode('utf-8') # Decodificamos o pacote recebido

            ackChecksum, ackMessage, ackSeqNumber = isACK.split(gap) # Separamos as informações do pacote, usando a variável 'gap' no split

            # Caso o checksum do ACK e o checksum calculado do ACK recebido sejam diferentes
            # Ou o número de sequência seja do pacote errado, iremos apenas continuar no loop, aguardando o ACK correto
            if ackChecksum != str(checksum_calc(ackMessage)) or ackSeqNumber != str(seqNumber): 
                flagWhile = 1 # Ficamos no loop
            else:
                flagWhile = 0 # Saímos do loop

        except socket.timeout: # Caso o temporizador estoure, fazemos o reenvio da mensagem
            udpSocketClient.sendto(f"{checksum}{gap}{clientMessage}{gap}{seqNumber}".encode('utf-8'), destination)
        else: # Caso recebamos um pacote no "try", checamos se a flagWhile foi alterada
            if flagWhile == 0: # Se é igual a zero, quer dizer que recebemos o ACK correto
                auxWhile = 0 

print("1 - Enviar arquivos para teste")
print(" Obs.: Você precisa ter um arquivo 'teste.txt' na sua máquina")
print("2 - Chat Cliente-Servidor")

option = int(input())
print("-----------------------")
print("")

gap = "<gap>"

if option == 1:

    fileName = "teste.txt"
    fileSize = os.path.getsize(fileName)

    udpSocketClient = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # Socket do cliente para enviar arquivos para o servidor

    destination = (serverIP, serverPort)

    udpSocketClient.connect(destination)
    udpSocketClient.send(f"{fileName}{gap}{fileSize}".encode('utf-8'))


    with open(fileName, "rb") as file_:
        while True:
            bytesRead = file_.read(4096) # Lê os bytes do arquivo

            if not bytesRead: # Se não tem mais bytes, acabou o arquivo, então para de enviar
                print("File sended!")
                udpSocketClient.sendall('file_download_exit'.encode('utf-8'))
                break
            udpSocketClient.sendall(bytesRead) # Sendall é uma variação do socket.send(), só que fica enviando até terminar tudo
            sleep(0.001)

    udpSocketClient.close()
    file_.close()

elif option == 2:

    flag = 1

    udpSocketClient = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # Socket do cliente para enviar mensagens para o servidor

    destination = (serverIP, serverPort) # "Socket" do servidor que o cliente vai enviar mensagem

    while flag == 1:
        
        # Função que captura a entrada do usuário e faz o envio
        send(gap, destination, checksum)
        
        # Função para esperar o ACK / fazer retransmissão
        waitACK(udpSocketClient, gap, seqNumber, clientMessage, checksum)

        # Recebimento da mensagem de "Entendido!"
        pktMessage, source = udpSocketClient.recvfrom(1024) 
        seqNumber = 1 - seqNumber # Fazemos a alteração do número de sequência
        pktMessage = pktMessage.decode('utf-8')

        pktChecksum, pktMessage, pktSeqNumber = pktMessage.split(gap) # Separamos as informações do pacote, usando a variável 'gap' no split
        mainMessage = pktMessage

        # Caso o checksum do "Entendido!" e o checksum calculado do "Entendido!" recebido sejam diferentes
        # vamos pedir a retransmissão com um ACK de número de sequência errado
        if str(checksum_calc(pktMessage)) != pktChecksum:
            message = "ACK"
            check = checksum_calc(message)
            udpSocketClient.sendto(f"{check}{gap}{message}{gap}{1 - seqNumber}".encode('utf-8'), source) # Envio do ACK

            retry, aux = udpSocketClient.recvfrom(1024) # Recebimento de um novo "Entendido!"
            retry = retry.decode('utf-8')

            retryChecksum, retryMessage, retrySeqNumber = retry.split(gap) # Separamos as informações do pacote, usando a variável 'gap' no split
            mainMessage = retryMessage

            # Caso o checksum do "Entendido!" e o checksum calculado do "Entendido!" recebido sejam diferentes novamente
            # vamos avisar com um ACK errado novamente e encerrar a conexão
            if str(checksum_calc(retryMessage)) != retryChecksum:
                udpSocketClient.sendto(f"{check}{gap}{message}{gap}{1 - seqNumber}".encode('utf-8'), source)
                flag = 0
        
        # Se tudo estiver certo, vamos enviar o ACK correto e printar a mensagem do "Entendido!" na tela
        else:
            message = "ACK"
            check = checksum_calc(message)
            udpSocketClient.sendto(f"{check}{gap}{message}{gap}{seqNumber}".encode('utf-8'), source)
            print(source[0], ":", mainMessage)


    udpSocketClient.close()