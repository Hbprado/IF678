import socket
import os
import zlib
import time
from dataclasses import dataclass

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

def timer(udpSocketServer, seqNumber, respCheck, response, gap):
    auxWhile = 1 # Variável auxiliar para o loop
    flagWhile = 1 #  Flag para controlar o loop
    while auxWhile:
        udpSocketServer.settimeout(0.6) # Definimos o tempo do nosso temporizador
        try:
            isACK, source = udpSocketServer.recvfrom(4096) # Esperamos o ACK do nosso pacote
            isACK = isACK.decode('utf-8') # Decodificamos o pacote recebido

            ackChecksum, ackMessage, ackSeqNumber = isACK.split(gap) # Separamos as informações do pacote, usando a variável 'gap' no split

            # Caso o checksum do ACK e o checksum calculado do ACK recebido sejam diferentes
            # Ou o número de sequência seja do pacote errado, iremos apenas continuar no loop, aguardando o ACK correto
            if ackChecksum != str(checksum_calc(ackMessage)) or ackSeqNumber != str(seqNumber):
                flagWhile = 1 # Ficamos no loop
            else:
                flagWhile = 0 # Saímos do loop

        except socket.timeout: # Caso o temporizador estoure, fazemos o reenvio da mensagem
            udpSocketServer.sendto(f"{respCheck}{gap}{response}{gap}{seqNumber}".encode('utf-8'), source)
        else: # Caso recebamos um pacote no "try", checamos se a flagWhile foi alterada
            if flagWhile == 0: # Se é igual a zero, quer dizer que recebemos o ACK correto
                auxWhile = 0

def waitMessage(udpSocketServer):
    auxWhile = 1
    while auxWhile:
        try:
            clientMessage, source = udpSocketServer.recvfrom(1024) # Recebemos a mensagem do cliente
        except:
            auxWhile = 1
        else:
            auxWhile = 0
            return clientMessage, source

@dataclass
class clientInfo:
    id: int
    mesa: int
    name: str
    socket: None # Vai ser um array
    pedidos: None # Vai ser um array
    total: float

@dataclass
class foodInfo:
    id: int
    name: str
    price: float

serverIP = ''
serverPort = 5001

seqNumber = 0

print("1 - Receber arquivos para teste")
print("2 - Chat Cliente-Servidor")

option = int(input())
print("-----------------------")
print("")

gap = "<gap>"

if option == 1:

    udpSocketServer = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    server = (serverIP, serverPort)

    print("Aguardando conexão...")
    udpSocketServer.bind(server) # O bind serve para que o servidor comece a escutar o IP e a Porta definida anteriormente

    fileInfo, source = udpSocketServer.recvfrom(4096) # Recebemos os dados contendo nome e tamanho do arquivo
    fileInfo = fileInfo.decode('utf-8')
    print("File information received!")

    fileName, fileSize = fileInfo.split(gap) # Separamos o nome e o tamanho usando a variável 'gap' no split

    fileName = os.path.basename(fileName) # O caminho que recebemos é o do cliente, então temos que tirar esse caminho, pois vai ser diferente do servidor

    with open(fileName, "wb") as file_:
        print("Reading file...")    
        while True:
            bytesRead = udpSocketServer.recv(4096)

            if bytesRead == b'file_download_exit': # Se nada for recebido, acabou o arquivo, então para de receber
                print("File Downloaded")
                break
            
            file_.write(bytesRead) # Escreve o que foi recebido no arquivo
            
    file_.close()
    udpSocketServer.close()


elif option == 2:

    flag = 1

    clientsTable = []
    clientsID = 0

    foodList = [foodInfo(1, "Bacalhau", 49.90), foodInfo(2, "Parmegiana", 69.90), foodInfo(3, "Lasanha", 39.90), foodInfo(4, "Ovo Frito", 9.90), foodInfo(5, "Coxinha", 4.90)]

    udpSocketServer = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    server = (serverIP, serverPort)

    udpSocketServer.bind(server) # O bind serve para que o servidor comece a escutar o IP e a Porta definida anteriormente

    while flag == 1:
        clientMessage, source = waitMessage(udpSocketServer)
        
        clientMessage = clientMessage.decode('utf-8') # Decodificamos a mensagem

        pktChecksum, pktMessage, pktSeqNumber = clientMessage.split(gap) # Separamos as informações do pacote, usando a variável 'gap' no split

        # Caso o checksum da mensagem e o checksum calculado da mensagem recebido sejam diferentes
        # vamos pedir a retransmissão, enviando um ACK de número de sequência errado
        if str(checksum_calc(pktMessage)) != pktChecksum:
            message = "ACK"
            check = checksum_calc(message)
            udpSocketServer.sendto(f"{check}{gap}{message}{gap}{1 - seqNumber}".encode('utf-8'), source)

            retry, aux = udpSocketServer.recvfrom(1024) # Recebemos novamente a mensagem do cliente
            retry = retry.decode('utf-8')

            retryChecksum, pktMessage, retrySeqNumber = retry.split(gap) # Separamos as informações do pacote, usando a variável 'gap' no split

            # Caso o checksum da mensagem e o checksum calculado da mensagem recebido sejam diferentes novamente
            # vamos avisar com um ACK errado novamente e encerrar a conexão
            if str(checksum_calc(pktMessage)) != retryChecksum:
                udpSocketServer.sendto(f"{check}{gap}{message}{gap}{1 - seqNumber}".encode('utf-8'), source)
                flag = 0
        
        if pktMessage == "1": # CARDÁPIO
            # Se tudo estiver certo com o comando recebido, vamos enviar um ACK correto
            message = "ACK"
            check = checksum_calc(message)
            udpSocketServer.sendto(f"{check}{gap}{message}{gap}{seqNumber}".encode('utf-8'), source)
            print (source[0], ":", pktMessage) # Printamos a mensagem no terminal
            seqNumber = 1 - seqNumber # Alteramos o número de sequência

            # Fazemos o envio do cardápio, baseado na nossa foodList criada previamente
            response = "\n------- Cardápio ------- \n"
            for food in foodList:
                response += f"{food.id} - {food.name} - {food.price}\n"
            response += "------------------------- \n"
            respCheck = checksum_calc(response)
            udpSocketServer.sendto(f"{respCheck}{gap}{response}{gap}{seqNumber}".encode('utf-8'), source)

            # No rdt3.0, ao enviarmos um pacote, ficamos esperando em loop até que chegue o ACK correto.
            # Ou seja, caso chegue o ACK do pacote errado, continuamos esperando. Caso esperemos demais,
            # o temporizador vai estourar, então faremos reenvio do pacote e o reset o temporizador.
            
            # Ativamos o timer para iniciar o processo citado acima.
            timer(udpSocketServer, seqNumber, respCheck, response, gap)

        elif pktMessage == "2": # PEDIDO
            # Se tudo estiver certo com o comando recebido, vamos enviar um ACK correto
            message = "ACK"
            check = checksum_calc(message)
            udpSocketServer.sendto(f"{check}{gap}{message}{gap}{seqNumber}".encode('utf-8'), source)
            print (source[0], ":", pktMessage)
            seqNumber = 1 - seqNumber # Alteramos o número de sequência

            # Respondemos o cliente, solicitando a comida que ele deseja pedir
            response = "Digite o ID ou NOME da comida desejada"
            respCheck = checksum_calc(response)
            udpSocketServer.sendto(f"{respCheck}{gap}{response}{gap}{seqNumber}".encode('utf-8'), source)

            # No rdt3.0, ao enviarmos um pacote, ficamos esperando em loop até que chegue o ACK correto.
            # Ou seja, caso chegue o ACK do pacote errado, continuamos esperando. Caso esperemos demais,
            # o temporizador vai estourar, então faremos reenvio do pacote e o reset o temporizador.
            
            # Ativamos o timer para iniciar o processo citado acima.
            timer(udpSocketServer, seqNumber, respCheck, response, gap)

            # Após sabermos que o nossa solicitação chegou tudo ok no cliente, vamos esperar a resposta do cliente
            clientMessage, source = waitMessage(udpSocketServer)
            
            clientMessage = clientMessage.decode('utf-8') # Decodificamos a mensagem

            pktChecksum, pktMessage, pktSeqNumber = clientMessage.split(gap) # Separamos as informações do pacote, usando a variável 'gap' no split

            # Salvamos o pedido do cliente
            pedido = pktMessage

            # Caso o checksum da mensagem e o checksum calculado da mensagem recebido sejam diferentes
            # vamos pedir a retransmissão com um ACK de número de sequência errado
            if str(checksum_calc(pktMessage)) != pktChecksum:
                message = "ACK"
                check = checksum_calc(message)
                udpSocketServer.sendto(f"{check}{gap}{message}{gap}{1 - seqNumber}".encode('utf-8'), source)

                retry, aux = udpSocketServer.recvfrom(1024) # Recebemos novamente a mensagem do cliente
                retry = retry.decode('utf-8')

                retryChecksum, pktMessage, retrySeqNumber = retry.split(gap) # Separamos as informações do pacote, usando a variável 'gap' no split

                # Salvamos o pedido do cliente novamente
                pedido = pktMessage

                # Caso o checksum da mensagem e o checksum calculado da mensagem recebido sejam diferentes novamente
                # vamos avisar com um ACK errado novamente e encerrar a conexão
                if str(checksum_calc(pktMessage)) != retryChecksum:
                    udpSocketServer.sendto(f"{check}{gap}{message}{gap}{1 - seqNumber}".encode('utf-8'), source)
                    flag = 0

            # Se tudo estiver certo, vamos enviar um ACK correto
            message = "ACK"
            check = checksum_calc(message)
            udpSocketServer.sendto(f"{check}{gap}{message}{gap}{seqNumber}".encode('utf-8'), source)
            print (source[0], ":", pktMessage)
            seqNumber = 1 - seqNumber # Alteramos o número de sequência

            # Adiciono o pedido na coluna de pedidos do cliente em questão
            foodFlag = 1
            for food in foodList:
                if str(food.id) == pedido or food.name == pedido:
                    for client in clientsTable:
                        if client.socket == source:
                            client.pedidos.append(food)
                            foodFlag = 0
            
            # Avisamos ao cliente se o pedido foi registrado com sucesso ou não
            if foodFlag == 0:
                response = "Pedido registrado!!"
            else:
                response = "Não temos a comida solicitada! Tente novamente..."
            
            respCheck = checksum_calc(response)
            udpSocketServer.sendto(f"{respCheck}{gap}{response}{gap}{seqNumber}".encode('utf-8'), source)

            # No rdt3.0, ao enviarmos um pacote, ficamos esperando em loop até que chegue o ACK correto.
            # Ou seja, caso chegue o ACK do pacote errado, continuamos esperando. Caso esperemos demais,
            # o temporizador vai estourar, então faremos reenvio do pacote e o reset o temporizador.
            
            # Ativamos o timer para iniciar o processo citado acima.
            timer(udpSocketServer, seqNumber, respCheck, response, gap)

        elif pktMessage == "3": # CONTA INDIVIDUAL
            # Se tudo estiver certo com o comando recebido, vamos enviar um ACK correto
            message = "ACK"
            check = checksum_calc(message)
            udpSocketServer.sendto(f"{check}{gap}{message}{gap}{seqNumber}".encode('utf-8'), source)
            print (source[0], ":", pktMessage)
            seqNumber = 1 - seqNumber # Alteramos o número de sequência

            # Mandamos a conta individual do cliente, concatenando as informações que temos
            for client in clientsTable:
                if client.socket == source:
                    total = 0
                    response = f"\n> Conta de {client.name} da mesa {client.mesa} < \n"
                    for food in client.pedidos:
                        response += f"{food.name} __________ {food.price}\n"
                        total += food.price
                    response += f"-------- TOTAL = {round(total, 2)} --------\n"

            respCheck = checksum_calc(response)
            udpSocketServer.sendto(f"{respCheck}{gap}{response}{gap}{seqNumber}".encode('utf-8'), source)

            # No rdt3.0, ao enviarmos um pacote, ficamos esperando em loop até que chegue o ACK correto.
            # Ou seja, caso chegue o ACK do pacote errado, continuamos esperando. Caso esperemos demais,
            # o temporizador vai estourar, então faremos reenvio do pacote e o reset o temporizador.
            
            # Ativamos o timer para iniciar o processo citado acima.
            timer(udpSocketServer, seqNumber, respCheck, response, gap)

        elif pktMessage == "4": # CONTA DA MESA
            # Se tudo estiver certo com o comando recebido, vamos enviar um ACK correto
            message = "ACK"
            check = checksum_calc(message)
            udpSocketServer.sendto(f"{check}{gap}{message}{gap}{seqNumber}".encode('utf-8'), source)
            print (source[0], ":", pktMessage)
            seqNumber = 1 - seqNumber # Alteramos o número de sequência 

            # Procuramos o cliente pelo socket, para descobrirmos a mesa dele
            for client in clientsTable:
                if client.socket == source:
                    auxMesa = client.mesa
                    totalMesa = 0
                    # Agora que sabemos a mesa, podemos achar todos os clientes que estão nessa mesa e mostrar a conta de cada um
                    for client2 in clientsTable:
                        if client2.mesa == auxMesa:
                            client2.total = 0
                            response = f"\n> Sua conta {client2.name} da mesa {client2.mesa} < \n"
                            for food in client.pedidos:
                                response += f"{food.name} __________ {food.price}\n"
                                client2.total += food.price
                            response += f"-------- TOTAL = {round(client2.total, 2)} --------\n"

            respCheck = checksum_calc(response)
            udpSocketServer.sendto(f"{respCheck}{gap}{response}{gap}{seqNumber}".encode('utf-8'), source)

            # No rdt3.0, ao enviarmos um pacote, ficamos esperando em loop até que chegue o ACK correto.
            # Ou seja, caso chegue o ACK do pacote errado, continuamos esperando. Caso esperemos demais,
            # o temporizador vai estourar, então faremos reenvio do pacote e o reset o temporizador.
            
            # Ativamos o timer para iniciar o processo citado acima.
            timer(udpSocketServer, seqNumber, respCheck, response, gap)

        elif pktMessage == "5": # PAGAMENTO
            # Se tudo estiver certo com o comando recebido, vamos enviar um ACK correto
            message = "ACK"
            check = checksum_calc(message)
            udpSocketServer.sendto(f"{check}{gap}{message}{gap}{seqNumber}".encode('utf-8'), source)
            print (source[0], ":", pktMessage)
            seqNumber = 1 - seqNumber # Alteramos o número de sequência

            # Achamos o cliente pelo socket
            for client in clientsTable:
                if client.socket == source:
                    auxMesa = client.mesa
                    totalMesa = 0
                    clientesMesa = -1 # Começo com -1 pois o próprio cliente não entra na conta da divisão do valor a mais (caso tenha)
                    totalCliente = 0

                    # Calculamos o valor da sua conta e mostramos para ele
                    response = f"\n> Sua conta {client.name} da mesa {client.mesa} < \n"
                    for food in client.pedidos:
                        response += f"{food.name} __________ {food.price}\n"
                        totalCliente += food.price
                    response += f"TOTAL = {round(totalCliente, 2)}, Quanto deseja pagar?: \n"
                    client.total = totalCliente

                    # Calculamos também a conta da mesa inteira
                    for client2 in clientsTable:
                        if client2.mesa == auxMesa:
                            for food in client2.pedidos:
                                totalMesa += food.price
                            clientesMesa += 1

            respCheck = checksum_calc(response)
            udpSocketServer.sendto(f"{respCheck}{gap}{response}{gap}{seqNumber}".encode('utf-8'), source)

            # No rdt3.0, ao enviarmos um pacote, ficamos esperando em loop até que chegue o ACK correto.
            # Ou seja, caso chegue o ACK do pacote errado, continuamos esperando. Caso esperemos demais,
            # o temporizador vai estourar, então faremos reenvio do pacote e o reset o temporizador.
            
            # Ativamos o timer para iniciar o processo citado acima.
            timer(udpSocketServer, seqNumber, respCheck, response, gap)

            # Agora vamos esperar o valor que o cliente quer pagar e fazer a checagem do valor
            clientMessage, source = waitMessage(udpSocketServer)
            
            clientMessage = clientMessage.decode('utf-8') # Decodificamos a mensagem

            pktChecksum, pktMessage, pktSeqNumber = clientMessage.split(gap) # Separamos as informações do pacote, usando a variável 'gap' no split

            # Salvamos o valor de pagamento do cliente
            pagamento = pktMessage

            # Caso o checksum da mensagem e o checksum calculado da mensagem recebido sejam diferentes
            # vamos pedir a retransmissão com um ACK de número de sequência errado
            if str(checksum_calc(pktMessage)) != pktChecksum:
                message = "ACK"
                check = checksum_calc(message)
                udpSocketServer.sendto(f"{check}{gap}{message}{gap}{1 - seqNumber}".encode('utf-8'), source)

                retry, aux = udpSocketServer.recvfrom(1024) # Recebemos novamente a mensagem do cliente
                retry = retry.decode('utf-8')

                retryChecksum, pktMessage, retrySeqNumber = retry.split(gap) # Separamos as informações do pacote, usando a variável 'gap' no split

                # Salvamos o valor de pagamento do cliente novamente
                pagamento = pktMessage

                # Caso o checksum da mensagem e o checksum calculado da mensagem recebido sejam diferentes novamente
                # vamos avisar com um ACK errado novamente e encerrar a conexão
                if str(checksum_calc(pktMessage)) != retryChecksum:
                    udpSocketServer.sendto(f"{check}{gap}{message}{gap}{1 - seqNumber}".encode('utf-8'), source)
                    flag = 0

            # Se tudo estiver certo, vamos enviar um ACK correto
            message = "ACK"
            check = checksum_calc(message)
            udpSocketServer.sendto(f"{check}{gap}{message}{gap}{seqNumber}".encode('utf-8'), source)
            print (source[0], ":", pagamento)
            seqNumber = 1 - seqNumber # Alteramos o número de sequência
            
            # Fazemos a checagem para saber se o cliente pode pagar esse valor ou não
            if float(pagamento) < totalCliente: # Caso seja menor que a conta dele, não pode pagar
                response = f"Opa, resta pagar: {total-float(pagamento)}"
            elif float(pagamento) == totalCliente: # Caso seja igual a conta dele, tudo certo
                response = f"Conta paga com sucesso!"
                # Faço a remoção do cliente
                for client in clientsTable:
                    if client.socket == source:
                        clientsTable.pop(clientsTable.index(client))
            elif float(pagamento) > totalMesa: # Caso seja maior que a conta da mesa, não pode pagar
                response = f"Opa, voce pagou {float(pagamento)-total} a mais que a conta total da mesa!"
            elif totalCliente < float(pagamento) and totalMesa > float(pagamento): # Pagar um valor maior que a conta individual, mas menor que a mesa
                        auxValue = float(pagamento) - totalCliente # Retiro a quantia da conta individual do pagamento
                        # Faço a remoção do cliente
                        for client in clientsTable:
                            if client.socket == source:
                                clientsTable.pop(clientsTable.index(client))
                        
                        auxValue = auxValue / clientesMesa # Divido a quantia restante do pagamento igualmente

                        for client in clientsTable:
                            if client.mesa == auxMesa:
                                client.total -= auxValue # Retiro a quantia do total da conta de cada um da mesa
                        response = "Conta paga com sucesso!"
            
            respCheck = checksum_calc(response)
            udpSocketServer.sendto(f"{respCheck}{gap}{response}{gap}{seqNumber}".encode('utf-8'), source)

            # No rdt3.0, ao enviarmos um pacote, ficamos esperando em loop até que chegue o ACK correto.
            # Ou seja, caso chegue o ACK do pacote errado, continuamos esperando. Caso esperemos demais,
            # o temporizador vai estourar, então faremos reenvio do pacote e o reset o temporizador.
            
            # ATIVAR TIMER
            timer(udpSocketServer, seqNumber, respCheck, response, gap)

        elif pktMessage == "6": # SAIR
            # Se tudo estiver certo com o comando recebido, vamos enviar um ACK correto
            message = "ACK"
            check = checksum_calc(message)
            udpSocketServer.sendto(f"{check}{gap}{message}{gap}{seqNumber}".encode('utf-8'), source)
            print (source[0], ":", pktMessage)
            seqNumber = 1 - seqNumber # Alteramos o número de sequência

            # Faço a remoção do cliente
            for client in clientsTable:
                if client.socket == source:
                    clientsTable.pop(clientsTable.index(client))

            # Fazemos o envio da resposta do servidor para o cliente
            response = "Tudo ok, volte sempre!"
            respCheck = checksum_calc(response)
            udpSocketServer.sendto(f"{respCheck}{gap}{response}{gap}{seqNumber}".encode('utf-8'), source)

            # No rdt3.0, ao enviarmos um pacote, ficamos esperando em loop até que chegue o ACK correto.
            # Ou seja, caso chegue o ACK do pacote errado, continuamos esperando. Caso esperemos demais,
            # o temporizador vai estourar, então faremos reenvio do pacote e o reset o temporizador.
            
            # Ativamos o timer para iniciar o processo citado acima.
            timer(udpSocketServer, seqNumber, respCheck, response, gap)

        elif pktMessage == "chefia":
            # Se tudo estiver certo com o comando recebido, vamos enviar um ACK correto
            message = "ACK"
            check = checksum_calc(message)
            udpSocketServer.sendto(f"{check}{gap}{message}{gap}{seqNumber}".encode('utf-8'), source)
            print (source[0], ":", pktMessage)
            seqNumber = 1 - seqNumber # Alteramos o número de sequência

            # Como recebemos "chefia", iremos pedir a mesa do cliente
            response = "Digite sua mesa"
            respCheck = checksum_calc(response)
            udpSocketServer.sendto(f"{respCheck}{gap}{response}{gap}{seqNumber}".encode('utf-8'), source)

            # No rdt3.0, ao enviarmos um pacote, ficamos esperando em loop até que chegue o ACK correto.
            # Ou seja, caso chegue o ACK do pacote errado, continuamos esperando. Caso esperemos demais,
            # o temporizador vai estourar, então faremos reenvio do pacote e o reset o temporizador.
            
            # Ativamos o timer para iniciar o processo citado acima.
            timer(udpSocketServer, seqNumber, respCheck, response, gap)
                
            # Após sabermos que o nosso pedido de mesa chegou tudo ok, vamos esperar a resposta do cliente
            clientMessage, source = waitMessage(udpSocketServer)
            
            clientMessage = clientMessage.decode('utf-8') # Decodificamos a mensagem

            pktChecksum, pktMessage, pktSeqNumber = clientMessage.split(gap) # Separamos as informações do pacote, usando a variável 'gap' no split

            # Salvamos a mesa do cliente
            mesaCliente = pktMessage

            # Caso o checksum da mensagem e o checksum calculado da mensagem recebido sejam diferentes
            # vamos pedir a retransmissão com um ACK de número de sequência errado
            if str(checksum_calc(pktMessage)) != pktChecksum:
                message = "ACK"
                check = checksum_calc(message)
                udpSocketServer.sendto(f"{check}{gap}{message}{gap}{1 - seqNumber}".encode('utf-8'), source)

                retry, aux = udpSocketServer.recvfrom(1024) # Recebemos novamente a mensagem do cliente
                retry = retry.decode('utf-8')

                retryChecksum, pktMessage, retrySeqNumber = retry.split(gap) # Separamos as informações do pacote, usando a variável 'gap' no split

                # Salvamos a mesa do cliente novamente
                mesaCliente = pktMessage

                # Caso o checksum da mensagem e o checksum calculado da mensagem recebido sejam diferentes novamente
                # vamos avisar com um ACK errado novamente e encerrar a conexão
                if str(checksum_calc(pktMessage)) != retryChecksum:
                    udpSocketServer.sendto(f"{check}{gap}{message}{gap}{1 - seqNumber}".encode('utf-8'), source)
                    flag = 0

            # Se tudo estiver certo, vamos enviar um ACK correto
            message = "ACK"
            check = checksum_calc(message)
            udpSocketServer.sendto(f"{check}{gap}{message}{gap}{seqNumber}".encode('utf-8'), source)
            print (source[0], ":", pktMessage)
            seqNumber = 1 - seqNumber # Alteramos o número de sequência

            # Agora que recebemos o número da mesa, iremos pedir o nome do cliente
            response = "Digite seu nome"
            respCheck = checksum_calc(response)
            udpSocketServer.sendto(f"{respCheck}{gap}{response}{gap}{seqNumber}".encode('utf-8'), source)

            # No rdt3.0, ao enviarmos um pacote, ficamos esperando em loop até que chegue o ACK correto.
            # Ou seja, caso chegue o ACK do pacote errado, continuamos esperando. Caso esperemos demais,
            # o temporizador vai estourar, então faremos reenvio do pacote e o reset o temporizador.
            
            # Ativamos o timer para iniciar o processo citado acima.
            timer(udpSocketServer, seqNumber, respCheck, response, gap)

            # Após sabermos que o nosso pedido de nome chegou tudo ok, vamos esperar a resposta do cliente
            clientMessage, source = waitMessage(udpSocketServer)
            
            clientMessage = clientMessage.decode('utf-8') # Decodificamos a mensagem

            pktChecksum, pktMessage, pktSeqNumber = clientMessage.split(gap) # Separamos as informações do pacote, usando a variável 'gap' no split

            # Salvamos o nome do cliente
            clientName = pktMessage

            # Caso o checksum da mensagem e o checksum calculado da mensagem recebido sejam diferentes
            # vamos pedir a retransmissão com um ACK de número de sequência errado
            if str(checksum_calc(pktMessage)) != pktChecksum:
                message = "ACK"
                check = checksum_calc(message)
                udpSocketServer.sendto(f"{check}{gap}{message}{gap}{1 - seqNumber}".encode('utf-8'), source)

                retry, aux = udpSocketServer.recvfrom(1024) # Recebemos novamente a mensagem do cliente
                retry = retry.decode('utf-8')

                retryChecksum, pktMessage, retrySeqNumber = retry.split(gap) # Separamos as informações do pacote, usando a variável 'gap' no split

                # Salvamos o nome do cliente novamente
                clientName = pktMessage

                # Caso o checksum da mensagem e o checksum calculado da mensagem recebido sejam diferentes novamente
                # vamos avisar com um ACK errado novamente e encerrar a conexão
                if str(checksum_calc(pktMessage)) != retryChecksum:
                    udpSocketServer.sendto(f"{check}{gap}{message}{gap}{1 - seqNumber}".encode('utf-8'), source)
                    flag = 0
            
            # Se tudo estiver certo, vamos enviar um ACK correto
            message = "ACK"
            check = checksum_calc(message)
            udpSocketServer.sendto(f"{check}{gap}{message}{gap}{seqNumber}".encode('utf-8'), source)
            print (source[0], ":", pktMessage)
            seqNumber = 1 - seqNumber # Alteramos o número de sequência

            # Fazemos o envio da resposta do servidor para o cliente: "Entendido!"
            response = "\nEscolha sua opção:\n 1 - Cardápio\n 2 - Pedido\n 3 - Conta Individual\n 4 - Conta da Mesa\n 5 - Pagamento\n 6 - Sair\n"
            respCheck = checksum_calc(response)
            udpSocketServer.sendto(f"{respCheck}{gap}{response}{gap}{seqNumber}".encode('utf-8'), source)


            # No rdt3.0, ao enviarmos um pacote, ficamos esperando em loop até que chegue o ACK correto.
            # Ou seja, caso chegue o ACK do pacote errado, continuamos esperando. Caso esperemos demais,
            # o temporizador vai estourar, então faremos reenvio do pacote e o reset o temporizador.
            
            # Ativamos o timer para iniciar o processo citado acima.
            timer(udpSocketServer, seqNumber, respCheck, response, gap)

            # Salvo as informações recebidas do cliente na tabela de clientes
            clientsID = clientsID + 1
            clientsTable.append(clientInfo(clientsID, mesaCliente, clientName, source, [], 0))

        else:
            # Se tudo estiver certo, vamos enviar um ACK correto
            message = "ACK"
            check = checksum_calc(message)
            udpSocketServer.sendto(f"{check}{gap}{message}{gap}{seqNumber}".encode('utf-8'), source)
            print (source[0], ":", pktMessage)
            seqNumber = 1 - seqNumber # Alteramos o número de sequência

            # Fazemos o envio da resposta do servidor para o cliente: "Entendido!"
            response = "Comando não existente..."
            respCheck = checksum_calc(response)
            udpSocketServer.sendto(f"{respCheck}{gap}{response}{gap}{seqNumber}".encode('utf-8'), source)


            # No rdt3.0, ao enviarmos um pacote, ficamos esperando em loop até que chegue o ACK correto.
            # Ou seja, caso chegue o ACK do pacote errado, continuamos esperando. Caso esperemos demais,
            # o temporizador vai estourar, então faremos reenvio do pacote e o reset o temporizador.
            
            # Ativamos o timer para iniciar o processo citado acima.
            timer(udpSocketServer, seqNumber, respCheck, response, gap)

    udpSocketServer.close()