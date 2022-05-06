import socket
import os
import zlib

# def checksum_calculator(data):
#     checksum = zlib.crc32(data)
#     return checksum

# Function to find the Checksum of Sent Message
def findChecksum(SentMessage, k):
   
    # Dividing sent message in packets of k bits.
    c1 = SentMessage[0:k]
    c2 = SentMessage[k:2*k]
    c3 = SentMessage[2*k:3*k]
    c4 = SentMessage[3*k:4*k]
 
    # Calculating the binary sum of packets
    Sum = bin(int(c1, 2)+int(c2, 2)+int(c3, 2)+int(c4, 2))[2:]
 
    # Adding the overflow bits
    if(len(Sum) > k):
        x = len(Sum)-k
        Sum = bin(int(Sum[0:x], 2)+int(Sum[x:], 2))[2:]
    if(len(Sum) < k):
        Sum = '0'*(k-len(Sum))+Sum
 
    # Calculating the complement of sum
    Checksum = ''
    for i in Sum:
        if(i == '1'):
            Checksum += '0'
        else:
            Checksum += '1'
    return Checksum

def checkReceiverChecksum(ReceivedMessage, k, Checksum):
   
    # Dividing sent message in packets of k bits.
    c1 = ReceivedMessage[0:k]
    c2 = ReceivedMessage[k:2*k]
    c3 = ReceivedMessage[2*k:3*k]
    c4 = ReceivedMessage[3*k:4*k]
 
    # Calculating the binary sum of packets + checksum
    ReceiverSum = bin(int(c1, 2)+int(c2, 2)+int(Checksum, 2) +
                      int(c3, 2)+int(c4, 2)+int(Checksum, 2))[2:]
 
    # Adding the overflow bits
    if(len(ReceiverSum) > k):
        x = len(ReceiverSum)-k
        ReceiverSum = bin(int(ReceiverSum[0:x], 2)+int(ReceiverSum[x:], 2))[2:]
 
    # Calculating the complement of sum
    ReceiverChecksum = ''
    for i in ReceiverSum:
        if(i == '1'):
            ReceiverChecksum += '0'
        else:
            ReceiverChecksum += '1'
    return ReceiverChecksum
 

def main():
    serverIP = ''
    serverPort = 5001

    print("1 - Receber arquivos para teste")
    print("2 - Chat Cliente-Servidor")

    option = int(input())

    if option == 1:
        k = 8 #Pacotes terao k bits
        gap = "<gap>"

        udpSocketServer = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        server = (serverIP, serverPort)

        print("Aguardando conexão...")
        udpSocketServer.bind(server) # O bind serve para que o servidor comece a escutar o IP e a Porta definida anteriormente

        fileInfo, source = udpSocketServer.recvfrom(4096) # Recebemos os dados contendo nome e tamanho do arquivo
        fileInfo = fileInfo.decode('utf-8')
        checksum = findChecksum(fileInfo, k)
        print("File information received!")

        fileName, fileSize = fileInfo.split(gap) # Separamos o nome e o tamanho usando a variável 'gap' no split

        fileName = os.path.basename(fileName) # O caminho que recebemos é o do cliente, então temos que tirar esse caminho, pois vai ser diferente do servidor

        with open(fileName, "wb") as file_:
            print("Reading file...")    
            while True:
                bytesRead = udpSocketServer.recv(4096)
                retorno_checksum = checkReceiverChecksum(bytesRead, k, checksum)
                # If sum = 0, No error is detected
                if(int(retorno_checksum, 2) == 0):
                    print("Receiver Checksum is equal to 0. Therefore,")
                    print("STATUS: ACCEPTED")
                # Otherwise, Error is detected
                else:
                    print("Receiver Checksum is not equal to 0. Therefore,")
                    print("STATUS: ERROR DETECTED")
                if bytesRead == b'file_download_exit': # Se nada for recebido, acabou o arquivo, então para de receber
                    print("File Downloaded")
                    break
                
                file_.write(bytesRead) # Escreve o que foi recebido no arquivo
                
        file_.close()
        udpSocketServer.close()


    elif option == 2:
        k = 8
        flag = 1

        udpSocketServer = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        server = (serverIP, serverPort)

        udpSocketServer.bind(server) # O bind serve para que o servidor comece a escutar o IP e a Porta definida anteriormente

        while flag == 1:
            clientMessage, source = udpSocketServer.recvfrom(1024) # O 1024 representa o tamanho do buffer
            clientMessage = clientMessage.decode('ASCII') # Faço a conversão de bytes para string de volta
            #checksumChat = findChecksum(clientMessage, k)
            
            if clientMessage == "SAIR":
                print ("A conexão foi encerrada pelo cliente...")
                flag = 0
            else:
                print (source[0], ":", clientMessage)
                response = "Entendido!"
                udpSocketServer.sendto(bytes(response, "utf8"), source)
                
        udpSocketServer.close()


main()