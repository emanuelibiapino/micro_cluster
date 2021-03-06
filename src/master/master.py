import zmq as mySocket
import sys
import threading
import json
import time
import base64
from readdata import load
import zlib
from txt_to_json import make as data_json
from jack_module import make_jack
import os
from final_reducer import reducer
from sorting import sorting as make_order
from sender import send


def descompacta(text):
    return zlib.decompress(text)


def compacta(text):
    return zlib.compress(text)


def tprint(msg):

    sys.stdout.write(msg + '\n')
    sys.stdout.flush()


class ServerTask(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):

        context = mySocket.Context()
        frontend = context.socket(mySocket.ROUTER)
        frontend.bind('tcp://192.168.0.3:5576')

        backend = context.socket(mySocket.DEALER)
        backend.bind('inproc://backend')

        # workers = []

        worker = ServerWorker(context)
        worker.start()
        # workers.append(worker)

        mySocket.proxy(frontend, backend)

        frontend.close()
        backend.close()
        context.term()


class ServerWorker(threading.Thread):

    def __init__(self, context):
        threading.Thread.__init__(self)
        self.context = context

    def run(self):

        worker = self.context.socket(mySocket.DEALER)
        worker.connect('inproc://backend')
        tprint('Servidor TRABALAHNDO')
        quant_slave = 1
        count = 0

        lastid = None

        myNodes = []

        while count < quant_slave:

            ident, msg = worker.recv_multipart()

            myNodes.append(ident)  # Guardando referência do meu node

            lastid = ident

            print("Worker %s" % (ident))

            if lastid != ident.decode():
                count += 1

        print("Terminou!")

        # recebendo data e convertendo em JSOn
        data = data_json(
            load()
        )
        # montando clusters do arquivo recebido com base na quantidade de nodes do cluster
        parts = make_jack(count, data)

        count_ident = 0

        for line in parts:
            # aqui se cifra a mensagem em base64
            cifrado = base64.b64encode(str(line).encode('utf-8'))
            compactado = compacta(cifrado)

            # Enviando para cada node uma parte do arquivo
            worker.send_multipart([myNodes[count_ident], compactado])
            count_ident += 1

        count = 0

        while count < quant_slave:

            ident, msg = worker.recv_multipart()

            descompactado = descompacta(msg)  # descompactando texto
            decifrado = base64.b64decode(descompactado)  # decifra mensagem

            out = open('cache/mapper_output.txt', 'a')
            # EVAL converte bytes em Array List
            for line in eval(decifrado):
                out.write(str(line))

            count += 1

        out.close()
        print("Aqui 1")
        # Sorting results mapper
        make_order('cache/mapper_output.txt')
        print("Aqui 2")
        # executa o final reducing
        reducer('cache/mapper_output.txt')
        print("Aqui 3")
        # Envia pro cliente

        send("".join([line for line in open('cache/reducer_output.txt')]))

        print("Aqui 4")
        # Deletando file tmp
        os.remove('cache/mapper_output.txt')
        print("Aqui 5")

        print("Task - Completa!")

        worker.close()
        print("Aqui 6")


def main():

    server = ServerTask()
    server.start()
    server.join()
